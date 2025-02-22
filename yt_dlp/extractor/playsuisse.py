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
    _TESTS = [
        {
            # Old URL
            'url': 'https://www.playsuisse.ch/watch/763211/0',
            'only_matching': True,
        },
        {
            # episode in a series
            'url': 'https://www.playsuisse.ch/watch/763182?episodeId=763211',
            'md5': '82df2a470b2dfa60c2d33772a8a60cf8',
            'info_dict': {
                'id': '763211',
                'ext': 'mp4',
                'title': 'Knochen',
                'description': 'md5:8ea7a8076ba000cd9e8bc132fd0afdd8',
                'duration': 3344,
                'series': 'Wilder',
                'season': 'Season 1',
                'season_number': 1,
                'episode': 'Knochen',
                'episode_number': 1,
                'thumbnail': 're:https://playsuisse-img.akamaized.net/',
            },
        }, {
            # film
            'url': 'https://www.playsuisse.ch/watch/808675',
            'md5': '818b94c1d2d7c4beef953f12cb8f3e75',
            'info_dict': {
                'id': '808675',
                'ext': 'mp4',
                'title': 'Der Läufer',
                'description': 'md5:9f61265c7e6dcc3e046137a792b275fd',
                'duration': 5280,
                'thumbnail': 're:https://playsuisse-img.akamaized.net/',
            },
        }, {
            # series (treated as a playlist)
            'url': 'https://www.playsuisse.ch/detail/1115687',
            'info_dict': {
                'description': 'md5:e4a2ae29a8895823045b5c3145a02aa3',
                'id': '1115687',
                'series': 'They all came out to Montreux',
                'title': 'They all came out to Montreux',
            },
            'playlist': [{
                'info_dict': {
                    'description': 'md5:f2462744834b959a31adc6292380cda2',
                    'duration': 3180,
                    'episode': 'Folge 1',
                    'episode_number': 1,
                    'id': '1112663',
                    'season': 'Season 1',
                    'season_number': 1,
                    'series': 'They all came out to Montreux',
                    'thumbnail': 're:https://playsuisse-img.akamaized.net/',
                    'title': 'Folge 1',
                    'ext': 'mp4',
                },
            }, {
                'info_dict': {
                    'description': 'md5:9dfd308699fe850d3bce12dc1bad9b27',
                    'duration': 2935,
                    'episode': 'Folge 2',
                    'episode_number': 2,
                    'id': '1112661',
                    'season': 'Season 1',
                    'season_number': 1,
                    'series': 'They all came out to Montreux',
                    'thumbnail': 're:https://playsuisse-img.akamaized.net/',
                    'title': 'Folge 2',
                    'ext': 'mp4',
                },
            }, {
                'info_dict': {
                    'description': 'md5:14a93a3356b2492a8f786ab2227ef602',
                    'duration': 2994,
                    'episode': 'Folge 3',
                    'episode_number': 3,
                    'id': '1112664',
                    'season': 'Season 1',
                    'season_number': 1,
                    'series': 'They all came out to Montreux',
                    'thumbnail': 're:https://playsuisse-img.akamaized.net/',
                    'title': 'Folge 3',
                    'ext': 'mp4',
                },
            }],
        },
    ]

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
        # NOTE In the web app, the "locale" header is used to switch between languages,
        # However this doesn't seem to take effect when passing the header here.
        response = self._download_json(
            'https://www.playsuisse.ch/api/graphql',
            media_id, data=json.dumps({
                'operationName': 'AssetWatch',
                'query': self._GRAPHQL_QUERY,
                'variables': {'assetId': media_id},
            }).encode(),
            headers={'Content-Type': 'application/json', 'locale': 'de'})

        return response['data']['assetV2']

    def _real_extract(self, url):
        if not self._ID_TOKEN:
            self.raise_login_required(method='password')

        media_id = self._match_id(url)
        media_data = self._get_media_data(media_id)
        info = self._extract_single(media_data)
        if media_data.get('episodes'):
            info.update({
                '_type': 'playlist',
                'entries': map(self._extract_single, media_data['episodes']),
            })
        return info

    def _extract_single(self, media_data):
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

        return {
            'id': media_data['id'],
            'title': media_data.get('name'),
            'description': media_data.get('description'),
            'thumbnails': thumbnails,
            'duration': int_or_none(media_data.get('duration')),
            'formats': formats,
            'subtitles': subtitles,
            'series': media_data.get('seriesName'),
            'season_number': int_or_none(media_data.get('seasonNumber')),
            'episode': media_data.get('name') if media_data.get('episodeNumber') else None,
            'episode_number': int_or_none(media_data.get('episodeNumber')),
        }
