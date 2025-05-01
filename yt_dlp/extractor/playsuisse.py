import base64
import hashlib
import json
import uuid

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_qs,
    traverse_obj,
    update_url_query,
    urlencode_postdata,
)


class PlaySuisseIE(InfoExtractor):
    _NETRC_MACHINE = 'playsuisse'
    _VALID_URL = r'https?://(?:www\.)?playsuisse\.ch/(?:watch|detail)/(?:[^#]*[?&]episodeId=)?(?P<id>[0-9]+)'
    
    _GRAPHQL_QUERY = '''
        query AssetWatch($assetId: ID!) {
            assetV2(id: $assetId) {
                ...Asset
                episodes {
                    ...Asset
                }
            }
        }
        fragment Asset on AssetV2 {
            id
            name
            description
            duration
            episodeNumber
            seasonNumber
            seriesName
            medias {
                type
                url
            }
            thumbnail16x9 {
                ...ImageDetails
            }
            thumbnail2x3 {
                ...ImageDetails
            }
            thumbnail16x9WithTitle {
                ...ImageDetails
            }
            thumbnail2x3WithTitle {
                ...ImageDetails
            }
        }
        fragment ImageDetails on AssetImage {
            id
            url
        }'''
    _CLIENT_ID = '1e33f1bf-8bf3-45e4-bbd9-c9ad934b5fca'
    _LOGIN_BASE = 'https://account.srgssr.ch'
    _ID_TOKEN = None

    def _perform_login(self, username, password):
        code_verifier = uuid.uuid4().hex + uuid.uuid4().hex + uuid.uuid4().hex
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()).decode().rstrip('=')

        request_id = parse_qs(self._request_webpage(
            f'{self._LOGIN_BASE}/authz-srv/authz', None, 'Requesting session ID', query={
                'client_id': self._CLIENT_ID,
                'redirect_uri': 'https://www.playsuisse.ch/auth',
                'scope': 'email profile openid offline_access',
                'response_type': 'code',
                'code_challenge': code_challenge,
                'code_challenge_method': 'S256',
                'view_type': 'login',
            }).url)['requestId'][0]

        try:
            exchange_id = self._download_json(
                f'{self._LOGIN_BASE}/verification-srv/v2/authenticate/initiate/password', None,
                'Submitting username', headers={'content-type': 'application/json'}, data=json.dumps({
                    'usage_type': 'INITIAL_AUTHENTICATION',
                    'request_id': request_id,
                    'medium_id': 'PASSWORD',
                    'type': 'password',
                    'identifier': username,
                }).encode())['data']['exchange_id']['exchange_id']
        except ExtractorError:
            raise ExtractorError('Invalid username', expected=True)

        try:
            login_data = self._download_json(
                f'{self._LOGIN_BASE}/verification-srv/v2/authenticate/authenticate/password', None,
                'Submitting password', headers={'content-type': 'application/json'}, data=json.dumps({
                    'requestId': request_id,
                    'exchange_id': exchange_id,
                    'type': 'password',
                    'password': password,
                }).encode())['data']
        except ExtractorError:
            raise ExtractorError('Invalid password', expected=True)

        authorization_code = parse_qs(self._request_webpage(
            f'{self._LOGIN_BASE}/login-srv/verification/login', None, 'Logging in',
            data=urlencode_postdata({
                'requestId': request_id,
                'exchange_id': login_data['exchange_id']['exchange_id'],
                'verificationType': 'password',
                'sub': login_data['sub'],
                'status_id': login_data['status_id'],
                'rememberMe': True,
                'lat': '',
                'lon': '',
            })).url)['code'][0]

        self._ID_TOKEN = self._download_json(
            f'{self._LOGIN_BASE}/proxy/token', None, 'Downloading token', data=b'', query={
                'client_id': self._CLIENT_ID,
                'redirect_uri': 'https://www.playsuisse.ch/auth',
                'code': authorization_code,
                'code_verifier': code_verifier,
                'grant_type': 'authorization_code',
            })['id_token']

        if not self._ID_TOKEN:
            raise ExtractorError('Login failed')

    def _get_media_data(self, media_id):
        response = self._download_json(
            'https://www.playsuisse.ch/api/graphql',
            media_id, data=json.dumps({
                'operationName': 'AssetWatch',
                'query': self._GRAPHQL_QUERY,
                'variables': {'assetId': media_id},
            }).encode(),
            headers={'Content-Type': 'application/json', 'locale': 'fr'})

        return response['data']['assetV2']

    def _real_extract(self, url):
        if not self._ID_TOKEN:
            self.raise_login_required(method='password')

        media_id = self._match_id(url)
        media_data = self._get_media_data(media_id)
        info = self._extract_single(media_data)
        
        if info is None:
            raise ExtractorError('Unable to extract media information')
        
        if media_data.get('episodes'):
            info.update({
                '_type': 'playlist',
                'entries': [
                    self._extract_single(episode)
                    for episode in media_data['episodes']
                    if self._extract_single(episode) is not None
                ],
            })
        return info

    def _extract_single(self, media_data):
        if not media_data or 'id' not in media_data:
            return None

        thumbnails = traverse_obj(media_data, lambda k, _: k.startswith('thumbnail'))

        formats, subtitles = [], {}
        for media in traverse_obj(media_data, 'medias', default=[]):
            if not media.get('url') or media.get('type') != 'HLS':
                continue
            f, subs = self._extract_m3u8_formats_and_subtitles(
                update_url_query(media['url'], {'id_token': self._ID_TOKEN}),
                media_data['id'], 'mp4', m3u8_id='HLS', fatal=False)
            formats.extend(f)
            self._merge_subtitles(subs, target=subtitles)

        series_name = media_data.get('seriesName', '')
        episode_name = media_data.get('name', '')
        
        if series_name and episode_name:
            title = f"{series_name} - {episode_name}"
        else:
            title = episode_name or series_name or 'Unknown Title'

        return {
            'id': media_data['id'],
            'title': title,
            'description': media_data.get('description'),
            'thumbnails': thumbnails,
            'duration': int_or_none(media_data.get('duration')),
            'formats': formats,
            'subtitles': subtitles,
            'series': series_name,
            'season_number': int_or_none(media_data.get('seasonNumber')),
            'episode': episode_name if media_data.get('episodeNumber') else None,
            'episode_number': int_or_none(media_data.get('episodeNumber')),
        }
