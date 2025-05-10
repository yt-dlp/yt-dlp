import base64
import hashlib
import json
import uuid

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    join_nonempty,
    parse_qs,
    traverse_obj,
    update_url_query,
    urlencode_postdata,
)
from ..utils.traversal import unpack


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
            'md5': 'e20d1ede6872a03b41905ca1060a1ef2',
            'info_dict': {
                'id': '763211',
                'ext': 'mp4',
                'title': 'Knochen',
                'description': 'md5:3bdd80e2ce20227c47aab1df2a79a519',
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
            'url': 'https://www.playsuisse.ch/detail/2573198',
            'md5': '1f115bb0a5191477b1a5771643a4283d',
            'info_dict': {
                'id': '2573198',
                'ext': 'mp4',
                'title': 'Azor',
                'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
                'genres': ['Fiction'],
                'creators': ['Andreas Fontana'],
                'cast': ['Fabrizio Rongione', 'Stéphanie Cléau', 'Gilles Privat', 'Alexandre Trocki'],
                'location': 'France; Argentine',
                'release_year': 2021,
                'duration': 5981,
                'thumbnail': 're:https://playsuisse-img.akamaized.net/',
            },
        }, {
            # series (treated as a playlist)
            'url': 'https://www.playsuisse.ch/detail/1115687',
            'info_dict': {
                'id': '1115687',
                'series': 'They all came out to Montreux',
                'title': 'They all came out to Montreux',
                'description': 'md5:0fefd8c5b4468a0bb35e916887681520',
                'genres': ['Documentary'],
                'creators': ['Oliver Murray'],
                'location': 'Switzerland',
                'release_year': 2021,
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
            descriptionLong
            year
            contentTypes
            directors
            mainCast
            productionCountries
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

    def _get_media_data(self, media_id, locale=None):
        response = self._download_json(
            'https://www.playsuisse.ch/api/graphql',
            media_id, data=json.dumps({
                'operationName': 'AssetWatch',
                'query': self._GRAPHQL_QUERY,
                'variables': {'assetId': media_id},
            }).encode(),
            headers={'Content-Type': 'application/json', 'locale': locale or 'de'})

        return response['data']['assetV2']

    def _real_extract(self, url):
        if not self._ID_TOKEN:
            self.raise_login_required(method='password')

        media_id = self._match_id(url)
        media_data = self._get_media_data(media_id, traverse_obj(parse_qs(url), ('locale', 0)))
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
            'thumbnails': thumbnails,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(media_data, {
                'id': ('id', {str}),
                'title': ('name', {str}),
                'description': (('descriptionLong', 'description'), {str}, any),
                'genres': ('contentTypes', ..., {str}),
                'creators': ('directors', ..., {str}),
                'cast': ('mainCast', ..., {str}),
                'location': ('productionCountries', ..., {str}, all, {unpack(join_nonempty, delim='; ')}, filter),
                'release_year': ('year', {str}, {lambda x: x[:4]}, {int_or_none}),
                'duration': ('duration', {int_or_none}),
                'series': ('seriesName', {str}),
                'season_number': ('seasonNumber', {int_or_none}),
                'episode': ('name', {str}, {lambda x: x if media_data['episodeNumber'] is not None else None}),
                'episode_number': ('episodeNumber', {int_or_none}),
            }),
        }
