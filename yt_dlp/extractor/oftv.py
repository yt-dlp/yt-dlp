from .common import InfoExtractor
from ..utils import (
    int_or_none,
    str_or_none,
    traverse_obj,
    unified_timestamp,
    url_or_none,
    urljoin,
)


class OfTVNewIE(InfoExtractor):
    IE_NAME = 'oftv:video-new'
    _VALID_URL = r'https?://(?:www\.)?of\.tv/v/(?P<id>[^#/?]+)'
    _TESTS = [{
        'url': 'https://of.tv/v/zjtc6',
        'md5': 'fcdffb9e0a375851d53a939b45313a8c',
        'info_dict': {
            'id': 'zjtc6',
            'ext': 'mp4',
            'title': 'S1E1: Monte Cristo Sandwich',
            'thumbnails': 'mincount:3',
            'thumbnail': r're:https://.+\.(jpg|webp)',
            'description': 'md5:89a6a3404540e9d5a4ec9ffa63a85d4d',
            'duration': 1423,
            'timestamp': 1652394900,
            'upload_date': '20220512',
            'creators': 'count:4',
            'channel': 'This is Fire',
            'channel_id': '9iGia',
            'channel_url': 'https://of.tv/c/this-is-fire',
        },
    }]

    def _extract_data(self, json_data):
        thumbnails = []
        video_id = traverse_obj(json_data, ('unique_id', {str}))
        for k, v in json_data.get('thumbnail', {}).items():
            thumbnails.append({'url': v, 'preference': int(k)})
        m3u8_url = traverse_obj(json_data, ('video_src', {url_or_none}))
        return {
            'id': video_id,
            **traverse_obj(json_data, {
                'title': ('title', {str}),
                'alt_title': ('long_title', {str_or_none}),
                'description': ('description', {str_or_none}),
                'duration': ('duration', {int_or_none}),
                'timestamp': ('published_at', {unified_timestamp}),
                'creators': ('featured_creators', ..., (('nickname', 'of_handle'))),
                'season': ('season', {str_or_none}),
                'episode': ('episode', {str_or_none}),
                'channel': ('creator', 'channel_name', {str_or_none}),
                'channel_id': ('creator', 'unique_id', {str_or_none}),
                'channel_url': ('creator', 'oftv_handle', {urljoin('https://of.tv/c/')}),
            }),
            'formats': self._extract_m3u8_formats(m3u8_url, video_id),
            'thumbnails': thumbnails,
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        json_data = self._download_json(f'https://api.of.tv/v0/pages/videos/{video_id}', video_id)['data']['video']
        return self._extract_data(json_data)


class OfTVIE(InfoExtractor):
    IE_NAME = 'oftv:video'
    _VALID_URL = r'https?://(?:www\.)?of\.tv/video/(?P<id>[^#!/]+)'
    _TESTS = [{
        'url': 'https://of.tv/video/627d7d95b353db0001dadd1a',
        'md5': 'fcdffb9e0a375851d53a939b45313a8c',
        'info_dict': {
            'id': 'zjtc6',
            'ext': 'mp4',
            'title': 'S1E1: Monte Cristo Sandwich',
            'thumbnails': 'mincount:3',
            'thumbnail': r're:https://.+\.(jpg|webp)',
            'description': 'md5:89a6a3404540e9d5a4ec9ffa63a85d4d',
            'duration': 1423,
            'timestamp': 1652394900,
            'upload_date': '20220512',
            'creators': 'count:4',
            'channel': 'This is Fire',
            'channel_id': '9iGia',
            'channel_url': 'https://of.tv/c/this-is-fire',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        return self.url_result(self._og_search_url(webpage), OfTVNewIE)


class OfTVPlaylistNewIE(OfTVNewIE):
    IE_NAME = 'oftv:playlist-new'
    _VALID_URL = r'https?://(?:www\.)?of\.tv/c/(?P<id>[^/#?]+)'
    _TESTS = [{
        'url': 'https://of.tv/c/this-is-fire/',
        'info_dict': {
            'id': 'this-is-fire',
            'title': 'This is Fire',
        },
        'playlist_mincount': 44,
    }]

    def _entries(self, json_data):
        for entry in json_data.get('items', []):
            yield self._extract_data(entry)

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        json_data = self._download_json(f'https://api.of.tv/v0/pages/creators/{playlist_id}', playlist_id)['data']['creator_playlist']
        return self.playlist_result(self._entries(json_data), playlist_id, traverse_obj(json_data, ('label', {str})))


class OfTVPlaylistIE(InfoExtractor):
    IE_NAME = 'oftv:playlist'
    _VALID_URL = r'https?://(?:www\.)?of\.tv/creators/(?P<id>[^/#?]+)'
    _TESTS = [{
        'url': 'https://of.tv/creators/this-is-fire/',
        'info_dict': {
            'id': 'this-is-fire',
            'title': 'This is Fire',
        },
        'playlist_mincount': 44,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)
        return self.url_result(self._og_search_url(webpage), OfTVPlaylistNewIE)
