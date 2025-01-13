import secrets

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class EggsBaseIE(InfoExtractor):
    _API_HEADERS = {
        'Accept': '*/*',
        'apVersion': '8.2.00',
        'deviceName': 'Android',
    }

    @staticmethod
    def _generate_random_device_id():
        return secrets.token_hex(8)

    def _download_eggs_json(self, url, music_id):
        headers = self._API_HEADERS.copy()
        headers['deviceId'] = self._generate_random_device_id()
        return self._download_json(url, video_id=music_id, headers=headers)

    def _extract_music_info(self, data, song_id):
        music_info = traverse_obj(data, {
            'id': ('musicId', {str_or_none}, {lambda x: x or song_id}),
            'title': ('musicTitle', {str}, {lambda x: x or 'Unknown Title'}),
            'url': ('musicDataPath', {url_or_none}),
            'uploader': ('artist', 'displayName', {str}, {lambda x: x or 'Unknown Artist'}),
            'thumbnail': ('imageDataPath', {url_or_none}),
            'youtube_url': ('youtubeUrl', {url_or_none}),
            'youtube_id': ('youtubeVideoId', {str_or_none}),
            'source_type': ('sourceType', {int}),
            'vcodec': (None, {lambda x: 'none'}),
        }, get_all=False)

        if not music_info.get('url') and not (music_info.get('source_type') == 2 and music_info.get('youtube_url')):
            raise ExtractorError('Audio URL not found (possibly an unsupported sourceType)', expected=True)

        return music_info


class EggsIE(EggsBaseIE):
    IE_NAME = 'eggs:single'
    _VALID_URL = r'https?://eggs\.mu/artist/[^/]+/song/(?P<song_id>[^/]+)'

    _TESTS = [{
        'url': 'https://eggs.mu/artist/32_sunny_girl/song/0e95fd1d-4d61-4d5b-8b18-6092c551da90',
        'info_dict': {
            'id': '0e95fd1d-4d61-4d5b-8b18-6092c551da90',
            'ext': 'm4a',
            'title': 'シネマと信号',
            'uploader': 'Sunny Girl',
            'source_type': 1,
            'thumbnail': r're:https?://.*\.jpg(?:\?.*)?$',
        },
    }, {
        'url': 'https://eggs.mu/artist/KAMO_3pband/song/1d4bc45f-1af6-47a9-8b30-a70cae350b4f',
        'info_dict': {
            'id': '80cLKA2wnoA',
            'ext': 'mp4',
            'title': 'KAMO「いい女だから」Audio',
            'uploader': 'KAMO',
            'live_status': 'not_live',
            'channel_id': 'UCsHLBw2__5Q9y55skXPotOg',
            'channel_follower_count': int,
            'description': 'md5:d260da711ecbec3e720293dc11401b87',
            'availability': 'public',
            'uploader_id': '@KAMO_band',
            'upload_date': '20240925',
            'thumbnail': 'https://i.ytimg.com/vi/80cLKA2wnoA/maxresdefault.jpg',
            'comment_count': int,
            'channel_url': 'https://www.youtube.com/channel/UCsHLBw2__5Q9y55skXPotOg',
            'view_count': int,
            'duration': 151,
            'like_count': int,
            'channel': 'KAMO',
            'playable_in_embed': True,
            'uploader_url': 'https://www.youtube.com/@KAMO_band',
            'tags': [],
            'timestamp': 1727271121,
            'age_limit': 0,
            'categories': ['People & Blogs'],
        },
        'add_ie': ['Youtube'],
        'params': {'skip_download': 'Youtube'},
    }]

    def _real_extract(self, url):
        song_id = self._match_valid_url(url).group('song_id')
        json_data = self._download_eggs_json(
            f'https://app-front-api.eggs.mu/v1/musics/{song_id}', music_id=song_id)
        music_info = self._extract_music_info(json_data, song_id)

        if music_info['source_type'] == 2 and music_info['youtube_url']:
            return self.url_result(
                music_info['youtube_url'], ie='Youtube', video_id=music_info['youtube_id'])

        return music_info


class EggsArtistIE(EggsBaseIE):
    IE_NAME = 'eggs:artist'
    _VALID_URL = r'https?://eggs\.mu/artist/(?P<artist_id>[^/]+)$'

    _TESTS = [
        {
            'url': 'https://eggs.mu/artist/32_sunny_girl',
            'info_dict': {
                'id': '32_sunny_girl',
                'title': 'Sunny Girl',
            },
            'playlist_mincount': 18,
        },
        {
            'url': 'https://eggs.mu/artist/KAMO_3pband',
            'info_dict': {
                'id': 'KAMO_3pband',
                'title': 'KAMO',
            },
            'playlist_mincount': 2,
        },
    ]

    def _real_extract(self, url):
        artist_id = self._match_valid_url(url).group('artist_id')
        json_data = self._download_eggs_json(
            f'https://app-front-api.eggs.mu/v1/artists/{artist_id}/musics', music_id=artist_id)
        items = traverse_obj(json_data, 'data', default=[])
        entries = []
        display_name = None

        for item in items:
            music_info = self._extract_music_info(item, '')
            if not music_info['id']:
                continue

            if not display_name:
                display_name = music_info['uploader']

            if music_info['source_type'] == 2 and music_info['youtube_url']:
                entries.append(
                    self.url_result(
                        music_info['youtube_url'], ie='Youtube', video_id=music_info['youtube_id']))
                continue

            if not music_info.get('url'):
                continue

            entries.append(music_info)

        return self.playlist_result(
            entries,
            playlist_id=artist_id,
            playlist_title=display_name or artist_id)
