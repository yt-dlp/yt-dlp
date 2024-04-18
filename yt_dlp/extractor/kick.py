from .common import InfoExtractor
from ..networking import HEADRequest
from ..utils import (
    UserNotLive,
    float_or_none,
    merge_dicts,
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
            f'https://kick.com/api/v1/{path}', display_id, note=note,
            headers=merge_dicts(headers, self._API_HEADERS), impersonate=True, **kwargs)


class KickIE(KickBaseIE):
    _VALID_URL = r'https?://(?:www\.)?kick\.com/(?!(?:video|categories|search|auth)(?:[/?#]|$))(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://kick.com/yuppy',
        'info_dict': {
            'id': '6cde1-kickrp-joe-flemmingskick-info-heremust-knowmust-see21',
            'ext': 'mp4',
            'title': str,
            'description': str,
            'channel': 'yuppy',
            'channel_id': '33538',
            'uploader': 'Yuppy',
            'uploader_id': '33793',
            'upload_date': str,
            'live_status': 'is_live',
            'timestamp': int,
            'thumbnail': r're:^https?://.*\.jpg',
            'categories': list,
        },
        'skip': 'livestream',
    }, {
        'url': 'https://kick.com/kmack710',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        channel = self._match_id(url)
        response = self._call_api(f'channels/{channel}', channel)
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
    _VALID_URL = r'https?://(?:www\.)?kick\.com/video/(?P<id>[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12})'
    _TESTS = [{
        'url': 'https://kick.com/video/58bac65b-e641-4476-a7ba-3707a35e60e3',
        'md5': '3870f94153e40e7121a6e46c068b70cb',
        'info_dict': {
            'id': '58bac65b-e641-4476-a7ba-3707a35e60e3',
            'ext': 'mp4',
            'title': '🤠REBIRTH IS BACK!!!!🤠!stake CODE JAREDFPS 🤠',
            'description': 'md5:02b0c46f9b4197fb545ab09dddb85b1d',
            'channel': 'jaredfps',
            'channel_id': '26608',
            'uploader': 'JaredFPS',
            'uploader_id': '26799',
            'upload_date': '20240402',
            'timestamp': 1712097108,
            'duration': 33859.0,
            'thumbnail': r're:^https?://.*\.jpg',
            'categories': ['Call of Duty: Warzone'],
        },
        'params': {
            'skip_download': 'm3u8',
        },
        'expected_warnings': [r'impersonation'],
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        response = self._call_api(f'video/{video_id}', video_id)

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
