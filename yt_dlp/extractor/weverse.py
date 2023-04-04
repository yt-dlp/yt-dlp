import base64
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import uuid

from .common import InfoExtractor
from .youtube import YoutubeIE
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    str_or_none,
    traverse_obj,
    try_call,
    update_url_query,
    url_or_none,
)


class WeverseBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'weverse'
    _ACCOUNT_API_BASE = 'https://accountapi.weverse.io/web/api/v2'
    _API_HEADERS = {
        'Referer': 'https://weverse.io/',
        'WEV-device-Id': str(uuid.uuid4()),
    }

    def _perform_login(self, username, password):
        headers = {
            'x-acc-app-secret': '5419526f1c624b38b10787e5c10b2a7a',
            'x-acc-app-version': '2.2.6',
            'x-acc-language': 'en',
            'x-acc-service-id': 'weverse',
            'x-acc-trace-id': str(uuid.uuid4()),
            'x-clog-user-device-id': str(uuid.uuid4()),
        }
        check_username = self._download_json(
            f'{self._ACCOUNT_API_BASE}/signup/email/status', None,
            note='Checking username', query={'email': username}, headers=headers)
        if not check_username.get('hasPassword'):
            raise ExtractorError('Invalid username provided', expected=True)

        headers['content-type'] = 'application/json'
        try:
            auth = self._download_json(
                f'{self._ACCOUNT_API_BASE}/auth/token/by-credentials', None, data=json.dumps({
                    'email': username,
                    'password': password,
                }, separators=(',', ':')).encode(), headers=headers, note='Logging in')
        except ExtractorError as e:
            if isinstance(e.cause, urllib.error.HTTPError) and e.cause.code == 401:
                raise ExtractorError('Invalid password provided', expected=True)
            raise

        WeverseBaseIE._API_HEADERS['Authorization'] = f'Bearer {auth["accessToken"]}'

    def _real_initialize(self):
        if self._API_HEADERS.get('Authorization'):
            return

        token = try_call(lambda: self._get_cookies('https://weverse.io/')['we2_access_token'].value)
        if not token:
            self.raise_login_required()

        WeverseBaseIE._API_HEADERS['Authorization'] = f'Bearer {token}'

    def _call_api(self, ep, video_id, data=None, note='Downloading API JSON'):
        # Ref: https://ssl.pstatic.net/static/wevweb/2_3_2_11101725/public/static/js/2488.a09b41ff.chunk.js
        # From https://ssl.pstatic.net/static/wevweb/2_3_2_11101725/public/static/js/main.e206f7c1.js:
        key = b'1b9cb6378d959b45714bec49971ade22e6e24e42'
        api_path = update_url_query(ep, {
            'appId': 'be4d79eb8fc7bd008ee82c8ec4ff6fd4',
            'language': 'en',
            'platform': 'WEB',
            'wpf': 'pc',
        })
        wmsgpad = int(time.time() * 1000)
        wmd = base64.b64encode(hmac.HMAC(
            key, f'{api_path[:255]}{wmsgpad}'.encode(), digestmod=hashlib.sha1).digest()).decode()
        headers = {'Content-Type': 'application/json'} if data else {}
        try:
            return self._download_json(
                f'https://global.apis.naver.com/weverse/wevweb{api_path}', video_id, note=note,
                data=data, headers={**self._API_HEADERS, **headers}, query={
                    'wmsgpad': wmsgpad,
                    'wmd': wmd,
                })
        except ExtractorError as e:
            if isinstance(e.cause, urllib.error.HTTPError) and e.cause.code == 401:
                self.raise_login_required(
                    'Session token has expired. Log in again or refresh cookies in browser')
            elif isinstance(e.cause, urllib.error.HTTPError) and e.cause.code == 403:
                raise ExtractorError('Your account does not have access to this content', expected=True)
            raise

    def _call_post_api(self, video_id):
        return self._call_api(f'/post/v1.0/post-{video_id}?fieldSet=postV1', video_id)


