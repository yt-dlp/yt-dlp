import base64
import binascii
import json
import time
import uuid

from .common import InfoExtractor
from ..dependencies import Cryptodome
from ..utils import (
    ExtractorError,
    int_or_none,
    jwt_decode_hs256,
    traverse_obj,
    try_call,
    url_or_none,
    urlencode_postdata,
    variadic,
)


class WrestleUniverseBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'wrestleuniverse'
    _VALID_URL_TMPL = r'https?://(?:www\.)?wrestle-universe\.com/(?:(?P<lang>\w{2})/)?%s/(?P<id>\w+)'
    _API_HOST = 'api.wrestle-universe.com'
    _API_PATH = None
    _REAL_TOKEN = None
    _TOKEN_EXPIRY = None
    _REFRESH_TOKEN = None
    _DEVICE_ID = None
    _LOGIN_QUERY = {'key': 'AIzaSyCaRPBsDQYVDUWWBXjsTrHESi2r_F3RAdA'}
    _LOGIN_HEADERS = {
        'Accept': '*/*',
        'Content-Type': 'application/json',
        'X-Client-Version': 'Chrome/JsCore/9.9.4/FirebaseCore-web',
        'X-Firebase-gmpid': '1:307308870738:web:820f38fe5150c8976e338b',
        'Referer': 'https://www.wrestle-universe.com/',
        'Origin': 'https://www.wrestle-universe.com',
    }

    @property
    def _TOKEN(self):
        if not self._REAL_TOKEN or not self._TOKEN_EXPIRY:
            token = try_call(lambda: self._get_cookies('https://www.wrestle-universe.com/')['token'].value)
            if not token and not self._REFRESH_TOKEN:
                self.raise_login_required()
            self._TOKEN = token

        if not self._REAL_TOKEN or self._TOKEN_EXPIRY <= int(time.time()):
            if not self._REFRESH_TOKEN:
                raise ExtractorError(
                    'Expired token. Refresh your cookies in browser and try again', expected=True)
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
        login = self._download_json(
            'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword', None,
            'Logging in', query=self._LOGIN_QUERY, headers=self._LOGIN_HEADERS, data=json.dumps({
                'returnSecureToken': True,
                'email': username,
                'password': password,
            }, separators=(',', ':')).encode(), expected_status=400)
        token = traverse_obj(login, ('idToken', {str}))
        if not token:
            raise ExtractorError(
                f'Unable to log in: {traverse_obj(login, ("error", "message"))}', expected=True)
        self._REFRESH_TOKEN = traverse_obj(login, ('refreshToken', {str}))
        if not self._REFRESH_TOKEN:
            self.report_warning('No refresh token was granted')
        self._TOKEN = token

    def _real_initialize(self):
        if self._DEVICE_ID:
            return

        self._DEVICE_ID = self._configuration_arg('device_id', [None], ie_key=self._NETRC_MACHINE)[0]
        if not self._DEVICE_ID:
            self._DEVICE_ID = self.cache.load(self._NETRC_MACHINE, 'device_id')
            if self._DEVICE_ID:
                return
            self._DEVICE_ID = str(uuid.uuid4())

        self.cache.store(self._NETRC_MACHINE, 'device_id', self._DEVICE_ID)

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
            f'https://{self._API_HOST}/v1/{self._API_PATH}/{video_id}{param}', video_id,
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

    def _download_metadata(self, url, video_id, lang, props_keys):
        metadata = self._call_api(video_id, msg='metadata', query={'al': lang or 'ja'}, auth=False, fatal=False)
        if not metadata:
            webpage = self._download_webpage(url, video_id)
            nextjs_data = self._search_nextjs_data(webpage, video_id)
            metadata = traverse_obj(nextjs_data, (
                'props', 'pageProps', *variadic(props_keys, (str, bytes, dict, set)), {dict})) or {}
        return metadata

    def _get_formats(self, data, path, video_id=None):
        hls_url = traverse_obj(data, path, get_all=False)
        if not hls_url and not data.get('canWatch'):
            self.raise_no_formats(
                'This account does not have access to the requested content', expected=True)
        elif not hls_url:
            self.raise_no_formats('No supported formats found')
        return self._extract_m3u8_formats(hls_url, video_id, 'mp4', m3u8_id='hls', live=True)


