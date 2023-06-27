from .common import InfoExtractor

from ..utils import (
    HEADRequest,
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
        self._request_webpage(HEADRequest('https://kick.com/'), None, 'Setting up session', fatal=False)
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
            headers=merge_dicts(headers, self._API_HEADERS), **kwargs)


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
        'url': 'https://kick.com/video/54244b5e-050a-4df4-a013-b2433dafbe35',
        'md5': '73691206a6a49db25c5aa1588e6538fc',
        'info_dict': {
            'id': '54244b5e-050a-4df4-a013-b2433dafbe35',
            'ext': 'mp4',
            'title': 'Making 710-carBoosting. Kinda No Pixel inspired.  !guilded  - !links',
            'description': 'md5:a0d3546bf7955d0a8252ffe0fd6f518f',
            'channel': 'kmack710',
            'channel_id': '16278',
            'uploader': 'Kmack710',
            'uploader_id': '16412',
            'upload_date': '20221206',
            'timestamp': 1670318289,
            'duration': 40104.0,
            'thumbnail': r're:^https?://.*\.jpg',
            'categories': ['Grand Theft Auto V'],
        },
        'params': {
            'skip_download': 'm3u8',
        },
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
