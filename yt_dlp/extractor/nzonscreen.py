from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
    smuggle_url,
    strip_or_none,
    traverse_obj,
    unsmuggle_url,
    url_or_none,
    urljoin,
)


class NZOnScreenIE(InfoExtractor):
    _VALID_URL = r'https?://www\.nzonscreen\.com/title/(?P<id>[^/?#]+)/?(?!series)'
    _TESTS = [{
        'url': 'https://www.nzonscreen.com/title/shoop-shoop-diddy-wop-cumma-cumma-wang-dang-1982',
        'info_dict': {
            'id': '726ed6585c6bfb30',
            'ext': 'mp4',
            'format_id': 'hi',
            'height': 480,
            'width': 640,
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
            'format_id': 'hi',
            'height': 480,
            'width': 640,
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
            'format_id': 'hi',
            'height': 540,
            'width': 718,
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
        'playlist': [{
            'info_dict': {
                'id': '8f4941d243e42210',
                'ext': 'mp4',
                'format_id': 'hd',
                'height': 574,
                'width': 740,
                'title': 'Flatmates ep 1',
                'display_id': 'flatmates-episode-one-1997',
                'thumbnail': r're:https://www\.nzonscreen\.com/content/images/.+\.jpg',
                'duration': 1355.0,
                'description': 'Episode 1',
            },
        }],
        'info_dict': {
            'id': 'flatmates-episode-one-1997',
            'title': 'Flatmates - Full Series',
        },
        'playlist_count': 5,
    }, {
        'url': 'https://www.nzonscreen.com/title/reluctant-hero-2008',
        'info_dict': {
            'id': '847f5c91af65d44b',
            'ext': 'mp4',
            'format_id': 'hi',
            'height': 360,
            'width': 640,
            'subtitles': {
                'en': [{'ext': 'vtt', 'url': 'https://www.nzonscreen.com/captions/3367'}],
            },
            'title': 'Reluctant Hero (clip 1)',
            'description': 'Part one of four from this full length documentary.',
            'display_id': 'reluctant-hero-2008',
            'duration': 1108.0,
            'thumbnail': r're:https://www\.nzonscreen\.com/content/images/.+\.jpg',
        },
        'params': {'noplaylist': True},
    }]

    def _extract_formats(self, playlist):
        formats = []
        for quality, (id_, url) in enumerate(traverse_obj(
                playlist, ('h264', {'lo': 'lo_res', 'hi': 'hi_res', 'hd': 'hd_res'}),
                expected_type=url_or_none).items()):
            if traverse_obj(playlist, ('h264', f'{id_}_res_mb', {float_or_none})):
                formats.append({
                    'url': url,
                    'format_id': id_,
                    'ext': 'mp4',
                    'quality': quality,
                    'filesize_approx': float_or_none(traverse_obj(
                        playlist, ('h264', f'{id_}_res_mb')), invscale=1024**2),
                })
        if formats:
            formats[-1].update(traverse_obj(playlist, {
                'height': ('height', {int_or_none}),
                'width': ('width', {int_or_none}),
            }))
        return formats

    def _extract_from_api_resp(self, vid_info, is_single_vid, title, video_id):
        return {
            'alt_title': title if is_single_vid else None,
            'display_id': video_id,
            'http_headers': {
                'Referer': 'https://www.nzonscreen.com/',
                'Origin': 'https://www.nzonscreen.com/',
            },
            'subtitles': {'en': [{
                'url': traverse_obj(vid_info, ('h264', 'caption_url', {urljoin('https://www.nzonscreen.com')})),
                'ext': 'vtt',
            }]},
            'formats': self._extract_formats(vid_info),
            **traverse_obj(vid_info, {
                'id': 'uuid',
                'title': ('label', {strip_or_none}),
                'description': ('description', {strip_or_none}),
                'thumbnail': ('thumbnail', 'path'),
                'duration': ('duration', {float_or_none}),
            }),
        }

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        ep_idx = smuggled_data.get('ep')
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        title = strip_or_none((
            self._html_extract_title(webpage, default=None)
            or self._og_search_title(webpage)).rsplit('|', 2)[0])
        playlist = self._download_json(
            f'https://www.nzonscreen.com/html5/video_data/{video_id}', video_id,
            'Downloading media data')
        playlist_len = len(playlist)

        if ep_idx is None and playlist_len > 1 and self._yes_playlist(video_id, traverse_obj(playlist, (0, 'id'))):
            return self.playlist_result(
                # the site's m3u8 URLs are short-lived, we have to extract them just before downloading
                [self.url_result(smuggle_url(url, {'ep': idx}), NZOnScreenIE.ie_key()) for idx in range(playlist_len)],
                playlist_id=video_id, playlist_title=title)

        vid_info = playlist[ep_idx or 0]
        return {
            'alt_title': title if playlist_len == 1 else None,
            'display_id': video_id,
            'http_headers': {
                'Referer': 'https://www.nzonscreen.com/',
                'Origin': 'https://www.nzonscreen.com/',
            },
            'subtitles': {'en': [{
                'url': traverse_obj(vid_info, ('h264', 'caption_url', {urljoin('https://www.nzonscreen.com')})),
                'ext': 'vtt',
            }]},
            'formats': self._extract_formats(vid_info),
            **traverse_obj(vid_info, {
                'id': 'uuid',
                'title': ('label', {strip_or_none}),
                'description': ('description', {strip_or_none}),
                'thumbnail': ('thumbnail', 'path'),
                'duration': ('duration', {float_or_none}),
            }),
        }