class WrestleUniverseVODIE(WrestleUniverseBaseIE):
    _VALID_URL = WrestleUniverseBaseIE._VALID_URL_TMPL % 'videos'
    _TESTS = [{
        'url': 'https://www.wrestle-universe.com/en/videos/dp8mpjmcKfxzUhEHM2uFws',
        'info_dict': {
            'id': 'dp8mpjmcKfxzUhEHM2uFws',
            'ext': 'mp4',
            'title': 'The 3rd “Futari wa Princess” Max Heart Tournament',
            'description': 'md5:318d5061e944797fbbb81d5c7dd00bf5',
            'location': '埼玉・春日部ふれあいキューブ',
            'channel': 'tjpw',
            'duration': 7119,
            'timestamp': 1674979200,
            'upload_date': '20230129',
            'thumbnail': 'https://image.asset.wrestle-universe.com/8FjD67P8rZc446RBQs5RBN/8FjD67P8rZc446RBQs5RBN',
            'chapters': 'count:7',
            'cast': 'count:21',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }]

    _API_PATH = 'videoEpisodes'

    def _real_extract(self, url):
        lang, video_id = self._match_valid_url(url).group('lang', 'id')
        metadata = self._download_metadata(url, video_id, lang, 'videoEpisodeFallbackData')
        video_data = self._call_api(video_id, ':watch', 'watch', data={'deviceId': self._DEVICE_ID})

        return {
            'id': video_id,
            'formats': self._get_formats(video_data, (
                (('protocolHls', 'url'), ('chromecastUrls', ...)), {url_or_none}), video_id),
            **traverse_obj(metadata, {
                'title': ('displayName', {str}),
                'description': ('description', {str}),
                'channel': ('labels', 'group', {str}),
                'location': ('labels', 'venue', {str}),
                'timestamp': ('watchStartTime', {int_or_none}),
                'thumbnail': ('keyVisualUrl', {url_or_none}),
                'cast': ('casts', ..., 'displayName', {str}),
                'duration': ('duration', {int}),
                'chapters': ('videoChapters', lambda _, v: isinstance(v.get('start'), int), {
                    'title': ('displayName', {str}),
                    'start_time': ('start', {int}),
                    'end_time': ('end', {int}),
                }),
            }),
        }


class WrestleUniversePPVIE(WrestleUniverseBaseIE):
    _VALID_URL = WrestleUniverseBaseIE._VALID_URL_TMPL % 'lives'
    _TESTS = [{
        'note': 'HLS AES-128 key obtained via API',
        'url': 'https://www.wrestle-universe.com/en/lives/buH9ibbfhdJAY4GKZcEuJX',
        'info_dict': {
            'id': 'buH9ibbfhdJAY4GKZcEuJX',
            'ext': 'mp4',
            'title': '【PPV】Beyond the origins, into the future',
            'description': 'md5:9a872db68cd09be4a1e35a3ee8b0bdfc',
            'channel': 'tjpw',
            'location': '東京・Twin Box AKIHABARA',
            'duration': 10098,
            'timestamp': 1675076400,
            'upload_date': '20230130',
            'thumbnail': 'https://image.asset.wrestle-universe.com/rJs2m7cBaLXrwCcxMdQGRM/rJs2m7cBaLXrwCcxMdQGRM',
            'thumbnails': 'count:3',
            'hls_aes': {
                'key': '5633184acd6e43f1f1ac71c6447a4186',
                'iv': '5bac71beb33197d5600337ce86de7862',
            },
        },
        'params': {
            'skip_download': 'm3u8',
        },
        'skip': 'No longer available',
    }, {
        'note': 'unencrypted HLS',
        'url': 'https://www.wrestle-universe.com/en/lives/wUG8hP5iApC63jbtQzhVVx',
        'info_dict': {
            'id': 'wUG8hP5iApC63jbtQzhVVx',
            'ext': 'mp4',
            'title': 'GRAND PRINCESS \'22',
            'description': 'md5:e4f43d0d4262de3952ff34831bc99858',
            'channel': 'tjpw',
            'location': '東京・両国国技館',
            'duration': 18044,
            'timestamp': 1647665400,
            'upload_date': '20220319',
            'thumbnail': 'https://image.asset.wrestle-universe.com/i8jxSTCHPfdAKD4zN41Psx/i8jxSTCHPfdAKD4zN41Psx',
            'thumbnails': 'count:3',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }]

    _API_PATH = 'events'

    def _real_extract(self, url):
        lang, video_id = self._match_valid_url(url).group('lang', 'id')
        metadata = self._download_metadata(url, video_id, lang, 'eventFallbackData')

        info = {
            'id': video_id,
            **traverse_obj(metadata, {
                'title': ('displayName', {str}),
                'description': ('description', {str}),
                'channel': ('labels', 'group', {str}),
                'location': ('labels', 'venue', {str}),
                'timestamp': ('startTime', {int_or_none}),
                'thumbnails': (('keyVisualUrl', 'alterKeyVisualUrl', 'heroKeyVisualUrl'), {'url': {url_or_none}}),
            }),
        }

        ended_time = traverse_obj(metadata, ('endedTime', {int_or_none}))
        if info.get('timestamp') and ended_time:
            info['duration'] = ended_time - info['timestamp']

        video_data, decrypt = self._call_encrypted_api(
            video_id, ':watchArchive', 'watch archive', data={'method': 1})
        info['formats'] = self._get_formats(video_data, (
            ('hls', None), ('urls', 'chromecastUrls'), ..., {url_or_none}), video_id)
        for f in info['formats']:
            # bitrates are exaggerated in PPV playlists, so avoid wrong/huge filesize_approx values
            if f.get('tbr'):
                f['tbr'] = int(f['tbr'] / 2.5)

        hls_aes_key = traverse_obj(video_data, ('hls', 'key', {decrypt}))
        if hls_aes_key:
            info['hls_aes'] = {
                'key': hls_aes_key,
                'iv': traverse_obj(video_data, ('hls', 'iv', {decrypt})),
            }
        elif traverse_obj(video_data, ('hls', 'encryptType', {int})):
            self.report_warning('HLS AES-128 key was not found in API response')

        return info
