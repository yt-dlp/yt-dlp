import base64

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    try_get,
)
from ..utils.traversal import traverse_obj


class PokerGoBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'pokergo'
    _AUTH_TOKEN = None
    _PROPERTY_ID = '1dfb3940-7d53-4980-b0b0-f28b369a000d'

    def _perform_login(self, username, password):
        if self._AUTH_TOKEN:
            return
        self.report_login()
        PokerGoBaseIE._AUTH_TOKEN = self._download_json(
            f'https://subscription.pokergo.com/properties/{self._PROPERTY_ID}/sign-in', None,
            headers={'authorization': f'Basic {base64.b64encode(f"{username}:{password}".encode()).decode()}'},
            data=b'')['meta']['token']
        if not self._AUTH_TOKEN:
            raise ExtractorError('Unable to get Auth Token.', expected=True)

    def _real_initialize(self):
        if not self._AUTH_TOKEN:
            self.raise_login_required(method='password')


class PokerGoIE(PokerGoBaseIE):
    _VALID_URL = r'https?://(?:www\.)?pokergo\.com/videos/(?P<id>[^&$#/?]+)'

    _TESTS = [{
        'url': 'https://www.pokergo.com/videos/2a70ec4e-4a80-414b-97ec-725d9b72a7dc',
        'info_dict': {
            'id': 'aVLOxDzY',
            'ext': 'mp4',
            'title': 'Poker After Dark | Season 12 (2020) | Cry Me a River | Episode 2',
            'description': 'md5:c7a8c29556cbfb6eb3c0d5d622251b71',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/aVLOxDzY/poster.jpg?width=720',
            'timestamp': 1608085715,
            'duration': 2700.12,
            'season_number': 12,
            'episode_number': 2,
            'series': 'poker after dark',
            'upload_date': '20201216',
            'season': 'Season 12',
            'episode': 'Episode 2',
            'display_id': '2a70ec4e-4a80-414b-97ec-725d9b72a7dc',
        },
        'params': {'skip_download': True},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data_json = self._download_json(
            f'https://api.pokergo.com/v2/properties/{self._PROPERTY_ID}/videos/{video_id}', video_id,
            headers={'authorization': f'Bearer {self._AUTH_TOKEN}'})['data']
        v_id = data_json['source']

        thumbnails = [{
            'url': image['url'],
            'id': image.get('label'),
            'width': image.get('width'),
            'height': image.get('height'),
        } for image in data_json.get('images') or [] if image.get('url')]
        series_json = traverse_obj(data_json, ('show_tags', lambda _, v: v['video_id'] == video_id, any)) or {}

        return {
            '_type': 'url_transparent',
            'display_id': video_id,
            'title': data_json.get('title'),
            'description': data_json.get('description'),
            'duration': data_json.get('duration'),
            'thumbnails': thumbnails,
            'season_number': series_json.get('season'),
            'episode_number': series_json.get('episode_number'),
            'series': try_get(series_json, lambda x: x['tag']['name']),
            'url': f'https://cdn.jwplayer.com/v2/media/{v_id}',
        }


class PokerGoCollectionIE(PokerGoBaseIE):
    _VALID_URL = r'https?://(?:www\.)?pokergo\.com/collections/(?P<id>[^&$#/?]+)'

    _TESTS = [{
        'url': 'https://www.pokergo.com/collections/19ffe481-5dae-481a-8869-75cc0e3c4700',
        'playlist_mincount': 13,
        'info_dict': {
            'id': '19ffe481-5dae-481a-8869-75cc0e3c4700',
        },
    }]

    def _entries(self, playlist_id):
        data_json = self._download_json(
            f'https://api.pokergo.com/v2/properties/{self._PROPERTY_ID}/collections/{playlist_id}?include=entities',
            playlist_id, headers={'authorization': f'Bearer {self._AUTH_TOKEN}'})['data']
        for video in data_json.get('collection_video') or []:
            video_id = video.get('id')
            if video_id:
                yield self.url_result(
                    f'https://www.pokergo.com/videos/{video_id}',
                    ie=PokerGoIE.ie_key(), video_id=video_id)

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        return self.playlist_result(self._entries(playlist_id), playlist_id=playlist_id)
