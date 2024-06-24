from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    parse_iso8601,
    traverse_obj,
    urljoin,
)


class CaffeineTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?caffeine\.tv/[^/?#]+/video/(?P<id>[\da-f-]+)'
    _TESTS = [{
        'url': 'https://www.caffeine.tv/TsuSurf/video/cffc0a00-e73f-11ec-8080-80017d29f26e',
        'info_dict': {
            'id': 'cffc0a00-e73f-11ec-8080-80017d29f26e',
            'ext': 'mp4',
            'title': 'GOOOOD MORNINNNNN #highlights',
            'timestamp': 1654702180,
            'upload_date': '20220608',
            'uploader': 'RahJON Wicc',
            'uploader_id': 'TsuSurf',
            'duration': 3145,
            'age_limit': 17,
            'thumbnail': 'https://www.caffeine.tv/broadcasts/776b6f84-9cd5-42e3-af1d-4a776eeed697/replay/lobby.jpg',
            'comment_count': int,
            'view_count': int,
            'like_count': int,
            'tags': ['highlights', 'battlerap'],
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        json_data = self._download_json(
            f'https://api.caffeine.tv/social/public/activity/{video_id}', video_id)
        broadcast_info = traverse_obj(json_data, ('broadcast_info', {dict})) or {}

        video_url = broadcast_info['video_url']
        ext = determine_ext(video_url)
        if ext == 'm3u8':
            formats = self._extract_m3u8_formats(video_url, video_id, 'mp4')
        else:
            formats = [{'url': video_url}]

        return {
            'id': video_id,
            'formats': formats,
            **traverse_obj(json_data, {
                'like_count': ('like_count', {int_or_none}),
                'view_count': ('view_count', {int_or_none}),
                'comment_count': ('comment_count', {int_or_none}),
                'tags': ('tags', ..., {str}, {lambda x: x or None}),
                'uploader': ('user', 'name', {str}),
                'uploader_id': (((None, 'user'), 'username'), {str}, any),
                'is_live': ('is_live', {bool}),
            }),
            **traverse_obj(broadcast_info, {
                'title': ('broadcast_title', {str}),
                'duration': ('content_duration', {int_or_none}),
                'timestamp': ('broadcast_start_time', {parse_iso8601}),
                'thumbnail': ('preview_image_path', {lambda x: urljoin(url, x)}),
            }),
            'age_limit': {
                # assume Apple Store ratings: https://en.wikipedia.org/wiki/Mobile_software_content_rating_system
                'FOUR_PLUS': 0,
                'NINE_PLUS': 9,
                'TWELVE_PLUS': 12,
                'SEVENTEEN_PLUS': 17,
            }.get(broadcast_info.get('content_rating'), 17),
        }
