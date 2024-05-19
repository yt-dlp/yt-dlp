import base64
import json
import uuid

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    js_to_json,
    traverse_obj,
    urljoin,
)


class CaracolTvPlayIE(InfoExtractor):
    _VALID_URL = r'https?://play\.caracoltv\.com/videoDetails/(?P<id>[^/?#]+)'
    _NETRC_MACHINE = 'caracoltv-play'

    _TESTS = [{
        'url': 'https://play.caracoltv.com/videoDetails/OTo4NGFmNjUwOWQ2ZmM0NTg2YWRiOWU0MGNhOWViOWJkYQ==',
        'info_dict': {
            'id': 'OTo4NGFmNjUwOWQ2ZmM0NTg2YWRiOWU0MGNhOWViOWJkYQ==',
            'title': 'La teoría del promedio',
            'description': 'md5:1cdd6d2c13f19ef0d9649ab81a023ac3',
        },
        'playlist_count': 6,
    }, {
        'url': 'https://play.caracoltv.com/videoDetails/OTo3OWM4ZTliYzQxMmM0MTMxYTk4Mjk2YjdjNGQ4NGRkOQ==/ella?season=0',
        'info_dict': {
            'id': 'OTo3OWM4ZTliYzQxMmM0MTMxYTk4Mjk2YjdjNGQ4NGRkOQ==',
            'title': 'Ella',
            'description': 'md5:a639b1feb5ddcc0cff92a489b4e544b8',
        },
        'playlist_count': 10,
    }, {
        'url': 'https://play.caracoltv.com/videoDetails/OTpiYTY1YTVmOTI5MzI0ZWJhOGZiY2Y3MmRlOWZlYmJkOA==/la-vuelta-al-mundo-en-80-risas-2022?season=0',
        'info_dict': {
            'id': 'OTpiYTY1YTVmOTI5MzI0ZWJhOGZiY2Y3MmRlOWZlYmJkOA==',
            'title': 'La vuelta al mundo en 80 risas 2022',
            'description': 'md5:e97aac36106e5c37ebf947b3350106a4',
        },
        'playlist_count': 17,
    }, {
        'url': 'https://play.caracoltv.com/videoDetails/MzoxX3BwbjRmNjB1',
        'only_matching': True,
    }]

    _USER_TOKEN = None

    def _extract_app_token(self, webpage):
        config_js_path = self._search_regex(
            r'<script[^>]+src\s*=\s*"([^"]+coreConfig.js[^"]+)', webpage, 'config js url', fatal=False)

        mediation_config = {} if not config_js_path else self._search_json(
            r'mediation\s*:', self._download_webpage(
                urljoin('https://play.caracoltv.com/', config_js_path), None, fatal=False, note='Extracting JS config'),
            'mediation_config', None, transform_source=js_to_json, fatal=False)

        key = traverse_obj(
            mediation_config, ('live', 'key')) or '795cd9c089a1fc48094524a5eba85a3fca1331817c802f601735907c8bbb4f50'
        secret = traverse_obj(
            mediation_config, ('live', 'secret')) or '64dec00a6989ba83d087621465b5e5d38bdac22033b0613b659c442c78976fa0'

        return base64.b64encode(f'{key}:{secret}'.encode()).decode()

    def _perform_login(self, email, password):
        webpage = self._download_webpage('https://play.caracoltv.com/', None, fatal=False)
        app_token = self._extract_app_token(webpage)

        bearer_token = self._download_json(
            'https://eu-gateway.inmobly.com/applications/oauth', None, data=b'', note='Retrieving bearer token',
            headers={'Authorization': f'Basic {app_token}'})['token']

        self._USER_TOKEN = self._download_json(
            'https://eu-gateway.inmobly.com/user/login', None, note='Performing login', headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {bearer_token}',
            }, data=json.dumps({
                'device_data': {
                    'device_id': str(uuid.uuid4()),
                    'device_token': '',
                    'device_type': 'web'
                },
                'login_data': {
                    'enabled': True,
                    'email': email,
                    'password': password,
                }
            }).encode())['user_token']

    def _extract_video(self, video_data, series_id=None, season_id=None, season_number=None):
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(video_data['stream_url'], series_id, 'mp4')

        return {
            'id': video_data['id'],
            'title': video_data.get('name'),
            'description': video_data.get('description'),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': traverse_obj(
                video_data, ('extra_thumbs', ..., {'url': 'thumb_url', 'height': 'height', 'width': 'width'})),
            'series_id': series_id,
            'season_id': season_id,
            'season_number': int_or_none(season_number),
            'episode_number': int_or_none(video_data.get('item_order')),
            'is_live': video_data.get('entry_type') == 3,
        }

    def _extract_series_seasons(self, seasons, series_id):
        for season in seasons:
            api_response = self._download_json(
                'https://eu-gateway.inmobly.com/feed', series_id, query={'season_id': season['id']},
                headers={'Authorization': f'Bearer {self._USER_TOKEN}'})

            season_number = season.get('order')
            for episode in api_response['items']:
                yield self._extract_video(episode, series_id, season['id'], season_number)

    def _real_extract(self, url):
        series_id = self._match_id(url)

        if self._USER_TOKEN is None:
            self._perform_login('guest@inmobly.com', 'Test@gus1')

        api_response = self._download_json(
            'https://eu-gateway.inmobly.com/feed', series_id, query={'include_ids': series_id},
            headers={'Authorization': f'Bearer {self._USER_TOKEN}'})['items'][0]

        if not api_response.get('seasons'):
            return self._extract_video(api_response)

        return self.playlist_result(
            self._extract_series_seasons(api_response['seasons'], series_id),
            series_id, **traverse_obj(api_response, {
                'title': 'name',
                'description': 'description',
            }))
