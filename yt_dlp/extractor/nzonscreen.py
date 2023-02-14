from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
    qualities,
    traverse_obj,
    try_get,
    url_or_none,
)


class NZOnScreenIE(InfoExtractor):
    _VALID_URL = r'^https://www.nzonscreen.com/title/(?P<id>[^\?]+)'
    _TESTS = [{
        'url': 'https://www.nzonscreen.com/title/shoop-shoop-diddy-wop-cumma-cumma-wang-dang-1982',
        'info_dict': {
            'id': '726ed6585c6bfb30',
            'display_id': 'shoop-shoop-diddy-wop-cumma-cumma-wang-dang-1982',
            'ext': 'mp4',
            'title': 'Monte Video - "Shoop Shoop, Diddy Wop"',
            'playable_in_embed': False,
            'thumbnail': r're:https://www\.nzonscreen\.com/content/images/.+\.jpg',
            'duration': 158,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.nzonscreen.com/title/shes-a-mod-1964?collection=best-of-the-60s',
        'info_dict': {
            'id': '3dbe709ff03c36f1',
            'display_id': 'shes-a-mod-1964',
            'ext': 'mp4',
            'title': 'Ray Columbus - \'She\'s A Mod\'',
            'playable_in_embed': False,
            'thumbnail': r're:https://www\.nzonscreen\.com/content/images/.+\.jpg',
            'duration': 130,
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _extract_formats(self, playlist):
        quality = qualities(['lo_res', 'hd_res', 'hi_res'])
        for id_, url in (playlist.get('h264') or {}).items():
            if not id_.endswith('_res') or not url_or_none(url):
                continue
            yield {
                'url': url,
                'format_id': id_[:-4],
                'ext': 'mp4',
                'quality': quality(id_),
                'height': int_or_none(playlist.get('height')) if id_ == 'hi_res' else None,
                'width': int_or_none(playlist.get('width')) if id_ == 'hi_res' else None,
                'filesize_approx': float_or_none(traverse_obj(playlist, ('h264', f'{id_}_mb')), invscale=1024**2),
            }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        playlist = self._parse_json(self._html_search_regex(
            r'data-video-config=\'([^\']+)\'', webpage, 'media data'), video_id)

        return {
            'id': playlist['uuid'],
            'display_id': video_id,
            'title': traverse_obj(playlist, 'label', 'description') or try_get(
                self._html_extract_title(webpage, default=None) or self._og_search_title(webpage),
                lambda x: x.split('|')[0].strip()),
            'thumbnail': traverse_obj(playlist, ('thumbnail', 'path')),
            'duration': float_or_none(playlist.get('duration')),
            'playable_in_embed': playlist.get('embeddable'),
            'formats': list(self._extract_formats(playlist)),
            'http_headers': {
                'Referer': 'https://www.nzonscreen.com/',
                'Origin': 'https://www.nzonscreen.com/',
            }
        }
