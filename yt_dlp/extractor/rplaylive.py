import base64
import datetime as dt
import hashlib
import hmac
import json
import random
import re
import time

from .common import InfoExtractor
from ..aes import aes_cbc_encrypt_bytes
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
    _jwt_token = None
    _tested_jwt = False

    def _check_jwt_args(self):
        jwt_arg = self._configuration_arg('jwt_token', ie_key='rplaylive', casesense=True)
        if self._jwt_token is None and jwt_arg and not self._tested_jwt:
            self._login_by_token(jwt_arg[0], raw_token_hint=True)
            self._tested_jwt = True

    @property
    def user_id(self):
        self._check_jwt_args()
        return self._user_id

    @property
    def jwt_token(self):
        self._check_jwt_args()
        return self._jwt_token

    @property
    def requestor_query(self):
        return {
            'requestorOid': self.user_id,
            'loginType': 'plax',
        } if self.user_id else {}

    @property
    def jwt_header(self):
        return {
            'Origin': 'https://rplay.live',
            'Referer': 'https://rplay.live/',
            'Authorization': self.jwt_token or 'null',
        }

    @property
    def butter_header(self):
        return {
            'Origin': 'https://rplay.live',
            'Referer': 'https://rplay.live/',
            'Butter': self.get_butter_token(),
        }

    def _login_hint(self, *args, **kwargs):
        return (f'Use --username and --password, --netrc-cmd, --netrc ({self._NETRC_MACHINE}) '
                'or --extractor-args "rplaylive:jwt_token=xxx" to provide account credentials')

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

    def _login_by_token(self, jwt_token, raw_token_hint=False):
        user_info = self._download_json(
            'https://api.rplay-cdn.com/account/login', 'login', note='performing login', errnote='login failed',
            data=f'{{"token":"{jwt_token}","loginType":null,"checkAdmin":null}}'.encode(),
            headers={'Content-Type': 'application/json', 'Authorization': 'null'}, fatal=False)

        if user_info:
            self._user_id = traverse_obj(user_info, 'oid')
            self._jwt_token = jwt_token if self._user_id else None
        if not self._user_id:
            if raw_token_hint:
                self.report_warning('Login failed, possibly due to wrong or expired JWT token')
            else:
                self.report_warning('Login failed, possibly due to wrong password or website change')

    def get_butter_token(self):
        salt = 'QWI@(!WAS)Dj1AA(!@*DJ#@$@~1)P'
        key = 'S%M@#H#B(!@()a2@'
        ts_value = str(int(time.time() / 360))
        enc = aes_cbc_encrypt_bytes(f'{salt}https://rplay.live{ts_value}', key, ts_value.zfill(16))
        return enc.hex()


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
            'thumbnail': 'https://pb.rplay.live/thumbnail/669203d25223214e67579dc3',
            'uploader': '杏都める',
            'uploader_id': '667adc9e9aa7f739a2158ff3',
            'tags': ['杏都める', 'めいどるーちぇ', '無料', '耳舐め', 'ASMR'],
            'like_count': int,
            'view_count': int,
            'location': 'JP',
        },
    }, {
        'url': 'https://rplay.live/play/66783c65dcd1c768a8a69f24/',
        'info_dict': {
            'id': '66783c65dcd1c768a8a69f24',
            'ext': 'mp4',
            'title': 'md5:9be2febe48cee1b7536e3e9d4d5f8e56',
            'description': 'md5:a71374d3dcd1db0f852b96a69b41b699',
            'timestamp': 1719155813,
            'upload_date': '20240623',
            'release_timestamp': 1719155813,
            'release_date': '20240623',
            'duration': 4237.0,
            'thumbnail': 'https://pb.rplay.live/thumbnail/66783c65dcd1c768a8a69f24',
            'uploader': '狐月れんげ',
            'uploader_id': '65eeb4b237043dc0b5654f86',
            'tags': 'count:4',
            'age_limit': 18,
            'live_status': 'was_live',
            'like_count': int,
            'view_count': int,
            'location': 'JP',
        },
    }, {
        'url': 'https://rplay.live/play/682065da13ed2c564c77d8f7',
        'info_dict': {
            'id': '682065da13ed2c564c77d8f7',
            'ext': 'mp4',
            'title': 'md5:9551c4c0ffe610ef57a87fd1e8941073',
            'description': 'md5:eb03a6c7200022d1554ba67feb6043e0',
            'timestamp': 1746953690,
            'upload_date': '20250511',
            'release_timestamp': 1746953805,
            'release_date': '20250511',
            'duration': 11.483,
            'thumbnail': 'https://pb.rplay.live/thumbnail/682065da13ed2c564c77d8f7',
            'uploader': 'Seldea',
            'uploader_id': '64d483add2c96306099ef734',
            'tags': ['셀데아', '무료', 'Free', '無料'],
            'like_count': int,
            'view_count': int,
            'location': 'KR',
        },
        'params': {'extractor_args': {'rplaylive': {'lang': ['en']}}},
    }, {
        'url': 'https://rplay.live/play/664f6dbe8ff72ac8bb0aecfc',
        'info_dict': {
            'id': '664f6dbe8ff72ac8bb0aecfc',
            'ext': 'mp4',
            'title': 'md5:b47c5094854a84e3318f8b0bd70fdee8',
            'description': 'md5:edc7641e1bbb195e788a9695883f6ab9',
            'timestamp': 1716481470,
            'upload_date': '20240523',
            'release_timestamp': 1716485243,
            'release_date': '20240523',
            'duration': 7273.433333,
            'thumbnail': 'https://pb.rplay.live/thumbnail/664f6dbe8ff72ac8bb0aecfc',
            'uploader': 'ミス・ネフェルー',
            'uploader_id': '6640ce9db293d7d82bf76cfd',
            'tags': 'count:3',
            'age_limit': 18,
            'like_count': int,
            'view_count': int,
            'location': 'JP',
        },
        'skip': 'subscribe required',
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        playlist_id = traverse_obj(parse_qs(url), ('playlist', ..., any))
        if playlist_id and self._yes_playlist(playlist_id, video_id):
            playlist_info = self._download_json(
                'https://api.rplay-cdn.com/content/playlist', playlist_id,
                query={'playlistOid': playlist_id, **self.requestor_query},
                headers=self.jwt_header, fatal=False)
            if playlist_info:
                entries = traverse_obj(playlist_info, ('contentData', ..., '_id', {
                    lambda x: self.url_result(f'https://rplay.live/play/{x}/', ie=RPlayVideoIE, video_id=x)}))
                return self.playlist_result(entries, playlist_id, playlist_info.get('name'))
            else:
                self.report_warning('Failed to get playlist, downloading video only')

        video_info = self._download_json('https://api.rplay-cdn.com/content', video_id, query={
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
            'uploader': ('creatorInfo', 'nickname', {str}),
            'uploader_id': ('creatorOid', {str}),
            'tags': ('hashtags', lambda _, v: v[0] != '_'),
            'age_limit': (('hideContent', 'isAdultContent'), {lambda x: 18 if x else None}, any),
            'location': ('location', {str}),
            'view_count': ('views', {int}),
            'like_count': ('likes', {int}),
            'live_status': ('isReplayContent', {lambda x: 'was_live' if x else None}),
        })
        if preferred_lang := self._configuration_arg('lang', ie_key='rplaylive', default=[None])[0]:
            translated_metainfo = traverse_obj(video_info, {
                'title': ('multiLangTitle', preferred_lang, {str}),
                'description': ('multiLangIntroText', preferred_lang, {str}),
                'uploader': ('creatorInfo', 'multiLangNick', preferred_lang, {str}),
            })
            if missing := [k for k in ['title', 'description', 'uploader'] if k not in translated_metainfo]:
                self.report_warning(
                    f'Did not find translations for {preferred_lang} for fields: {", ".join(missing)}; '
                    'will use original language for these field(s)', video_id)
            metainfo.update(translated_metainfo)

        m3u8_url = traverse_obj(video_info, ('canView', 'url', {url_or_none}))
        if not m3u8_url:
            msg = 'You do not have access to this video'
            if traverse_obj(video_info, ('viewableTiers', 'free')):
                msg = 'This video requires a free subscription to access'
            if not self.user_id:
                msg += f'. {self._login_hint()}'
            raise ExtractorError(msg, expected=True)

        raw_formats = self._extract_m3u8_formats(m3u8_url, video_id, headers=self.butter_header)
        formats = []
        for fmt in raw_formats:
            m3u8_doc = self._download_webpage(fmt['url'], video_id, f'getting m3u8 for {fmt["format_id"]}',
                                              headers=self.butter_header, fatal=False)
            if not m3u8_doc:
                continue  # skip invalid format
            fmt['url'] = encode_data_uri(m3u8_doc.encode(), 'application/x-mpegurl')
            match = re.search(r'^#EXT-X-KEY.*?URI="([^"]+)"', m3u8_doc, flags=re.M)
            if match:
                urlh = self._request_webpage(match[1], video_id, 'getting hls key', headers={
                    'Origin': 'https://rplay.live',
                    'Referer': 'https://rplay.live/',
                    'rplay-private-content-requestor': self.user_id or 'not-logged-in',
                    'age': random.randint(1, 4999),
                })
                fmt['hls_aes'] = {'key': urlh.read().hex()}
            formats.append(fmt)

        return {
            'id': video_id,
            'formats': formats,
            **metainfo,
            'thumbnail': f'https://pb.rplay.live/thumbnail/{video_id}',
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
        'playlist_mincount': 35,
    }, {
        'url': 'https://rplay.live/c/furachi',
        'info_dict': {
            'id': '65e07e60850f4527aab74757',
            'title': '桜彗ふらち OuseFurachi',
        },
        'playlist_mincount': 94,
    }]

    def _real_extract(self, url):
        user_id, short = self._match_valid_url(url).group('id', 'short')

        user_info = self._download_json('https://api.rplay-cdn.com/account/getuser', user_id, query={
            'customUrl' if short == 'c' else 'userOid': user_id, 'options': '{"includeContentMetadata":true}'})
        replays = self._download_json(
            'https://api.rplay-cdn.com/live/replays', user_id, query={'creatorOid': user_info.get('_id')})

        def _entries():
            def _entry_ids():
                for entry in traverse_obj(user_info, ('metadataSet', ..., lambda _, v: v['_id'])):
                    yield entry['_id'], entry.get('title')
                for entry in traverse_obj(replays, lambda _, v: v['_id']):
                    yield entry['_id'], entry.get('title')
            for vid, title in dict(_entry_ids()).items():
                yield self.url_result(f'https://rplay.live/play/{vid}', ie=RPlayVideoIE, id=vid, title=title)

        return self.playlist_result(_entries(), user_info.get('_id', user_id), user_info.get('nickname'))


