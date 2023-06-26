import base64
import binascii
import json
import time
import uuid

from .common import InfoExtractor
from ..compat import compat_HTTPError
from ..dependencies import Cryptodome
from ..utils import (
    ExtractorError,
    int_or_none,
    jwt_decode_hs256,
    traverse_obj,
    url_or_none,
    urlencode_postdata,
)


class StacommuBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'stacommu'
    _API_PATH = None
    _REAL_TOKEN = None
    _TOKEN_EXPIRY = None
    _REFRESH_TOKEN = None
    _DEVICE_ID = None
    _LOGIN_QUERY = {'key': 'AIzaSyCR9czxhH2eWuijEhTNWBZ5MCcOYEUTAhg'}
    _LOGIN_HEADERS = {
        'Accept': '*/*',
        'Content-Type': 'application/json',
        'X-Client-Version': 'Chrome/JsCore/9.9.4/FirebaseCore-web',
        'Referer': 'https://www.stacommu.jp/',
        'Origin': 'https://www.stacommu.jp',
    }

    @property
    def _TOKEN(self):
        if self._REAL_TOKEN and self._TOKEN_EXPIRY <= int(time.time()):
            self._refresh_token()

        return self._REAL_TOKEN

    @_TOKEN.setter
    def _TOKEN(self, value):
        self._REAL_TOKEN = value

        expiry = traverse_obj(value, ({jwt_decode_hs256}, 'exp', {int_or_none}))
        if not expiry:
            raise ExtractorError('There was a problem with the auth token')
        self._TOKEN_EXPIRY = expiry

    def _perform_login(self, username, password):
        try:
            login = self._download_json(
                'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword', None,
                'Logging in', query=self._LOGIN_QUERY, headers=self._LOGIN_HEADERS, data=json.dumps({
                    'returnSecureToken': True,
                    'email': username,
                    'password': password,
                }, separators=(',', ':')).encode())
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 400:
                message = traverse_obj(
                    self._parse_json(e.cause.read().decode(), None), ('error', 'message', {str}))
                self.report_warning(f'Unable to log in: {message}')
            else:
                raise
        else:
            self._REFRESH_TOKEN = traverse_obj(login, ('refreshToken', {str}))
            if not self._REFRESH_TOKEN:
                self.report_warning('No refresh token was granted')
            self._TOKEN = traverse_obj(login, ('idToken', {str}))

    def _real_initialize(self):
        if StacommuBaseIE._DEVICE_ID:
            return

        StacommuBaseIE._DEVICE_ID = self._configuration_arg('device_id', [None], ie_key='Stacommu')[0]
        if not StacommuBaseIE._DEVICE_ID:
            StacommuBaseIE._DEVICE_ID = self.cache.load(self._NETRC_MACHINE, 'device_id')
            if StacommuBaseIE._DEVICE_ID:
                return
            StacommuBaseIE._DEVICE_ID = str(uuid.uuid4())

        self.cache.store(self._NETRC_MACHINE, 'device_id', StacommuBaseIE._DEVICE_ID)

    def _refresh_token(self):
        refresh = self._download_json(
            'https://securetoken.googleapis.com/v1/token', None, 'Refreshing token',
            query=self._LOGIN_QUERY, data=urlencode_postdata({
                'grant_type': 'refresh_token',
                'refresh_token': self._REFRESH_TOKEN,
            }), headers={
                **self._LOGIN_HEADERS,
                'Content-Type': 'application/x-www-form-urlencoded',
            })
        if traverse_obj(refresh, ('refresh_token', {str})):
            self._REFRESH_TOKEN = refresh['refresh_token']
        token = traverse_obj(refresh, 'access_token', 'id_token', expected_type=str)
        if not token:
            raise ExtractorError('No auth token returned from refresh request')
        self._TOKEN = token

    def _call_api(self, video_id, param='', msg='API', auth=True, data=None, query={}, fatal=True):
        headers = {'CA-CID': ''}
        if data:
            headers['Content-Type'] = 'application/json;charset=utf-8'
            data = json.dumps(data, separators=(',', ':')).encode()
        if auth and self._TOKEN:
            headers['Authorization'] = f'Bearer {self._TOKEN}'
        return self._download_json(
            f'https://api.stacommu.jp/v1/{self._API_PATH}/{video_id}{param}', video_id,
            note=f'Downloading {msg} JSON', errnote=f'Failed to download {msg} JSON',
            data=data, headers=headers, query=query, fatal=fatal)

    def _call_encrypted_api(self, video_id, param='', msg='API', data={}, query={}, fatal=True):
        if not Cryptodome.RSA:
            raise ExtractorError('pycryptodomex not found. Please install', expected=True)
        private_key = Cryptodome.RSA.generate(2048)
        cipher = Cryptodome.PKCS1_OAEP.new(private_key, hashAlgo=Cryptodome.SHA1)

        def decrypt(data):
            if not data:
                return None
            try:
                return cipher.decrypt(base64.b64decode(data)).decode()
            except (ValueError, binascii.Error) as e:
                raise ExtractorError(f'Could not decrypt data: {e}')

        token = base64.b64encode(private_key.public_key().export_key('DER')).decode()
        api_json = self._call_api(video_id, param, msg, data={
            'deviceId': self._DEVICE_ID,
            'token': token,
            **data,
        }, query=query, fatal=fatal)
        return api_json, decrypt

    def _download_metadata(self, url, video_id, lang, props_key):
        metadata = self._call_api(video_id, msg='metadata', query={'al': 'ja'}, auth=False, fatal=False)
        if not metadata:
            webpage = self._download_webpage(url, video_id)
            nextjs_data = self._search_nextjs_data(webpage, video_id)
            metadata = traverse_obj(nextjs_data, ('props', 'pageProps', props_key, {dict})) or {}
        return metadata

    def _get_formats(self, data, path, video_id=None):
        hls_url = traverse_obj(data, path, get_all=False)
        if not hls_url and not data.get('canWatch'):
            self.raise_no_formats(
                'This account does not have access to the requested content', expected=True)
        elif not hls_url:
            self.raise_no_formats('No supported formats found')
        return self._extract_m3u8_formats(hls_url, video_id, 'mp4', m3u8_id='hls', live=True)

    def _extract_hls_key(self, data, path, decrypt):
        encryption_data = traverse_obj(data, path)
        if traverse_obj(encryption_data, ('encryptType', {int})) == 0:
            return None
        return traverse_obj(encryption_data, {'key': ('key', {decrypt}), 'iv': ('iv', {decrypt})})


