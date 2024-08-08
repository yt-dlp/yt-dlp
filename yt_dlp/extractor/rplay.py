import base64
import datetime as dt
import hashlib
import hmac
import json
import random
import re
import time

from .common import InfoExtractor
from ..jsinterp import DenoWrapper
from ..utils import (
    ExtractorError,
    UserNotLive,
    encode_data_uri,
    float_or_none,
    parse_iso8601,
    parse_qs,
    traverse_obj,
    url_or_none,
)


class RPlayBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'rplaylive'
    _TOKEN_CACHE = {}
    _user_id = None
    _login_type = None
    _jwt_token = None

    @property
    def user_id(self):
        return self._user_id

    @property
    def login_type(self):
        return self._login_type

    @property
    def jwt_token(self):
        return self._jwt_token

    @property
    def requestor_query(self):
        return {
            'requestorOid': self.user_id,
            'loginType': self.login_type,
        } if self.user_id else {}

    @property
    def jwt_header(self):
        return {
            'Referer': 'https://rplay.live/',
            'Authorization': self.jwt_token or 'null',
        }

    def _jwt_encode_hs256(self, payload: dict, key: str):
        # yt_dlp.utils.jwt_encode_hs256() uses slightly different details that would fails
        # and we need to re-implement it with minor changes
        b64encode = lambda x: base64.urlsafe_b64encode(
            json.dumps(x, separators=(',', ':')).encode()).strip(b'=')

        header_b64 = b64encode({'alg': 'HS256', 'typ': 'JWT'})
        payload_b64 = b64encode(payload)
        h = hmac.new(key.encode(), header_b64 + b'.' + payload_b64, hashlib.sha256)
        signature_b64 = base64.urlsafe_b64encode(h.digest()).strip(b'=')
        return header_b64 + b'.' + payload_b64 + b'.' + signature_b64

    def _perform_login(self, username, password):
        payload = {
            'eml': username,
            'dat': dt.datetime.now(dt.timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
            'iat': int(time.time()),
        }
        key = hashlib.sha256(password.encode()).hexdigest()
        self._login_by_token(self._jwt_encode_hs256(payload, key).decode())

    def _login_by_token(self, jwt_token):
        user_info = self._download_json(
            'https://api.rplay.live/account/login', 'login', note='performing login', errnote='Failed to login',
            data=f'{{"token":"{jwt_token}","loginType":null,"checkAdmin":null}}'.encode(),
            headers={'Content-Type': 'application/json', 'Authorization': 'null'}, fatal=False)

        if user_info:
            self._user_id = traverse_obj(user_info, 'oid')
            self._login_type = traverse_obj(user_info, 'accountType')
            self._jwt_token = jwt_token if self._user_id else None
        if not self._user_id:
            self.report_warning('Failed to login, possibly due to wrong password or website change')

    def _get_butter_files(self):
        cache = self.cache.load('rplay', 'butter-code') or {}
        if cache.get('date', 0) > time.time() - 86400:
            return cache['js'], cache['wasm']
        butter_js = self._download_webpage(
            'https://pb.rplay.live/kr/public/smooth_like_butter.js', 'butter', 'getting butter-sign js')
        urlh = self._request_webpage(
            'https://pb.rplay.live/kr/public/smooth_like_butter_bg.wasm', 'butter', 'getting butter-sign wasm')
        butter_wasm_array = list(urlh.read())
        self.cache.store('rplay', 'butter-code', {'js': butter_js, 'wasm': butter_wasm_array, 'date': time.time()})
        return butter_js, butter_wasm_array

    def _calc_butter_token(self):
        butter_js, butter_wasm_array = self._get_butter_files()
        butter_js = re.sub(r'export(?:\s+default)?([\s{])', r'\1', butter_js)
        butter_js = butter_js.replace('import.meta', '{}')

        butter_js += '''const __new_init = async () => {
            const t = __wbg_get_imports();
            __wbg_init_memory(t);
            const {module, instance} = await WebAssembly.instantiate(Uint8Array.from(%s), t);
            __wbg_finalize_init(instance, module);
        };''' % butter_wasm_array  # noqa: UP031

        butter_js += '''const navProxy = new Proxy(window.navigator, { get: (target, prop, receiver) => {
                if (prop === 'webdriver') return false;
                return target[prop];}});
            Object.defineProperty(window, "navigator", {get: () => navProxy});
            window.location = {origin: "https://rplay.live"};'''

        butter_js += '__new_init().then(() => console.log((new ButterFactory()).generate_butter()));'

        jsi = DenoWrapper(self)
        return jsi.execute(butter_js, jit_less=False)

    def get_butter_token(self):
        cache = self.cache.load('rplay', 'butter-token') or {}
        timestamp = str(int(time.time() / 360))
        if cache.get(timestamp):
            return cache[timestamp]
        token = self._calc_butter_token()
        self.cache.store('rplay', 'butter-token', {timestamp: token})
        return token


class RPlayVideoIE(RPlayBaseIE):
    _VALID_URL = r'https://rplay.live/play/(?P<id>[\d\w]+)'
    _TESTS = [{
        'url': 'https://rplay.live/play/669203d25223214e67579dc3/',
        'info_dict': {
            'id': '669203d25223214e67579dc3',
            'ext': 'mp4',
            'title': 'md5:6ab0a76410b40b1f5fb48a2ad7571264',
            'description': 'md5:d2fb2f74a623be439cf454df5ff3344a',
            'timestamp': 1720845266,
            'upload_date': '20240713',
            'release_timestamp': 1720846360,
            'release_date': '20240713',
            'duration': 5349.0,
            'thumbnail': r're:https://[\w\d]+.cloudfront.net/.*',
            'uploader': '杏都める',
            'uploader_id': '667adc9e9aa7f739a2158ff3',
            'tags': ['杏都める', 'めいどるーちぇ', '無料', '耳舐め', 'ASMR'],
        },
        'params': {'cachedir': False},
    }, {
        'url': 'https://rplay.live/play/660bee4fd3c1d09d69db6870/',
        'info_dict': {
            'id': '660bee4fd3c1d09d69db6870',
            'ext': 'mp4',
            'title': 'md5:7de162a0f1c2266ec428234620a124fc',
            'description': 'md5:c6d12cc8110b748d5588d5f00787cd35',
            'timestamp': 1712057935,
            'upload_date': '20240402',
            'release_timestamp': 1712061900,
            'release_date': '20240402',
            'duration': 6791.0,
            'thumbnail': r're:https://[\w\d]+.cloudfront.net/.*',
            'uploader': '狐月れんげ',
            'uploader_id': '65eeb4b237043dc0b5654f86',
            'tags': 'count:10',
            'age_limit': 18,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        playlist_id = traverse_obj(parse_qs(url), ('playlist', ..., any))
        if playlist_id and self._yes_playlist(playlist_id, video_id):
            playlist_info = self._download_json(
                'https://api.rplay.live/content/playlist', playlist_id,
                query={'playlistOid': playlist_id, **self.requestor_query},
                headers=self.jwt_header, fatal=False)
            if playlist_info:
                entries = traverse_obj(playlist_info, ('contentData', ..., '_id', {
                    lambda x: self.url_result(f'https://rplay.live/play/{x}/', ie=RPlayVideoIE, video_id=x)}))
                return self.playlist_result(entries, playlist_id, playlist_info.get('name'))
            else:
                self.report_warning('Failed to get playlist, downloading video only')

        video_info = self._download_json('https://api.rplay.live/content', video_id, query={
            'contentOid': video_id,
            'status': 'published',
            'withComments': True,
            'requestCanView': True,
            **self.requestor_query,
        }, headers=self.jwt_header)
        if video_info.get('drm'):
            raise ExtractorError('This video is DRM-protected')

        metainfo = traverse_obj(video_info, {
            'title': ('title', {str}),
            'description': ('introText', {str}),
            'release_timestamp': ('publishedAt', {parse_iso8601}),
            'timestamp': ('createdAt', {parse_iso8601}),
            'duration': ('length', {float_or_none}),
            'uploader': ('nickname', {str}),
            'uploader_id': ('creatorOid', {str}),
            'tags': ('hashtags', lambda _, v: v[0] != '_'),
            'age_limit': (('hideContent', 'isAdultContent'), {lambda x: 18 if x else None}, any),
        })

        m3u8_url = traverse_obj(video_info, ('canView', 'url', {url_or_none}))
        if not m3u8_url:
            msg = 'You do not have access to this video'
            if traverse_obj(video_info, ('viewableTiers', 'free')):
                msg = 'This video requires a free subscription to access'
            if not self.user_id:
                msg += f'. {self._login_hint(method="password")}'
            raise ExtractorError(msg, expected=True)

        thumbnail_key = traverse_obj(video_info, (
            'streamables', lambda _, v: v['type'].startswith('image/'), 's3key', any))
        if thumbnail_key:
            metainfo['thumbnail'] = url_or_none(self._download_webpage(
                'https://api.rplay.live/upload/privateasset', video_id, 'getting cover url', query={
                    'key': thumbnail_key,
                    'contentOid': video_id,
                    'creatorOid': metainfo.get('uploader_id'),
                    **self.requestor_query,
                }, errnote='Failed to get thumbnail url', fatal=False))

        formats = self._extract_m3u8_formats(m3u8_url, video_id, headers={
            'Referer': 'https://rplay.live/', 'Butter': self.get_butter_token()})
        for fmt in formats:
            m3u8_doc = self._download_webpage(fmt['url'], video_id, 'getting m3u8 contents', headers={
                'Referer': 'https://rplay.live/', 'Butter': self.get_butter_token()})
            fmt['url'] = encode_data_uri(m3u8_doc.encode(), 'application/x-mpegurl')
            match = re.search(r'^#EXT-X-KEY.*?URI="([^"]+)"', m3u8_doc, flags=re.M)
            if match:
                urlh = self._request_webpage(match[1], video_id, 'getting hls key', headers={
                    'Referer': 'https://rplay.live/',
                    'rplay-private-content-requestor': self.user_id or 'not-logged-in',
                    'age': random.randint(1, 4999),
                })
                fmt['hls_aes'] = {'key': urlh.read().hex()}

        return {
            'id': video_id,
            'formats': formats,
            **metainfo,
            'http_headers': {'Referer': 'https://rplay.live/'},
        }


class RPlayUserIE(InfoExtractor):
    _VALID_URL = r'https://rplay.live/(?P<short>c|creatorhome)/(?P<id>[\d\w]+)/?(?:[#?]|$)'
    _TESTS = [{
        'url': 'https://rplay.live/creatorhome/667adc9e9aa7f739a2158ff3?page=contents',
        'info_dict': {
            'id': '667adc9e9aa7f739a2158ff3',
            'title': '杏都める',
        },
        'playlist_mincount': 34,
    }, {
        'url': 'https://rplay.live/c/furachi?page=contents',
        'info_dict': {
            'id': '65e07e60850f4527aab74757',
            'title': '逢瀬ふらち OuseFurachi',
        },
        'playlist_mincount': 77,
    }]

    def _real_extract(self, url):
        user_id, short = self._match_valid_url(url).group('id', 'short')
        key = 'customUrl' if short == 'c' else 'userOid'

        user_info = self._download_json(
            f'https://api.rplay.live/account/getuser?{key}={user_id}&filter[]=nickname&filter[]=published', user_id)
        replays = self._download_json(
            'https://api.rplay.live/live/replays?=667e4cd99aa7f739a2c91852', user_id, query={
                'creatorOid': user_info.get('_id')})

        entries = traverse_obj(user_info, ('published', ..., {
            lambda x: self.url_result(f'https://rplay.live/play/{x}/', ie=RPlayVideoIE, video_id=x)}))
        for entry_id in traverse_obj(replays, (..., '_id', {str})):
            if entry_id in user_info.get('published', []):
                continue
            entries.append(self.url_result(f'https://rplay.live/play/{entry_id}/', ie=RPlayVideoIE, video_id=entry_id))

        return self.playlist_result(entries, user_info.get('_id', user_id), user_info.get('nickname'))


class RPlayLiveIE(RPlayBaseIE):
    _VALID_URL = [
        r'https://rplay.live/(?P<short>c)/(?P<id>[\d\w]+)/live',
        r'https://rplay.live/(?P<short>live)/(?P<id>[\d\w]+)',
    ]
    _TESTS = [{
        'url': 'https://rplay.live/c/chachamaru/live',
        'info_dict': {
            'id': '667e4cd99aa7f739a2c91852',
            'ext': 'mp4',
            'title': r're:【ASMR】ん～っやば//スキスキ耐久.*',
            'description': 'md5:7f88ac0a7a3d5d0b926a0baecd1d40e1',
            'timestamp': 1721739947,
            'upload_date': '20240723',
            'live_status': 'is_live',
            'thumbnail': 'https://pb.rplay.live/liveChannelThumbnails/667e4cd99aa7f739a2c91852',
            'uploader': '愛犬茶々丸',
            'uploader_id': '667e4cd99aa7f739a2c91852',
            'tags': 'count:9',
        },
        'skip': 'live',
    }, {
        'url': 'https://rplay.live/live/667adc9e9aa7f739a2158ff3',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        user_id, short = self._match_valid_url(url).group('id', 'short')

        if short == 'c':
            user_info = self._download_json(f'https://api.rplay.live/account/getuser?customUrl={user_id}', user_id)
            user_id = user_info['_id']
        else:
            user_info = self._download_json(f'https://api.rplay.live/account/getuser?userOid={user_id}', user_id)

        live_info = self._download_json('https://api.rplay.live/live/play', user_id, query={'creatorOid': user_id})

        stream_state = live_info['streamState']
        if stream_state == 'youtube':
            return self.url_result(f'https://www.youtube.com/watch?v={live_info["liveStreamId"]}')
        elif stream_state == 'live':
            if not self.user_id and not live_info.get('allowAnonymous'):
                self.raise_login_required(method='password')
            key2 = self._download_webpage(
                'https://api.rplay.live/live/key2', user_id, 'getting live key',
                headers=self.jwt_header, query=self.requestor_query) if self.user_id else ''
            formats = self._extract_m3u8_formats(
                'https://api.rplay.live/live/stream/playlist.m3u8', user_id,
                query={'creatorOid': user_id, 'key2': key2})

            return {
                'id': user_id,
                'formats': formats,
                'is_live': True,
                'http_headers': {'Referer': 'https://rplay.live'},
                'thumbnail': f'https://pb.rplay.live/liveChannelThumbnails/{user_id}',
                'uploader': traverse_obj(user_info, ('nickname', {str})),
                'uploader_id': user_id,
                **traverse_obj(live_info, {
                    'title': ('title', {str}),
                    'description': ('description', {str}),
                    'timestamp': ('streamStartTime', {parse_iso8601}),
                    'tags': ('hashtags', ..., {str}),
                    'age_limit': ('isAdultContent', {lambda x: 18 if x else None}),
                }),
            }
        elif stream_state == 'offline':
            raise UserNotLive
        else:
            raise ExtractorError(f'Unknow streamState: {stream_state}')
