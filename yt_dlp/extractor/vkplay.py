from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class VKPlayBaseIE(InfoExtractor):
    def _extract_initial_state(self, url, video_id):
        webpage = self._download_webpage(url, video_id)
        initial_state_json = self._search_regex(r'id="initial-state"[^>]*>([^<]+)</script>', webpage, 'initial_state')
        initial_state = self._parse_json(initial_state_json, video_id, fatal=False)
        return initial_state

    def _parse_playurls(self, playurls, video_id):
        formats = []
        for playurl in playurls:
            if not playurl.get('url', None):
                continue
            elif '.m3u8' in playurl['url']:
                try:
                    formats.extend(self._extract_m3u8_formats(playurl['url'], video_id))
                except Exception:
                    pass
            else:
                formats.append(playurl)
        return formats


class VKPlayIE(VKPlayBaseIE):
    _VALID_URL = r'https?://vkplay\.live/(?P<username>\w+)/record/(?P<id>[a-f0-9\-]+)'
    _TESTS = [{
        'url': 'https://vkplay.live/zitsmann/record/f5e6e3b5-dc52-4d14-965d-0680dd2882da',
        'info_dict': {
            'id': 'f5e6e3b5-dc52-4d14-965d-0680dd2882da',
            'ext': 'mp4',
            'title': 'Atomic Heart (пробуем!) спасибо подписчику EKZO!',
            'uploader': 'ZitsmanN',
            'uploader_id': 13159830,
            'release_timestamp': 1683461378,
            'release_date': '20230507',
            'thumbnail': r're:https://images.vkplay.live/public_video_stream/record/f5e6e3b5-dc52-4d14-965d-0680dd2882da/preview\?change_time=\d+',
            'duration': 10608,
            'view_count': int,
            'like_count': int,
            'categories': ['Atomic Heart'],
        },
        'params': {'skip_download': True},
    }]

    def _real_extract(self, url):
        username, video_id = self._match_valid_url(url).groups()

        initial_state = self._extract_initial_state(url, video_id)
        record_info = traverse_obj(initial_state, ('record', 'currentRecord', 'data'))
        if not record_info:
            record_info = self._download_json('https://api.vkplay.live/v1/blog/{username}/public_video_stream/record/{video_id}', video_id)
        playurls = traverse_obj(record_info, ('data', 0, 'playerUrls', ..., {
            'url': ('url', {url_or_none}),
            'format_id': ('type', {str_or_none}),
        }))

        return {
            'id': video_id,
            'formats': self._parse_playurls(playurls, video_id),
            **traverse_obj(record_info, {
                'title': ('title', {str}),
                'release_timestamp': ('startTime', {int_or_none}),
                'uploader': ('blog', 'owner', 'nick', {str_or_none}),
                'uploader_id': ('blog', 'owner', 'id', {int_or_none}),
                'thumbnail': ('previewUrl', {url_or_none}),
                'duration': ('duration', {int_or_none}),
                'view_count': ('count', 'views', {int_or_none}),
                'like_count': ('count', 'likes', {int_or_none}),
                'categories': ('category', 'title', {lambda i: [str_or_none(i)]}),
            })
        }


class VKPlayLiveIE(VKPlayBaseIE):
    _VALID_URL = r'https?://vkplay\.live/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://vkplay.live/bayda',
        'info_dict': {
            'id': 'f02c321e-427b-408d-b12f-ae34e53e0ea2',
            'ext': 'mp4',
            'title': r're:эскапизм крута .*',
            'uploader': 'Bayda',
            'uploader_id': 12279401,
            'release_timestamp': 1687209962,
            'release_date': '20230619',
            'thumbnail': r're:https://images.vkplay.live/public_video_stream/12279401/preview\?change_time=\d+',
            'view_count': int,
            'concurrent_view_count': int,
            'like_count': int,
            'categories': ['EVE Online'],
            'live_status': 'is_live',
        },
        'skip': 'livestream',
        'params': {'skip_download': True},
    }]

    def _real_extract(self, url):
        username = self._match_id(url)

        initial_state = self._extract_initial_state(url, username)
        stream_info = traverse_obj(initial_state, ('stream', 'stream', 'data', 'stream'))
        if not stream_info:
            stream_info = self._download_json(f'https://api.vkplay.live/v1/blog/{username}/public_video_stream', username)
        playurls = traverse_obj(stream_info, ('data', 0, 'playerUrls', ..., {
            'url': ('url', {url_or_none}),
            'format_id': ('type', {str_or_none}),
        }))
        if not playurls:
            if not traverse_obj(stream_info, ('isOnline', {bool})):
                raise ExtractorError('Stream is offline', expected=True)

        return {
            'formats': self._parse_playurls(playurls, username),
            **traverse_obj(stream_info, {
                'id': ('id', {str}),
                'title': ('title', {str}),
                'release_timestamp': ('startTime', {int_or_none}),
                'uploader': ('user', 'nick', {str_or_none}),
                'uploader_id': ('user', 'id', {int_or_none}),
                'thumbnail': ('previewUrl', {url_or_none}),
                'view_count': ('count', 'views', {int_or_none}),
                'concurrent_view_count': ('count', 'viewers', {int_or_none}),
                'like_count': ('count', 'likes', {int_or_none}),
                'categories': ('category', 'title', {lambda i: [str_or_none(i)]}),
                'is_live': ('isOnline', {bool}),
            })
        }
