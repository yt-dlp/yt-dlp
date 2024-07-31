from .common import InfoExtractor
from ..networking import HEADRequest
from ..utils import (
    UserNotLive,
    determine_ext,
    float_or_none,
    int_or_none,
    merge_dicts,
    parse_iso8601,
    str_or_none,
    traverse_obj,
    unified_timestamp,
    url_or_none,
)
class KickBaseIE(InfoExtractor):
    def _real_initialize(self):
        self._request_webpage(
            HEADRequest('https://kick.com/'), None, 'Setting up session', fatal=False, impersonate=True)
        xsrf_token = self._get_cookies('https://kick.com/').get('XSRF-TOKEN')
        if not xsrf_token:
            self.write_debug('kick.com did not set XSRF-TOKEN cookie')
        KickBaseIE._API_HEADERS = {
            'Authorization': f'Bearer {xsrf_token.value}',
            'X-XSRF-TOKEN': xsrf_token.value,
        } if xsrf_token else {}

    def _call_api(self, path, display_id, note='Downloading API JSON', headers={}, **kwargs):
        return self._download_json(
            f'https://kick.com/api/{path}', display_id, note=note,
            headers=merge_dicts(headers, self._API_HEADERS), impersonate=True, **kwargs)


class KickIE(KickBaseIE):
    IE_NAME = 'kick:live'
    _VALID_URL = r'https?://(?:www\.)?kick\.com/(?!(?:video|categories|search|auth)(?:[/?#]|$))(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://kick.com/xqc',
        'info_dict': {
            'id': '09886759-clickliveall-nightgamesstuff',
            'ext': 'mp4',
            'title': str,
            'description': str,
            'channel': 'xqc',
            'channel_id': 668,
            'uploader': 'xQc',
            'uploader_id': 676,
            'upload_date': str,
            'live_status': 'is_live',
            'timestamp': int,
            'thumbnail': r're:^https?://.*\.jpg',
            'categories': list,
            'language': 'English',
        },
        'skip': 'livestream',
    }, {
        'url': 'https://kick.com/xqc',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if KickClipIE.suitable(url) else super().suitable(url)

    def _real_extract(self, url):
        channel = self._match_id(url)
        response = self._call_api(f'v2/channels/{channel}', channel)
        if not traverse_obj(response, 'livestream', expected_type=dict):
            raise UserNotLive(video_id=channel)

        return {
            'id': str(traverse_obj(
                response, ('livestream', ('slug', 'id')), get_all=False, default=channel)),
            'formats': self._extract_m3u8_formats(
                response['playback_url'], channel, 'mp4', live=True),
            'title': traverse_obj(
                response, ('livestream', ('session_title', 'slug')), get_all=False, default=''),
            'description': traverse_obj(response, ('user', 'bio')),
            'channel': channel,
            'channel_id': str_or_none(traverse_obj(response, 'id', ('livestream', 'channel_id'))),
            'uploader': traverse_obj(response, 'name', ('user', 'username')),
            'uploader_id': str_or_none(traverse_obj(response, 'user_id', ('user', 'id'))),
            'is_live': True,
            'timestamp': unified_timestamp(traverse_obj(response, ('livestream', 'created_at'))),
            'thumbnail': traverse_obj(
                response, ('livestream', 'thumbnail', 'url'), expected_type=url_or_none),
            'categories': traverse_obj(response, ('recent_categories', ..., 'name')),
        }


class KickVODIE(KickBaseIE):
    IE_NAME = 'kick:vods'
    _VALID_URL = r'https?://(?:www\.)?kick\.com/video/(?P<id>[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12})'
    _TESTS = [{
        'url': 'https://kick.com/video/e74614f4-5270-4319-90ad-32179f19a45c',
        'md5': '3870f94153e40e7121a6e46c068b70cb',
        'info_dict': {
            'id': 'e74614f4-5270-4319-90ad-32179f19a45c',
            'ext': 'mp4',
            'title': '❎ MEGA DRAMA ❎ LIVE ❎ CLICK ❎ ULTIMATE SKILLS ❎ 100% JUICER ❎ GAMER EXTRAORDINAIRE ❎ TIME TO WIN ❎ AT EVERY SINGLE THING ❎ MUSCLES MASSIVE ❎ BRAIN HUGE ❎',
            'description': 'THE BEST AT ABSOLUTELY EVERYTHING. THE JUICER. LEADER OF THE JUICERS.',
            'channel': 'xqc',
            'channel_id': 668,
            'uploader': 'xQc',
            'uploader_id': 676,
            'upload_date': '20240724',
            'timestamp': 1721796562,
            'duration': 18566.0,
            'thumbnail': r're:^https?://.*\.jpg',
            'categories': ['VALORANT'],
        },
        'params': {
            'skip_download': 'm3u8',
        },
        'expected_warnings': [r'impersonation'],
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        response = self._call_api(f'v1/video/{video_id}', video_id)

        return {
            'id': video_id,
            'formats': self._extract_m3u8_formats(response['source'], video_id, 'mp4'),
            'title': traverse_obj(
                response, ('livestream', ('session_title', 'slug')), get_all=False, default=''),
            'description': traverse_obj(response, ('livestream', 'channel', 'user', 'bio')),
            'channel': traverse_obj(response, ('livestream', 'channel', 'slug')),
            'channel_id': str_or_none(traverse_obj(response, ('livestream', 'channel', 'id'))),
            'uploader': traverse_obj(response, ('livestream', 'channel', 'user', 'username')),
            'uploader_id': str_or_none(traverse_obj(response, ('livestream', 'channel', 'user_id'))),
            'timestamp': unified_timestamp(response.get('created_at')),
            'duration': float_or_none(traverse_obj(response, ('livestream', 'duration')), scale=1000),
            'thumbnail': traverse_obj(
                response, ('livestream', 'thumbnail'), expected_type=url_or_none),
            'categories': traverse_obj(response, ('livestream', 'categories', ..., 'name')),
        }


class KickClipIE(KickBaseIE):
    IE_NAME = 'kick:clips'
    _VALID_URL = r'https?://(?:www\.)?kick\.com/[\w-]+/?\?(?:[^#]+&)?clip=(?P<id>clip_[\w-]+)'
    _TESTS = [{
        'url': 'https://kick.com/mxddy?clip=clip_01GYXVB5Y8PWAPWCWMSBCFB05X',
        'info_dict': {
            'id': 'clip_01GYXVB5Y8PWAPWCWMSBCFB05X',
            'ext': 'mp4',
            'livestream_id': 1855384,
            'title': 'Maddy detains Abd D:',
            'category_id': 64,
            'channel': 'Mxddy',
            'channel_id': 133789,
            'uploader': 'AbdCreates',
            'uploader_id': 3309077,
            'thumbnail': r're:^https?://.*\.jpeg',
            'duration': 35,
            'category': 'VALORANT',
            'upload_date': '20230426',
            'view_count': int,
            'like_count': int,
            'is_mature': True,
        },
        'params': {
            'skip_download': 'm3u8',
        },
        'expected_warnings': [r'impersonation'],
    }, {
        'url': 'https://kick.com/destiny?clip=clip_01H9SKET879NE7N9RJRRDS98J3',

        'info_dict': {
            'id': 'clip_01H9SKET879NE7N9RJRRDS98J3',
            'title': 'W jews',
            'ext': 'mp4',
            'view_count': int,
            'like_count': int,
            'is_mature': False,
            'duration': 49.0,
            'thumbnail': 'https://clips.kick.com/clips/j3/clip_01H9SKET879NE7N9RJRRDS98J3/thumbnail.png',
            'uploader_id': 2027722,
            'channel': 'Destiny',
            'channel_id': 1772249,
            'category_id': 15,
            'uploader': 'punished_furry',
            'category': 'Just Chatting',
            'livestream_id': 14549749,
            'upload_date': '20230908',
        },
        'params': {
            'skip_download': 'm3u8',
        },
        'expected_warnings': [r'impersonation'],

    }]

    def _real_extract(self, url):

        clip_id = self._match_id(url)
        clip = self._call_api(f'v2/clips/{clip_id}/play', clip_id)['clip']
        clip_url = clip['clip_url']

        if determine_ext(clip_url) == 'm3u8':
            formats = self._extract_m3u8_formats(clip_url, clip_id, 'mp4')
        else:
            formats = [{'url': clip_url}]

        return {
            'id': clip_id,
            'formats': formats,
            'ext': 'mp4',
            **traverse_obj(clip, {
                'title': ('title', {str}),
                'description': ('livestream_id', {str}, {lambda x: f'Clipped from {x}' if x else None}),
                'channel': ('channel', 'username', {str}),
                'channel_id': ('channel', 'id', {int}, {str_or_none}),
                'uploader': ('creator', 'username', {str}),
                'uploader_id': ('creator', 'id', {int}, {str_or_none}),
                'thumbnail': ('thumbnail_url', {url_or_none}),
                'duration': ('duration', {float_or_none}),
                'categories': ('category', 'name', {str}, all),
                'timestamp': ('created_at', {parse_iso8601}),
                'view_count': ('views', {int_or_none}),
                'like_count': ('likes', {int_or_none}),
                'age_limit': ('is_mature', {bool}, {lambda x: 18 if x else 0}),
            }),
        }
