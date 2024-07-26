from yt_dlp.utils._utils import unified_strdate

from .common import InfoExtractor
from ..networking import HEADRequest
from ..utils import (
    UserNotLive,
    float_or_none,
    int_or_none,
    merge_dicts,
    traverse_obj,
    unified_timestamp,
    url_or_none,
)

# Routes ----------------------

# Clips
# https://kick.com/mxddy?clip=clip_01GYXVB5Y8PWAPWCWMSBCFB05X
# https://kick.com/api/v2/clips/clip_01GYXVB5Y8PWAPWCWMSBCFB05X

# Livestream
# https://kick.com/xqc
# https://kick.com/api/v2/channels/xqc

# VODs
# https://kick.com/video/e74614f4-5270-4319-90ad-32179f19a45c
# https://kick.com/api/v1/video/e74614f4-5270-4319-90ad-32179f19a45c


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
            'channel_id': int_or_none(traverse_obj(response, 'id', ('livestream', 'channel_id'))),
            'uploader': traverse_obj(response, 'name', ('user', 'username')),
            'uploader_id': int_or_none(traverse_obj(response, 'user_id', ('user', 'id'))),
            'is_live': True,
            'timestamp': unified_timestamp(traverse_obj(response, ('livestream', 'created_at'))),
            'thumbnail': traverse_obj(
                response, ('livestream', 'thumbnail', 'url'), expected_type=url_or_none),
            'categories': traverse_obj(response, ('recent_categories', ..., 'name')),
            'language': traverse_obj(
                response, ('livestream', ('language')), get_all=False, default=''),
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
            'channel_id': int_or_none(traverse_obj(response, ('livestream', 'channel', 'id'))),
            'uploader': traverse_obj(response, ('livestream', 'channel', 'user', 'username')),
            'uploader_id': int_or_none(traverse_obj(response, ('livestream', 'channel', 'user_id'))),
            'timestamp': unified_timestamp(response.get('created_at')),
            'duration': float_or_none(traverse_obj(response, ('livestream', 'duration')), scale=1000),
            'thumbnail': traverse_obj(
                response, ('livestream', 'thumbnail'), expected_type=url_or_none),
            'categories': traverse_obj(response, ('livestream', 'categories', ..., 'name')),
        }


class KickClipIE(KickBaseIE):
    IE_NAME = 'kick:clips'
    _VALID_URL = r'https?://(?:www\.)?kick\.com/(?P<channel>[\w-]+)\?clip=(?P<id>clip_[\w-]+)'
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
    }]

    def _real_extract(self, url):

        channel_slug, clip_id = self._match_valid_url(url).groups()
        response = self._call_api(f'v2/clips/{clip_id}/play', clip_id, note='Getting clip information')
        clip = traverse_obj(response, 'clip', expected_type=dict)

        return {
            'id': clip_id,
            'formats': [
                {
                    'url': traverse_obj(clip, 'video_url'),
                    'ext': 'mp4',
                },
            ],
            'title': traverse_obj(clip, 'title', default=''),
            'livestream_id': int_or_none(traverse_obj(clip, 'livestream_id')),
            'category_id': int_or_none(traverse_obj(clip, 'category_id')),
            'channel': traverse_obj(clip, ('channel', 'username')),
            'channel_id': int_or_none(traverse_obj(clip, ('channel', 'id'))),
            'uploader': traverse_obj(clip, ('creator', 'username')),
            'uploader_id': int_or_none(traverse_obj(clip, ('creator', 'id'))),
            'thumbnail': url_or_none(traverse_obj(clip, 'thumbnail_url')),
            'duration': float_or_none(traverse_obj(clip, 'duration')),
            'category': traverse_obj(clip, ('category', 'name'), default=''),
            'upload_date': unified_strdate(traverse_obj(clip, 'created_at')),
            'view_count': int_or_none(traverse_obj(clip, 'likes')),
            'like_count': int_or_none(traverse_obj(clip, 'views')),
            'is_mature': traverse_obj(clip, 'is_mature'),
        }
