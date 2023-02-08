import base64
import binascii
import json
import time

from .common import InfoExtractor
from ..dependencies import Cryptodome
from ..utils import (
    ExtractorError,
    int_or_none,
    jwt_decode_hs256,
    traverse_obj,
    try_call,
    url_or_none,
)


class WrestleUniverseBaseIE(InfoExtractor):
    _VALID_URL_TMPL = r'https?://(?:www\.)?wrestle-universe\.com/(?:(?P<lang>\w{2})/)?%s/(?P<id>\w+)'
    _API_PATH = None
    _TOKEN = None
    _TOKEN_EXPIRY = None

    def _get_token_cookie(self):
        if not self._TOKEN or not self._TOKEN_EXPIRY:
            self._TOKEN = try_call(lambda: self._get_cookies('https://www.wrestle-universe.com/')['token'].value)
            if not self._TOKEN:
                self.raise_login_required()
            expiry = traverse_obj(jwt_decode_hs256(self._TOKEN), ('exp', {int_or_none}))
            if not expiry:
                raise ExtractorError('There was a problem with the token cookie')
            self._TOKEN_EXPIRY = expiry

        if self._TOKEN_EXPIRY <= int(time.time()):
            raise ExtractorError(
                'Expired token. Refresh your cookies in browser and try again', expected=True)

        return self._TOKEN

    def _call_api(self, video_id, param='', msg='API', auth=True, data=None, query={}, fatal=True):
        headers = {'CA-CID': ''}
        if data:
            headers['Content-Type'] = 'application/json;charset=utf-8'
            data = json.dumps(data, separators=(',', ':')).encode()
        if auth:
            headers['Authorization'] = f'Bearer {self._get_token_cookie()}'
        return self._download_json(
            f'https://api.wrestle-universe.com/v1/{self._API_PATH}/{video_id}{param}', video_id,
            note=f'Downloading {msg} JSON', errnote=f'Failed to download {msg} JSON',
            data=data, headers=headers, query=query, fatal=fatal)

    def _call_encrypted_api(self, video_id, param='', msg='API', data={}, query={}, fatal=True):
        if not Cryptodome:
            raise ExtractorError('pycryptodomex not found. Please install', expected=True)
        private_key = Cryptodome.PublicKey.RSA.generate(2048)
        cipher = Cryptodome.Cipher.PKCS1_OAEP.new(private_key, hashAlgo=Cryptodome.Hash.SHA1)

        def decrypt(data):
            if not data:
                return None
            try:
                return cipher.decrypt(base64.b64decode(data)).decode()
            except (ValueError, binascii.Error) as e:
                raise ExtractorError(f'Could not decrypt data: {e}')

        token = base64.b64encode(private_key.public_key().export_key('DER')).decode()
        api_json = self._call_api(video_id, param, msg, data={
            # 'deviceId' (random uuid4 generated at login) is not required yet
            'token': token,
            **data,
        }, query=query, fatal=fatal)
        return api_json, decrypt

    def _download_metadata(self, url, video_id, lang, props_key):
        metadata = self._call_api(video_id, msg='metadata', query={'al': lang or 'ja'}, auth=False, fatal=False)
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
            'cast': 'count:18',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }]

    _API_PATH = 'videoEpisodes'

    def _real_extract(self, url):
        lang, video_id = self._match_valid_url(url).group('lang', 'id')
        metadata = self._download_metadata(url, video_id, lang, 'videoEpisodeFallbackData')
        video_data = self._call_api(video_id, ':watch', 'watch', data={
            # 'deviceId' is required if ignoreDeviceRestriction is False
            'ignoreDeviceRestriction': True,
        })

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

        info = traverse_obj(metadata, {
            'title': ('displayName', {str}),
            'description': ('description', {str}),
            'channel': ('labels', 'group', {str}),
            'location': ('labels', 'venue', {str}),
            'timestamp': ('startTime', {int_or_none}),
            'thumbnails': (('keyVisualUrl', 'alterKeyVisualUrl', 'heroKeyVisualUrl'), {'url': {url_or_none}}),
        })

        ended_time = traverse_obj(metadata, ('endedTime', {int_or_none}))
        if info.get('timestamp') and ended_time:
            info['duration'] = ended_time - info['timestamp']

        video_data, decrypt = self._call_encrypted_api(
            video_id, ':watchArchive', 'watch archive', data={'method': 1})
        formats = self._get_formats(video_data, (
            ('hls', None), ('urls', 'chromecastUrls'), ..., {url_or_none}), video_id)
        for f in formats:
            # bitrates are exaggerated in PPV playlists, so avoid wrong/huge filesize_approx values
            if f.get('tbr'):
                f['tbr'] = int(f['tbr'] / 2.5)

        hls_aes_key = traverse_obj(video_data, ('hls', 'key', {decrypt}))
        if not hls_aes_key and traverse_obj(video_data, ('hls', 'encryptType', {int}), default=0) > 0:
            self.report_warning('HLS AES-128 key was not found in API response')

        return {
            'id': video_id,
            'formats': formats,
            'hls_aes': {
                'key': hls_aes_key,
                'iv': traverse_obj(video_data, ('hls', 'iv', {decrypt})),
            },
            **info,
        }