class RPlayLiveIE(RPlayBaseIE):
    _VALID_URL = [
        r'https://rplay.live/(?P<short>c)/(?P<id>[\d\w]+)/live',
        r'https://rplay.live/(?P<short>live)/(?P<id>[\d\w]+)',
    ]
    _TESTS = [{
        'url': 'https://rplay.live/c/chachamaru/live',
        'info_dict': {
            'id': '667e511a6f7cead36a00e7b1',
            'ext': 'mp4',
            'title': r're:【ASMR】やばっ*',
            'description': 'md5:de9d0f8e8b80ee93678bebad5b43254e',
            'timestamp': 1740578497,
            'upload_date': '20250226',
            'live_status': 'is_live',
            'thumbnail': 'https://pb.rplay.live/liveChannelThumbnails/667e4cd99aa7f739a2c91852',
            'uploader': '愛犬茶々丸',
            'uploader_id': '667e4cd99aa7f739a2c91852',
            'tags': list,
        },
        'skip': 'live',
    }, {
        'url': 'https://rplay.live/live/667adc9e9aa7f739a2158ff3',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        user_id, short = self._match_valid_url(url).group('id', 'short')

        user_info = self._download_json('https://api.rplay-cdn.com/account/getuser', user_id, query={
            'customUrl' if short == 'c' else 'userOid': user_id})
        user_id = user_info['_id']

        live_info = self._download_json('https://api.rplay-cdn.com/live/play', user_id, query={
            'creatorOid': user_id, **self.requestor_query}, headers=self.jwt_header)

        stream_state = live_info['streamState']
        if stream_state == 'offline':
            raise UserNotLive
        elif stream_state == 'youtube':
            return self.url_result(f'https://www.youtube.com/watch?v={live_info["liveStreamId"]}')
        elif stream_state == 'twitch':
            return self.url_result(f'https://www.twitch.tv/{live_info["twitchLogin"]}')
        elif stream_state == 'live':
            if not self.user_id and not live_info.get('allowAnonymous'):
                self.raise_login_required(method='password')
            if not live_info.get('accessible'):
                if traverse_obj(live_info, ('tierHashes', lambda _, v: v == 'free', any)):
                    raise ExtractorError('The livestream requires a free subscription to access', expected=True)
                raise ExtractorError('You do not have access to the livestream', expected=True)
            key2 = traverse_obj(self._download_json(
                'https://api.rplay-cdn.com/live/key2', user_id, 'getting live key',
                headers=self.jwt_header, query=self.requestor_query), ('authKey', {str})) if self.user_id else ''
            if key2 is None:
                raise ExtractorError('Failed to get playlist key')
            formats = self._extract_m3u8_formats(
                'https://api.rplay-cdn.com/live/stream/playlist.m3u8', user_id,
                query={'creatorOid': user_id, 'key2': key2}, headers={'Referer': 'https://rplay.live'})

            return {
                'id': live_info.get('oid') or user_id,
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
        else:
            raise ExtractorError(f'Unknow streamState: {stream_state}')