class StacommuVODIE(StacommuBaseIE):
    _VALID_URL = r'https?://www\.stacommu\.jp/videos/episodes/(?P<id>[\da-zA-Z]+)'
    _TESTS = [{
        # not encrypted
        'url': 'https://www.stacommu.jp/videos/episodes/aXcVKjHyAENEjard61soZZ',
        'info_dict': {
            'id': 'aXcVKjHyAENEjard61soZZ',
            'ext': 'mp4',
            'title': 'スタコミュAWARDの裏側、ほぼ全部見せます！〜晴れ舞台の直前ドキドキ編〜',
            'description': 'md5:6400275c57ae75c06da36b06f96beb1c',
            'timestamp': 1679652000,
            'upload_date': '20230324',
            'thumbnail': 'https://image.stacommu.jp/6eLobQan8PFtBoU4RL4uGg/6eLobQan8PFtBoU4RL4uGg',
            'cast': 'count:11',
            'duration': 250,
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        # encrypted; requires a premium account
        'url': 'https://www.stacommu.jp/videos/episodes/3hybMByUvzMEqndSeu5LpD',
        'info_dict': {
            'id': '3hybMByUvzMEqndSeu5LpD',
            'ext': 'mp4',
            'title': 'スタプラフェス2023〜裏側ほぼ全部見せます〜＃10',
            'description': 'md5:85494488ccf1dfa1934accdeadd7b340',
            'timestamp': 1682506800,
            'upload_date': '20230426',
            'thumbnail': 'https://image.stacommu.jp/eMdXtEefR4kEyJJMpAFi7x/eMdXtEefR4kEyJJMpAFi7x',
            'cast': 'count:55',
            'duration': 312,
            'hls_aes': {
                'key': '6bbaf241b8e1fd9f59ecf546a70e4ae7',
                'iv': '1fc9002a23166c3bb1d240b953d09de9',
            },
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }]

    _API_PATH = 'videoEpisodes'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_info = self._call_api(video_id, msg='video information', auth=False, fatal=False)
        if not video_info:
            webpage = self._download_webpage(url, video_id)
            nextjs_data = self._search_nextjs_data(webpage, video_id)
            video_info = traverse_obj(
                nextjs_data,
                ('props', 'pageProps', 'dehydratedState', 'queries', 0, 'state', 'data', {dict})
            ) or {}
        hls_info, decrypt = self._call_encrypted_api(
            video_id, ':watch', 'stream information', data={'method': 1})

        return {
            'id': video_id,
            'formats': self._get_formats(hls_info, ('protocolHls', 'url', {url_or_none}), video_id),
            'hls_aes': self._extract_hls_key(hls_info, 'protocolHls', decrypt),
            **traverse_obj(video_info, {
                'title': ('displayName', {str}),
                'description': ('description', {str}),
                'timestamp': ('watchStartTime', {int_or_none}),
                'thumbnail': ('keyVisualUrl', {url_or_none}),
                'cast': ('casts', ..., 'displayName', {str}),
                'duration': ('duration', {int}),
            }),
        }


class StacommuLiveIE(StacommuBaseIE):
    _VALID_URL = r'https?://www\.stacommu\.jp/live/(?P<id>[\da-zA-Z]+)'
    _TESTS = [{
        'url': 'https://www.stacommu.jp/live/d2FJ3zLnndegZJCAEzGM3m',
        'info_dict': {
            'id': 'd2FJ3zLnndegZJCAEzGM3m',
            'ext': 'mp4',
            'title': '仲村悠菜 2023/05/04',
            'timestamp': 1683195647,
            'upload_date': '20230504',
            'thumbnail': 'https://image.stacommu.jp/pHGF57SPEHE2ke83FS92FN/pHGF57SPEHE2ke83FS92FN',
            'duration': 5322,
            'hls_aes': {
                'key': 'efbb3ec0b8246f61adf1764c5a51213a',
                'iv': '80621d19a1f19167b64cedb415b05d1c',
            },
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }]

    _API_PATH = 'events'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_info = self._call_api(video_id, msg='video information', auth=False)
        hls_info, decrypt = self._call_encrypted_api(
            video_id, ':watchArchive', 'stream information', data={'method': 1})

        return {
            'id': video_id,
            'formats': self._get_formats(hls_info, ('hls', 'urls', ..., {url_or_none}), video_id),
            'hls_aes': self._extract_hls_key(hls_info, 'hls', decrypt),
            **traverse_obj(video_info, {
                'title': ('displayName', {str}),
                'timestamp': ('startTime', {int_or_none}),
                'thumbnail': ('keyVisualUrl', {url_or_none}),
                'duration': ('duration', {int_or_none}),
            }),
        }
