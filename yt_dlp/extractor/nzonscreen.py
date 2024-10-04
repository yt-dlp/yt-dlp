from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
    strip_or_none,
    traverse_obj,
    url_or_none,
)


class NZOnScreenIE(InfoExtractor):
    _VALID_URL = r'https?://www\.nzonscreen\.com/title/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.nzonscreen.com/title/shoop-shoop-diddy-wop-cumma-cumma-wang-dang-1982',
        'info_dict': {
            'id': '726ed6585c6bfb30',
            'ext': 'mp4',
            'format_id': 'hd',
            'display_id': 'shoop-shoop-diddy-wop-cumma-cumma-wang-dang-1982',
            'title': 'Monte Video - "Shoop Shoop, Diddy Wop"',
            'description': 'Monte Video - "Shoop Shoop, Diddy Wop"',
            'alt_title': 'Shoop Shoop Diddy Wop Cumma Cumma Wang Dang',
            'thumbnail': r're:https://www\.nzonscreen\.com/content/images/.+\.jpg',
            'duration': 158,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.nzonscreen.com/title/shes-a-mod-1964?collection=best-of-the-60s',
        'info_dict': {
            'id': '3dbe709ff03c36f1',
            'ext': 'mp4',
            'format_id': 'hd',
            'display_id': 'shes-a-mod-1964',
            'title': 'Ray Columbus - \'She\'s A Mod\'',
            'description': 'Ray Columbus - \'She\'s A Mod\'',
            'alt_title': 'She\'s a Mod',
            'thumbnail': r're:https://www\.nzonscreen\.com/content/images/.+\.jpg',
            'duration': 130,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.nzonscreen.com/title/puha-and-pakeha-1968/overview',
        'info_dict': {
            'id': 'f86342544385ad8a',
            'ext': 'mp4',
            'format_id': 'hd',
            'display_id': 'puha-and-pakeha-1968',
            'title': 'Looking At New Zealand - Puha and Pakeha',
            'alt_title': 'Looking at New Zealand - \'Pūhā and Pākehā\'',
            'description': 'An excerpt from this television programme.',
            'duration': 212,
            'thumbnail': r're:https://www\.nzonscreen\.com/content/images/.+\.jpg',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.nzonscreen.com/title/flatmates-episode-one-1997',
        'info_dict': {
            'id': 'flatmates-episode-one-1997',
            'title': 'Flatmates - 1, First Episode',
        },
        'playlist_count': 5,
    }, {
        # hd format not present
        'url': 'https://www.nzonscreen.com/title/reluctant-hero-2008',
        'info_dict': {
            'id': '847f5c91af65d44b',
            'ext': 'mp4',
            'format_id': 'hi',
            'title': 'Reluctant Hero (clip 1)',
            'description': 'Part one of four from this full length documentary.',
            'display_id': 'reluctant-hero-2008',
            'duration': 1108.0,
            'thumbnail': r're:https://www\.nzonscreen\.com/content/images/.+\.jpg',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _extract_formats(self, playlist):
        for quality, (id_, url) in enumerate(traverse_obj(
                playlist, ('h264', {'lo': 'lo_res', 'hi': 'hi_res', 'hd': 'hd_res'}), expected_type=url_or_none).items()):
            if traverse_obj(playlist, ('h264', f'{id_}_res_mb', {float_or_none})):
                yield {
                    'url': url,
                    'format_id': id_,
                    'ext': 'mp4',
                    'quality': quality,
                    'height': int_or_none(playlist.get('height')) if id_ == 'hd' else None,
                    'width': int_or_none(playlist.get('width')) if id_ == 'hd' else None,
                    'filesize_approx': float_or_none(traverse_obj(playlist, ('h264', f'{id_}_res_mb')), invscale=1024**2),
                }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        title = strip_or_none((
            self._html_extract_title(webpage, default=None)
            or self._og_search_title(webpage)).rsplit('|', 2)[0])
        playlist = self._download_json(
            f'https://www.nzonscreen.com/html5/video_data/{video_id}', video_id, 'media data')

        # TODO: extract subtitles
        if len(playlist) == 1:
            playinfo = playlist[0]
            return {
                'alt_title': title,
                'display_id': video_id,
                'formats': list(self._extract_formats(playinfo)),
                'http_headers': {
                    'Referer': 'https://www.nzonscreen.com/',
                    'Origin': 'https://www.nzonscreen.com/',
                },
                **traverse_obj(playinfo, {
                    'id': ('uuid'),
                    'title': ('label', {strip_or_none}),
                    'description': ('description', {strip_or_none}),
                    'thumbnail': ('thumbnail', 'path'),
                    'duration': ('duration', {float_or_none}),
                }),
            }
        else:
            return self.playlist_result([{
                'display_id': video_id,
                'formats': list(self._extract_formats(playinfo)),
                'http_headers': {
                    'Referer': 'https://www.nzonscreen.com/',
                    'Origin': 'https://www.nzonscreen.com/',
                },
                **traverse_obj(playinfo, {
                    'id': ('uuid'),
                    'title': ('label', {strip_or_none}),
                    'description': ('description', {strip_or_none}),
                    'thumbnail': ('thumbnail', 'path'),
                    'duration': ('duration', {float_or_none}),
                }),
            } for playinfo in playlist], video_id, title)
