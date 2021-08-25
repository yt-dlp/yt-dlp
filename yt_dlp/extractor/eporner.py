# coding: utf-8
from __future__ import unicode_literals


from .common import InfoExtractor
from ..utils import (
    encode_base_n,
    ExtractorError,
    int_or_none,
    merge_dicts,
    parse_duration,
    str_to_int,
    url_or_none,
)


class EpornerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?eporner\.com/(?:(?:hd-porn|embed)/|video-)(?P<id>\w+)(?:/(?P<display_id>[\w-]+))?'
    _TESTS = [{
        'url': 'http://www.eporner.com/hd-porn/95008/Infamous-Tiffany-Teen-Strip-Tease-Video/',
        'md5': '39d486f046212d8e1b911c52ab4691f8',
        'info_dict': {
            'id': 'qlDUmNsj6VS',
            'display_id': 'Infamous-Tiffany-Teen-Strip-Tease-Video',
            'ext': 'mp4',
            'title': 'Infamous Tiffany Teen Strip Tease Video',
            'description': 'md5:764f39abf932daafa37485eb46efa152',
            'timestamp': 1232520922,
            'upload_date': '20090121',
            'duration': 1838,
            'view_count': int,
            'age_limit': 18,
        },
        'params': {
            'proxy': '127.0.0.1:8118'
        }
    }, {
        # New (May 2016) URL layout
        'url': 'http://www.eporner.com/hd-porn/3YRUtzMcWn0/Star-Wars-XXX-Parody/',
        'only_matching': True,
    }, {
        'url': 'http://www.eporner.com/hd-porn/3YRUtzMcWn0',
        'only_matching': True,
    }, {
        'url': 'http://www.eporner.com/embed/3YRUtzMcWn0',
        'only_matching': True,
    }, {
        'url': 'https://www.eporner.com/video-FJsA19J3Y3H/one-of-the-greats/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        display_id = mobj.group('display_id') or video_id

        webpage, urlh = self._download_webpage_handle(url, display_id)

        video_id = self._match_id(urlh.geturl())

        hash = self._search_regex(
            r'hash\s*[:=]\s*["\']([\da-f]{32})', webpage, 'hash')

        title = self._og_search_title(webpage, default=None) or self._html_search_regex(
            r'<title>(.+?) - EPORNER', webpage, 'title')

        # Reverse engineered from vjs.js
        def calc_hash(s):
            return ''.join((encode_base_n(int(s[lb:lb + 8], 16), 36) for lb in range(0, 32, 8)))

        video = self._download_json(
            'http://www.eporner.com/xhr/video/%s' % video_id,
            display_id, note='Downloading video JSON',
            query={
                'hash': calc_hash(hash),
                'device': 'generic',
                'domain': 'www.eporner.com',
                'fallback': 'false',
            })

        if video.get('available') is False:
            raise ExtractorError(
                '%s said: %s' % (self.IE_NAME, video['message']), expected=True)

        sources = video['sources']

        formats = []
        for kind, formats_dict in sources.items():
            if not isinstance(formats_dict, dict):
                continue
            for format_id, format_dict in formats_dict.items():
                if not isinstance(format_dict, dict):
                    continue
                src = url_or_none(format_dict.get('src'))
                if not src or not src.startswith('http'):
                    continue
                if kind == 'hls':
                    formats.extend(self._extract_m3u8_formats(
                        src, display_id, 'mp4', entry_protocol='m3u8_native',
                        m3u8_id=kind, fatal=False))
                else:
                    height = int_or_none(self._search_regex(
                        r'(\d+)[pP]', format_id, 'height', default=None))
                    fps = int_or_none(self._search_regex(
                        r'(\d+)fps', format_id, 'fps', default=None))

                    formats.append({
                        'url': src,
                        'format_id': format_id,
                        'height': height,
                        'fps': fps,
                    })
        self._sort_formats(formats)

        json_ld = self._search_json_ld(webpage, display_id, default={})

        duration = parse_duration(self._html_search_meta(
            'duration', webpage, default=None))
        view_count = str_to_int(self._search_regex(
            r'id=["\']cinemaviews1["\'][^>]*>\s*([0-9,]+)',
            webpage, 'view count', default=None))

        return merge_dicts(json_ld, {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'duration': duration,
            'view_count': view_count,
            'formats': formats,
            'age_limit': 18,
        })
