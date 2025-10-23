import functools
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    UserNotLive,
    determine_ext,
    float_or_none,
    int_or_none,
    parse_iso8601,
    str_or_none,
    traverse_obj,
    unified_timestamp,
    url_or_none,
)


class KickBaseIE(InfoExtractor):
    @functools.cached_property
    def _api_headers(self):
        token = traverse_obj(
            self._get_cookies('https://kick.com/'),
            ('session_token', 'value', {urllib.parse.unquote}))
        return {'Authorization': f'Bearer {token}'} if token else {}

    def _call_api(self, path, display_id, note='Downloading API JSON', headers={}, **kwargs):
        return self._download_json(
            f'https://kick.com/api/{path}', display_id, note=note,
            headers={**self._api_headers, **headers}, impersonate=True, **kwargs)


class KickIE(KickBaseIE):
    IE_NAME = 'kick:live'
    _VALID_URL = r'https?://(?:www\.)?kick\.com/(?!(?:video|categories|search|auth)(?:[/?#]|$))(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://kick.com/buddha',
        'info_dict': {
            'id': '92722911-nopixel-40',
            'ext': 'mp4',
            'title': str,
            'description': str,
            'timestamp': int,
            'thumbnail': r're:https?://.+\.jpg',
            'categories': list,
            'upload_date': str,
            'channel': 'buddha',
            'channel_id': '32807',
            'uploader': 'Buddha',
            'uploader_id': '33057',
            'live_status': 'is_live',
            'concurrent_view_count': int,
            'release_timestamp': int,
            'age_limit': 18,
            'release_date': str,
        },
        'params': {'skip_download': 'livestream'},
        # 'skip': 'livestream',
    }, {
        'url': 'https://kick.com/xqc',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if (KickVODIE.suitable(url) or KickClipIE.suitable(url)) else super().suitable(url)

    def _real_extract(self, url):
        channel = self._match_id(url)
        response = self._call_api(f'v2/channels/{channel}', channel)
        if not traverse_obj(response, 'livestream', expected_type=dict):
            raise UserNotLive(video_id=channel)

        return {
            'channel': channel,
            'is_live': True,
            'formats': self._extract_m3u8_formats(response['playback_url'], channel, 'mp4', live=True),
            **traverse_obj(response, {
                'id': ('livestream', 'slug', {str}),
                'title': ('livestream', 'session_title', {str}),
                'description': ('user', 'bio', {str}),
                'channel_id': (('id', ('livestream', 'channel_id')), {int}, {str_or_none}, any),
                'uploader': (('name', ('user', 'username')), {str}, any),
                'uploader_id': (('user_id', ('user', 'id')), {int}, {str_or_none}, any),
                'timestamp': ('livestream', 'created_at', {unified_timestamp}),
                'release_timestamp': ('livestream', 'start_time', {unified_timestamp}),
                'thumbnail': ('livestream', 'thumbnail', 'url', {url_or_none}),
                'categories': ('recent_categories', ..., 'name', {str}),
                'concurrent_view_count': ('livestream', 'viewer_count', {int_or_none}),
                'age_limit': ('livestream', 'is_mature', {bool}, {lambda x: 18 if x else 0}),
            }),
        }


class KickVODIE(KickBaseIE):
    IE_NAME = 'kick:vod'
    _VALID_URL = r'https?://(?:www\.)?kick\.com/[\w-]+/videos/(?P<id>[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12})'
    _TESTS = [{
        # Regular VOD
        'url': 'https://kick.com/xqc/videos/5c697a87-afce-4256-b01f-3c8fe71ef5cb',
        'info_dict': {
            'id': '5c697a87-afce-4256-b01f-3c8fe71ef5cb',
            'ext': 'mp4',
            'title': '🐗LIVE🐗CLICK🐗HERE🐗DRAMA🐗ALL DAY🐗NEWS🐗VIDEOS🐗CLIPS🐗GAMES🐗STUFF🐗WOW🐗IM HERE🐗LETS GO🐗COOL🐗VERY NICE🐗',
            'description': 'THE BEST AT ABSOLUTELY EVERYTHING. THE JUICER. LEADER OF THE JUICERS.',
            'uploader': 'xQc',
            'uploader_id': '676',
            'channel': 'xqc',
            'channel_id': '668',
            'view_count': int,
            'age_limit': 18,
            'duration': 22278.0,
            'thumbnail': r're:^https?://.*\.jpg',
            'categories': ['Deadlock'],
            'timestamp': 1756082443,
            'upload_date': '20250825',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # VOD of ongoing livestream (at the time of writing the test, ID rotates every two days)
        'url': 'https://kick.com/a-log-burner/videos/5230df84-ea38-46e1-be4f-f5949ae55641',
        'info_dict': {
            'id': '5230df84-ea38-46e1-be4f-f5949ae55641',
            'ext': 'mp4',
            'title': r're:😴 Cozy Fireplace ASMR 🔥 | Relax, Focus, Sleep 💤',
            'description': 'md5:080bc713eac0321a7b376a1b53816d1b',
            'uploader': 'A_Log_Burner',
            'uploader_id': '65114691',
            'channel': 'a-log-burner',
            'channel_id': '63967687',
            'view_count': int,
            'age_limit': 18,
            'thumbnail': r're:^https?://.*\.jpg',
            'categories': ['Other, Watch Party'],
            'timestamp': int,
            'upload_date': str,
            'live_status': 'is_live',
        },
        'skip': 'live',
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        response = self._call_api(f'v1/video/{video_id}', video_id)

        return {
            'id': video_id,
            'formats': self._extract_m3u8_formats(response['source'], video_id, 'mp4'),
            **traverse_obj(response, {
                'title': ('livestream', ('session_title', 'slug'), {str}, any),
                'description': ('livestream', 'channel', 'user', 'bio', {str}),
                'channel': ('livestream', 'channel', 'slug', {str}),
                'channel_id': ('livestream', 'channel', 'id', {int}, {str_or_none}),
                'uploader': ('livestream', 'channel', 'user', 'username', {str}),
                'uploader_id': ('livestream', 'channel', 'user_id', {int}, {str_or_none}),
                'timestamp': ('created_at', {parse_iso8601}),
                'duration': ('livestream', 'duration', {float_or_none(scale=1000)}),
                'thumbnail': ('livestream', 'thumbnail', {url_or_none}),
                'categories': ('livestream', 'categories', ..., 'name', {str}),
                'view_count': ('views', {int_or_none}),
                'age_limit': ('livestream', 'is_mature', {bool}, {lambda x: 18 if x else 0}),
                'is_live': ('livestream', 'is_live', {bool}),
            }),
        }


class KickClipIE(KickBaseIE):
    IE_NAME = 'kick:clips'
    _VALID_URL = r'https?://(?:www\.)?kick\.com/[\w-]+(?:/clips/|/?\?(?:[^#]+&)?clip=)(?P<id>clip_[\w-]+)'
    _TESTS = [{
        'url': 'https://kick.com/mxddy?clip=clip_01GYXVB5Y8PWAPWCWMSBCFB05X',
        'info_dict': {
            'id': 'clip_01GYXVB5Y8PWAPWCWMSBCFB05X',
            'ext': 'mp4',
            'title': 'Maddy detains Abd D:',
            'channel': 'mxddy',
            'channel_id': '133789',
            'uploader': 'AbdCreates',
            'uploader_id': '3309077',
            'thumbnail': r're:^https?://.*\.jpeg',
            'duration': 35,
            'timestamp': 1682481453,
            'upload_date': '20230426',
            'view_count': int,
            'like_count': int,
            'categories': ['VALORANT'],
            'age_limit': 18,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://kick.com/destiny?clip=clip_01H9SKET879NE7N9RJRRDS98J3',
        'info_dict': {
            'id': 'clip_01H9SKET879NE7N9RJRRDS98J3',
            'title': 'W jews',
            'ext': 'mp4',
            'channel': 'destiny',
            'channel_id': '1772249',
            'uploader': 'punished_furry',
            'uploader_id': '2027722',
            'duration': 49.0,
            'upload_date': '20230908',
            'timestamp': 1694150180,
            'thumbnail': 'https://clips.kick.com/clips/j3/clip_01H9SKET879NE7N9RJRRDS98J3/thumbnail.png',
            'view_count': int,
            'like_count': int,
            'categories': ['Just Chatting'],
            'age_limit': 0,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://kick.com/spreen/clips/clip_01J8RGZRKHXHXXKJEHGRM932A5',
        'info_dict': {
            'id': 'clip_01J8RGZRKHXHXXKJEHGRM932A5',
            'ext': 'mp4',
            'title': 'KLJASLDJKLJKASDLJKDAS',
            'channel': 'spreen',
            'channel_id': '5312671',
            'uploader': 'AnormalBarraBaja',
            'uploader_id': '26518262',
            'duration': 43.0,
            'upload_date': '20240927',
            'timestamp': 1727399987,
            'thumbnail': 'https://clips.kick.com/clips/f2/clip_01J8RGZRKHXHXXKJEHGRM932A5/thumbnail.webp',
            'view_count': int,
            'like_count': int,
            'categories': ['Minecraft'],
            'age_limit': 0,
        },
        'params': {'skip_download': 'm3u8'},
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
            **traverse_obj(clip, {
                'title': ('title', {str}),
                'channel': ('channel', 'slug', {str}),
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