class WeverseIE(WeverseBaseIE):
    _VALID_URL = r'https?://(?:www\.|m\.)?weverse.io/(?P<artist>[^/?#]+)/live/(?P<id>[\d-]+)'
    _TESTS = [{
        'url': 'https://weverse.io/billlie/live/0-107323480',
        'md5': '1fa849f00181eef9100d3c8254c47979',
        'info_dict': {
            'id': '0-107323480',
            'ext': 'mp4',
            'title': '행복한 평이루💜',
            'description': '',
            'uploader': 'Billlie',
            'uploader_id': 'billlie',
            'timestamp': 1666262058,
            'upload_date': '20221020',
            'release_timestamp': 1666262062,
            'release_date': '20221020',
            'duration': 3102,
            'thumbnail': r're:^https?://.*\.jpe?g$',
        },
    }]

    def _real_extract(self, url):
        uploader_id, video_id = self._match_valid_url(url).group('artist', 'id')
        post = self._call_post_api(video_id)
        api_video_id = post['extension']['video']['videoId']
        infra_video_id = post['extension']['video']['infraVideoId']

        in_key = self._call_api(
            f'/video/v1.0/vod/{api_video_id}/inKey?preview=false', video_id,
            data=b'{}', note='Downloading VOD API key')['inKey']

        vod = self._download_json(
            f'https://global.apis.naver.com/rmcnmv/rmcnmv/vod/play/v2.0/{infra_video_id}', video_id,
            note='Downloading VOD JSON', query={
                'key': in_key,
                'sid': traverse_obj(post, ('extension', 'video', 'serviceId')) or '2070',
                'pid': str(uuid.uuid4()),
                'nonce': int(time.time() * 1000),
                'devt': 'html5_pc',
                'prv': 'Y' if post.get('membershipOnly') else 'N',
                'aup': 'N',
                'stpb': 'N',
                'cpl': 'en',
                'env': 'prod',
                'lc': 'en',
                'adi': '[{"adSystem":"null"}]',
                'adu': '/',
            })

        formats = traverse_obj(vod, ('videos', 'list', lambda _, v: url_or_none(v['source']), {
            'url': 'source',
            'width': ('encodingOption', 'width', {int_or_none}),
            'height': ('encodingOption', 'height', {int_or_none}),
            'vcodec': 'type',
            'vbr': ('bitrate', 'video', {int_or_none}),
            'abr': ('bitrate', 'audio', {int_or_none}),
            'filesize': ('size', {int_or_none}),
            'format_id': ('encodingOption', 'id', {str_or_none}),
        }))

        for stream in traverse_obj(vod, ('streams', lambda _, v: v['type'] == 'HLS' and url_or_none(v['source']))):
            query = {}
            for param in traverse_obj(stream, ('keys', lambda _, v: v['type'] == 'param' and v['name'])):
                query.update({param['name']: param.get('value', '')})
            fmts = self._extract_m3u8_formats(
                stream['source'], video_id, 'mp4', m3u8_id='hls', fatal=False, query=query) or []
            if query:
                for fmt in fmts:
                    fmt['url'] = update_url_query(fmt['url'], query)
                    fmt['extra_param_to_segment_url'] = urllib.parse.urlencode(query)
            formats.extend(fmts)

        return {
            'id': video_id,
            'uploader_id': uploader_id,
            'formats': formats,
            **traverse_obj(post, {
                'title': (None, (('extension', 'mediaInfo', 'title'), 'title'), {str}),
                'description': (None, (('extension', 'mediaInfo', 'body'), 'body'), {str}),
                'uploader': ('author', 'profileName', {str}),
                'duration': ('extension', 'video', 'playTime', {float_or_none}),
                'timestamp': ('extension', 'video', 'onAirStartAt', {lambda x: int_or_none(x, 1000)}),
                'release_timestamp': ('publishedAt', {lambda x: int_or_none(x, 1000)}),
                'thumbnail': ('extension', (('mediaInfo', 'thumbnail', 'url'), ('video', 'thumb')), {url_or_none}),
                'is_live': ('extension', 'video', 'type', {lambda x: x != 'VOD'})
            }, get_all=False),
        }


class WeverseMediaIE(WeverseBaseIE):
    _VALID_URL = r'https?://(?:www\.|m\.)?weverse.io/(?P<artist>[^/?#]+)/media/(?P<id>[\d-]+)'
    _TESTS = [{
        'url': 'https://weverse.io/billlie/media/4-116372884',
        'md5': '8efc9cfd61b2f25209eb1a5326314d28',
        'info_dict': {
            'id': 'e-C9wLSQs6o',
            'ext': 'mp4',
            'title': 'Billlie | \'EUNOIA\' Performance Video (heartbeat ver.)',
            'description': 'md5:6181caaf2a2397bca913ffe368c104e5',
            'channel': 'Billlie',
            'channel_id': 'UCyc9sUCxELTDK9vELO5Fzeg',
            'channel_url': 'https://www.youtube.com/channel/UCyc9sUCxELTDK9vELO5Fzeg',
            'uploader': 'Billlie',
            'uploader_id': '@Billlie',
            'uploader_url': 'http://www.youtube.com/@Billlie',
            'upload_date': '20230403',
            'duration': 211,
            'age_limit': 0,
            'playable_in_embed': True,
            'live_status': 'not_live',
            'availability': 'public',
            'view_count': int,
            'comment_count': int,
            'like_count': int,
            'channel_follower_count': int,
            'thumbnail': 'https://i.ytimg.com/vi/e-C9wLSQs6o/maxresdefault.jpg',
            'categories': ['Entertainment'],
            'tags': 'count:7',
        },
    }, {
        'url': 'https://weverse.io/billlie/media/3-102914520',
        'md5': '031551fcbd716bc4f080cb6174a43d8a',
        'info_dict': {
            'id': '3-102914520',
            'ext': 'mp4',
            'title': 'From. SUHYEON🌸',
            'description': 'Billlie 멤버별 독점 영상 공개💙💜',
            'uploader': 'Billlie_official',
            'uploader_id': 'billlie',
            'timestamp': 1662174000,
            'upload_date': '20220903',
            'release_timestamp': 1662174000,
            'release_date': '20220903',
            'duration': 17.0,
            'thumbnail': r're:^https?://.*\.jpe?g$',
        },
    }]

    def _real_extract(self, url):
        uploader_id, video_id = self._match_valid_url(url).group('artist', 'id')
        post = self._call_post_api(video_id)
        media_type = traverse_obj(post, ('extension', 'mediaInfo', 'mediaType', {str.lower}))
        youtube_id = traverse_obj(post, ('extension', 'youtube', 'youtubeVideoId', {str}))

        if media_type == 'vod':
            return self.url_result(f'https://weverse.io/{uploader_id}/live/{video_id}', WeverseIE)
        elif media_type == 'youtube' and youtube_id:
            return self.url_result(youtube_id, YoutubeIE)
        elif media_type == 'image':
            self.raise_no_formats('No video content found in webpage', expected=True)
        elif media_type:
            raise ExtractorError(f'Unsupported media type "{media_type}"')

        self.raise_no_formats('No video content found in webpage')
