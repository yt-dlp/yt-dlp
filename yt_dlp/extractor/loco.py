import json
import random
import time

from .common import InfoExtractor
from ..utils import int_or_none, jwt_decode_hs256, try_call, url_or_none
from ..utils.traversal import require, traverse_obj


class LocoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?loco\.com/(?P<type>streamers|stream)/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://loco.com/streamers/teuzinfps',
        'info_dict': {
            'id': 'teuzinfps',
            'ext': 'mp4',
            'title': r're:MS BOLADAO, RESENHA & GAMEPLAY ALTO NIVEL',
            'description': 'bom e novo',
            'uploader_id': 'RLUVE3S9JU',
            'channel': 'teuzinfps',
            'channel_follower_count': int,
            'comment_count': int,
            'view_count': int,
            'concurrent_view_count': int,
            'like_count': int,
            'thumbnail': 'https://static.ivory.getloconow.com/default_thumb/743701a9-98ca-41ae-9a8b-70bd5da070ad.jpg',
            'tags': ['MMORPG', 'Gameplay'],
            'series': 'Tibia',
            'timestamp': int,
            'modified_timestamp': int,
            'live_status': 'is_live',
            'upload_date': str,
            'modified_date': str,
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }, {
        'url': 'https://loco.com/stream/c64916eb-10fb-46a9-9a19-8c4b7ed064e7',
        'md5': '8b9bda03eba4d066928ae8d71f19befb',
        'info_dict': {
            'id': 'c64916eb-10fb-46a9-9a19-8c4b7ed064e7',
            'ext': 'mp4',
            'title': 'PAULINHO LOKO NA LOCO!',
            'description': 'live on na loco',
            'uploader_id': '2MDO7Z1DPM',
            'channel': 'paulinholokobr',
            'channel_follower_count': int,
            'comment_count': int,
            'view_count': int,
            'concurrent_view_count': int,
            'like_count': int,
            'duration': 14491,
            'thumbnail': 'https://static.ivory.getloconow.com/default_thumb/59b5970b-23c1-4518-9e96-17ce341299fe.jpg',
            'tags': ['Gameplay'],
            'series': 'GTA 5',
            'timestamp': 1740612872,
            'modified_timestamp': 1750948439,
            'upload_date': '20250226',
            'modified_date': '20250626',
        },
    }, {
        # Requires video authorization
        'url': 'https://loco.com/stream/ac854641-ae0f-497c-a8ea-4195f6d8cc53',
        'md5': '0513edf85c1e65c9521f555f665387d5',
        'info_dict': {
            'id': 'ac854641-ae0f-497c-a8ea-4195f6d8cc53',
            'ext': 'mp4',
            'title': 'DUAS CONTAS DESAFIANTE, RUSH TOP 1 NO BRASIL!',
            'description': 'md5:aa77818edd6fe00dd4b6be75cba5f826',
            'uploader_id': '7Y9JNAZC3Q',
            'channel': 'ayellol',
            'channel_follower_count': int,
            'comment_count': int,
            'view_count': int,
            'concurrent_view_count': int,
            'like_count': int,
            'duration': 1229,
            'thumbnail': 'https://static.ivory.getloconow.com/default_thumb/f5aa678b-6d04-45d9-a89a-859af0a8028f.jpg',
            'tags': ['Gameplay', 'Carry'],
            'series': 'League of Legends',
            'timestamp': 1741182253,
            'upload_date': '20250305',
            'modified_timestamp': 1741182419,
            'modified_date': '20250305',
        },
    }]

    # From _app.js
    _CLIENT_ID = 'TlwKp1zmF6eKFpcisn3FyR18WkhcPkZtzwPVEEC3'
    _CLIENT_SECRET = 'Kp7tYlUN7LXvtcSpwYvIitgYcLparbtsQSe5AdyyCdiEJBP53Vt9J8eB4AsLdChIpcO2BM19RA3HsGtqDJFjWmwoonvMSG3ZQmnS8x1YIM8yl82xMXZGbE3NKiqmgBVU'

    def _is_jwt_expired(self, token):
        return jwt_decode_hs256(token)['exp'] - time.time() < 300

    def _get_access_token(self, video_id):
        access_token = try_call(lambda: self._get_cookies('https://loco.com')['access_token'].value)
        if access_token and not self._is_jwt_expired(access_token):
            return access_token
        access_token = traverse_obj(self._download_json(
            'https://api.getloconow.com/v3/user/device_profile/', video_id,
            'Downloading access token', fatal=False, data=json.dumps({
                'platform': 7,
                'client_id': self._CLIENT_ID,
                'client_secret': self._CLIENT_SECRET,
                'model': 'Mozilla',
                'os_name': 'Win32',
                'os_ver': '5.0 (Windows)',
                'app_ver': '5.0 (Windows)',
            }).encode(), headers={
                'Content-Type': 'application/json;charset=utf-8',
                'DEVICE-ID': ''.join(random.choices('0123456789abcdef', k=32)) + 'live',
                'X-APP-LANG': 'en',
                'X-APP-LOCALE': 'en-US',
                'X-CLIENT-ID': self._CLIENT_ID,
                'X-CLIENT-SECRET': self._CLIENT_SECRET,
                'X-PLATFORM': '7',
            }), 'access_token')
        if access_token and not self._is_jwt_expired(access_token):
            self._set_cookie('.loco.com', 'access_token', access_token)
            return access_token

    def _real_extract(self, url):
        video_type, video_id = self._match_valid_url(url).group('type', 'id')
        webpage = self._download_webpage(url, video_id)
        stream = traverse_obj(self._search_nextjs_v13_data(webpage, video_id), (
            ..., (None, 'ssrData'), ('liveStreamData', 'stream', 'liveStream'), {dict}, any, {require('stream info')}))

        if access_token := self._get_access_token(video_id):
            self._request_webpage(
                'https://drm.loco.com/v1/streams/playback/', video_id,
                'Downloading video authorization', fatal=False, headers={
                    'authorization': access_token,
                }, query={
                    'stream_uid': stream['uid'],
                })

        return {
            'formats': self._extract_m3u8_formats(stream['conf']['hls'], video_id),
            'id': video_id,
            'is_live': video_type == 'streamers',
            **traverse_obj(stream, {
                'title': ('title', {str}),
                'series': ('game_name', {str}),
                'uploader_id': ('user_uid', {str}),
                'channel': ('alias', {str}),
                'description': ('description', {str}),
                'concurrent_view_count': ('viewersCurrent', {int_or_none}),
                'view_count': ('total_views', {int_or_none}),
                'thumbnail': ('thumbnail_url_small', {url_or_none}),
                'like_count': ('likes', {int_or_none}),
                'tags': ('tags', ..., {str}),
                'timestamp': ('started_at', {int_or_none(scale=1000)}),
                'modified_timestamp': ('updated_at', {int_or_none(scale=1000)}),
                'comment_count': ('comments_count', {int_or_none}),
                'channel_follower_count': ('followers_count', {int_or_none}),
                'duration': ('duration', {int_or_none}),
            }),
        }
