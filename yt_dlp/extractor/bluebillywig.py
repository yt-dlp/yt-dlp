import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    mimetype2ext,
    parse_codecs,
    parse_iso8601,
    traverse_obj,
    urljoin,
)


class BlueBillywigIE(InfoExtractor):
    _VALID_URL = r'https?://(?P<tenant>[^./?#]+)\.bbvms\.com/p/(?P<playout>[^/?#]+)/c/(?P<id>(?:[^:.]+:)?\d+)\.(?:js(?:on)?|html)(?:[?#]|$)'
    # Not handled: interactive videos. https://www.bluebillywig.com/interactive-video/

    _TESTS = [{
        'url': 'https://scribit.bbvms.com/p/wcag_opties_transcript/c/6047028.html',
        'info_dict': {
            'id': '6047028',
            'ext': 'mp4',
            'title': "Toegankelijke video's Rijksoverheid",
            'description': '',
            'uploader': '',
            'view_count': int,
            'duration': 290,
            'timestamp': 1730451103,
            'upload_date': '20241101',
            'release_timestamp': 1730451194,
            'release_date': '20241101',
            'thumbnail': str,
        },
    }, {
        'url': 'https://omroepgelderland.bbvms.com/p/regiogroei_gelderland_web_videoplayer_noconsent/c/sourceid_string:8534231.json',
        'info_dict': {
            'id': '7444435',
            'ext': 'mp4',
            'title': 'Lege vlaggenmast Oldebroek raakt Ben',
            'description': 'md5:0ac0e9b5d8431e2cf49fc570391b26c4',
            'view_count': int,
            'duration': 85,
            'categories': ['GLD', 'WEZEP', 'GEMEENTE OLDEBROEK', 'OLDEBROEK'],
            'timestamp': 1791539401,
            'upload_date': '20261009',
            'release_timestamp': 1791539422,
            'release_date': '20261009',
            'thumbnail': str,
        },
    }, {
        'url': 'https://rtvoost.bbvms.com/p/regiogroei_oost_web_videoplayer_noconsent/c/4198331.json',
        'info_dict': {
            'id': '4198331',
            'ext': 'm3u8',
            'title': r're:TV Oost \d{4}-\d\d-\d\d \d\d:\d\d',
            'description': 'TV Oost live stream',
            'uploader': 'RTV Oost',
            'view_count': int,
            'categories': ['TV OOST', 'LIVE'],
            'timestamp': 1620392012,
            'upload_date': '20210507',
            'release_timestamp': 1620392026,
            'release_date': '20210507',
            'live_status': 'is_live',
            'thumbnail': str,
        },
    }]

    def _real_extract(self, url):
        tenant, playout, selector = self._match_valid_url(url).group('tenant', 'playout', 'id')

        meta = self._download_json(f'https://{tenant}.bbvms.com/p/{playout}/c/{selector}.json', selector)

        video_id = traverse_obj(meta, ('clipData', 'id'))
        media_urlbase = traverse_obj(meta, ('publicationData', 'defaultMediaAssetPath'))
        language = traverse_obj(meta, ('clipData', 'isocode'))
        is_live = traverse_obj(meta, ('clipData', 'sourcetype')) == 'live'

        formats = []
        thumbnails = []
        subtitles = {}
        for f in traverse_obj(meta, ('clipData', 'assets')) or ():
            if f.get('src') is None:
                continue
            fmt_url = urljoin(media_urlbase, f['src'])
            if f.get('mediatype') == 'MP4_HLS':
                hls_fmts, hls_subs = self._extract_m3u8_formats_and_subtitles(
                    fmt_url, video_id, m3u8_id='hls', live=is_live)
                for fmt in hls_fmts:
                    fmt.setdefault('language', language)
                formats.extend(hls_fmts)
                subtitles = self._merge_subtitles(subtitles, hls_subs)
                continue
            fmt = {
                **traverse_obj(f, {
                    'width': ('width', {int_or_none}),
                    'height': ('height', {int_or_none}),
                    'filesize': ('filesize', {int_or_none}),
                    'tbr': ('bandwidth', {int_or_none}),
                }),
                'format_id': f.get('jobqid'),
                'url': fmt_url,
                'language': language,
            }
            mime_mobj = re.match(
                r'((?:[^/]+)/(?:[^;]+))(?:;\s*codecs="([^"]+)")?', fmt.get('mimeType') or '')
            if mime_mobj:
                fmt['ext'] = mimetype2ext(mime_mobj.group(1))
                fmt.update(parse_codecs(mime_mobj.group(2)))
            formats.append(fmt)

        original_src = traverse_obj(meta, ('clipData', 'src'))
        if original_src:
            formats.append({
                **traverse_obj(meta, ('clipData', {
                    'width': ('width', {int_or_none}),
                    'height': ('height', {int_or_none}),
                })),
                'format_id': 'original_upload',
                'url': urljoin(media_urlbase, original_src),
                'language': language,
                'quality': 1,
            })

        for f in traverse_obj(meta, ('clipData', 'thumbnails')) or ():
            if f.get('src') is None:
                continue
            fmt_url = urljoin(media_urlbase, f['src'])
            thumbnails.append({
                **traverse_obj(f, {
                    'width': ('width', {int_or_none}),
                    'height': ('height', {int_or_none}),
                }),
                'url': fmt_url,
            })

        return {
            **traverse_obj(meta, {
                'id': ('contentId',),
                'title': ('clipData', 'title'),
                'description': ('clipData', 'description'),
                'duration': ('clipData', 'length', {int_or_none}),
                'timestamp': ('clipData', 'createddate', {parse_iso8601}),
                'release_timestamp': ('clipData', 'publisheddate', {parse_iso8601}),
                'modified_timestamp': ('clipData', 'modifieddate', {parse_iso8601}),
                'view_count': ('clipData', 'views', {int_or_none}),
                'uploader': ('clipData', 'author'),
                'categories': ('clipData', 'cat'),
            }),
            'is_live': is_live,
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': thumbnails,
        }
