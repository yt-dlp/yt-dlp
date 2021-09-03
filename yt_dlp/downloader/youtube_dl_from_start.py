from __future__ import unicode_literals

import re
from time import sleep

from .fragment import FragmentFD
from ..downloader import get_suitable_downloader
from ..extractor.youtube import YoutubeIE

from ..utils import (
    urljoin,
    time_millis,
)


class YoutubeDlFromStartDashFD(FragmentFD):
    """
    Download YouTube live from the start, to the end. For DASH formats.
    This currently does not handle downloading 2 streams at once.
    """

    FD_NAME = 'ytlivestartdash'

    @staticmethod
    def _manifest_fragments(ie: YoutubeIE, mpd_url, stream_number, fetch_span=5000):
        known_idx = 0
        no_fragment_count = 0
        prev_dl = time_millis()
        while True:
            if no_fragment_count > 5:
                return
            fmts, _ = ie._extract_mpd_formats_and_subtitles(
                mpd_url, None, note=False, errnote=False, fatal=False)
            if not fmts:
                no_fragment_count += 1
                continue
            fmt_info = next(x for x in fmts if x['manifest_stream_number'] == stream_number)
            fragments = fmt_info['fragments']
            fragment_base_url = fmt_info.get('fragment_base_url')

            last_fragment = fragments[-1]

            assert fragment_base_url
            last_url = urljoin(fragment_base_url, last_fragment['path'])

            last_seq = int(re.search(r'/sq/(\d+)', last_url).group(1))
            for idx in range(known_idx, last_seq):
                seq = idx + 1
                yield {
                    'frag_index': seq,
                    'index': seq,
                    'url': urljoin(fragment_base_url, 'sq/%d' % seq),
                }
            if known_idx == last_seq:
                no_fragment_count += 1
            else:
                no_fragment_count = 0
            known_idx = last_seq

            now_time = time_millis()
            if (now_time - prev_dl) < fetch_span:
                sleep((now_time - prev_dl) / 1e3)
            prev_dl = now_time

    def real_download(self, filename, info_dict):
        manifest_url = info_dict.get('manifest_url')
        if not manifest_url:
            self.report_error('URL for MPD manifest is not known; there is a problem in YoutubeIE code')

        stream_number = info_dict.get('manifest_stream_number', 0)
        yie: YoutubeIE = self.ydl.get_info_extractor(YoutubeIE.ie_key())

        real_downloader = get_suitable_downloader(
            info_dict, self.params, None, protocol='dash_frag_urls', to_stdout=(filename == '-'))

        ctx = {
            'filename': filename,
            'live': True,
        }

        if real_downloader:
            self._prepare_external_frag_download(ctx)
        else:
            self._prepare_and_start_frag_download(ctx, info_dict)

        fragments_to_download = self._manifest_fragments(yie, manifest_url, stream_number)

        if real_downloader:
            self.to_screen(
                '[%s] Fragment downloads will be delegated to %s' % (self.FD_NAME, real_downloader.get_basename()))
            info_copy = info_dict.copy()
            info_copy['fragments'] = fragments_to_download
            fd = real_downloader(self.ydl, self.params)
            return fd.real_download(filename, info_copy)

        return self.download_and_append_fragments(ctx, fragments_to_download, info_dict, ignore_lethal_error=True)
