import io
import quopri
import re
import uuid

from .fragment import FragmentFD
from ..compat import imghdr
from ..utils import escapeHTML, formatSeconds, srt_subtitles_timecode, urljoin
from ..version import __version__ as YT_DLP_VERSION


class MhtmlFD(FragmentFD):
    _STYLESHEET = '''\
html, body {
    margin: 0;
    padding: 0;
    height: 100vh;
}

html {
    overflow-y: scroll;
    scroll-snap-type: y mandatory;
}

body {
    scroll-snap-type: y mandatory;
    display: flex;
    flex-flow: column;
}

body > figure {
    max-width: 100vw;
    max-height: 100vh;
    scroll-snap-align: center;
}

body > figure > figcaption {
    text-align: center;
    height: 2.5em;
}

body > figure > img {
    display: block;
    margin: auto;
    max-width: 100%;
    max-height: calc(100vh - 5em);
}
'''
    _STYLESHEET = re.sub(r'\s+', ' ', _STYLESHEET)
    _STYLESHEET = re.sub(r'\B \B|(?<=[\w\-]) (?=[^\w\-])|(?<=[^\w\-]) (?=[\w\-])', '', _STYLESHEET)

    @staticmethod
    def _escape_mime(s):
        return '=?utf-8?Q?' + (b''.join(
            bytes((b,)) if b >= 0x20 else b'=%02X' % b
            for b in quopri.encodestring(s.encode(), header=True)
        )).decode('us-ascii') + '?='

    def _gen_cid(self, i, fragment, frag_boundary):
        return f'{i}.{frag_boundary}@yt-dlp.github.io.invalid'

    def _gen_stub(self, *, fragments, frag_boundary, title):
        output = io.StringIO()

        output.write(
            '<!DOCTYPE html>'
            '<html>'
            '<head>'
            f'<meta name="generator" content="yt-dlp {escapeHTML(YT_DLP_VERSION)}">'
            f'<title>{escapeHTML(title)}</title>'
            f'<style>{self._STYLESHEET}</style>'
            '<body>')

        t0 = 0
        for i, frag in enumerate(fragments):
            output.write('<figure>')
            try:
                t1 = t0 + frag['duration']
                output.write((
                    '<figcaption>Slide #{num}: {t0} – {t1} (duration: {duration})</figcaption>'
                ).format(
                    num=i + 1,
                    t0=srt_subtitles_timecode(t0),
                    t1=srt_subtitles_timecode(t1),
                    duration=formatSeconds(frag['duration'], msec=True),
                ))
            except (KeyError, ValueError, TypeError):
                t1 = None
                output.write(f'<figcaption>Slide #{i + 1}</figcaption>')
            output.write(f'<img src="cid:{self._gen_cid(i, frag, frag_boundary)}">')
            output.write('</figure>')
            t0 = t1

        return output.getvalue()

    def real_download(self, filename, info_dict):
        fragment_base_url = info_dict.get('fragment_base_url')
        fragments = info_dict['fragments'][:1] if self.params.get(
            'test', False) else info_dict['fragments']
        title = info_dict.get('title', info_dict['format_id'])
        origin = info_dict.get('webpage_url', info_dict['url'])

        ctx = {
            'filename': filename,
            'total_frags': len(fragments),
        }

        self._prepare_and_start_frag_download(ctx, info_dict)

        extra_state = ctx.setdefault('extra_state', {
            'header_written': False,
            'mime_boundary': str(uuid.uuid4()).replace('-', ''),
        })

        frag_boundary = extra_state['mime_boundary']

        if not extra_state['header_written']:
            stub = self._gen_stub(
                fragments=fragments,
                frag_boundary=frag_boundary,
                title=title,
            )

            ctx['dest_stream'].write((
                'MIME-Version: 1.0\r\n'
                'From: <nowhere@yt-dlp.github.io.invalid>\r\n'
                'To: <nowhere@yt-dlp.github.io.invalid>\r\n'
                f'Subject: {self._escape_mime(title)}\r\n'
                'Content-type: multipart/related; '
                f'boundary="{frag_boundary}"; '
                'type="text/html"\r\n'
                f'X.yt-dlp.Origin: {origin}\r\n'
                '\r\n'
                f'--{frag_boundary}\r\n'
                'Content-Type: text/html; charset=utf-8\r\n'
                f'Content-Length: {len(stub)}\r\n'
                '\r\n'
                f'{stub}\r\n').encode())
            extra_state['header_written'] = True

        for i, fragment in enumerate(fragments):
            if (i + 1) <= ctx['fragment_index']:
                continue

            fragment_url = fragment.get('url')
            if not fragment_url:
                assert fragment_base_url
                fragment_url = urljoin(fragment_base_url, fragment['path'])

            success = self._download_fragment(ctx, fragment_url, info_dict)
            if not success:
                continue
            frag_content = self._read_fragment(ctx)

            frag_header = io.BytesIO()
            frag_header.write(
                b'--%b\r\n' % frag_boundary.encode('us-ascii'))
            frag_header.write(
                b'Content-ID: <%b>\r\n' % self._gen_cid(i, fragment, frag_boundary).encode('us-ascii'))
            frag_header.write(
                b'Content-type: %b\r\n' % f'image/{imghdr.what(h=frag_content) or "jpeg"}'.encode())
            frag_header.write(
                b'Content-length: %u\r\n' % len(frag_content))
            frag_header.write(
                b'Content-location: %b\r\n' % fragment_url.encode('us-ascii'))
            frag_header.write(
                b'X.yt-dlp.Duration: %f\r\n' % fragment['duration'])
            frag_header.write(b'\r\n')
            self._append_fragment(
                ctx, frag_header.getvalue() + frag_content + b'\r\n')

        ctx['dest_stream'].write(
            b'--%b--\r\n\r\n' % frag_boundary.encode('us-ascii'))
        return self._finish_frag_download(ctx, info_dict)
