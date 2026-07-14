from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    UserNotLive,
    clean_html,
    int_or_none,
    join_nonempty,
    parse_resolution,
    url_or_none,
)
from ..utils.traversal import require, traverse_obj


class WhoWatchIE(InfoExtractor):
    IE_NAME = 'whowatch'
    IE_DESC = 'ふわっち'

    _API_BASE = 'https://api.whowatch.tv/lives'
    _VALID_URL = r'https?://whowatch\.tv/(?P<type>archives|viewer)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://whowatch.tv/viewer/74386035',
        'info_dict': {
            'id': '74386035',
            'ext': 'mp4',
            'title': str,
            'categories': ['雑談'],
            'comment_count': int,
            'concurrent_view_count': int,
            'description': '母業',
            'like_count': int,
            'live_status': 'is_live',
            'thumbnail': r're:https?://.+',
            'timestamp': 1784016434,
            'upload_date': '20260714',
            'uploader': 'よるの⭐️ひかり',
            'uploader_id': 'ふ:pikari',
            'uploader_url': 'https://whowatch.tv/profile/w:pikari',
            'view_count': int,
        },
        'skip': 'Invalid URL',
    }, {
        'url': 'https://whowatch.tv/archives/73287032',
        'info_dict': {
            'id': '73287032',
            'ext': 'mp4',
            'title': '森黒之 最後の放送',
            'categories': ['雑談'],
            'comment_count': int,
            'description': '最後の見送り',
            'duration': 10802,
            'live_status': 'was_live',
            'thumbnail': r're:https?://.+',
            'timestamp': 1780615257,
            'upload_date': '20260604',
            'uploader': 'Yossan',
            'uploader_id': 'ふ:yossan',
            'uploader_url': 'https://whowatch.tv/profile/w:yossan',
            'view_count': int,
        },
    }]

    def _call_api(self, video_id, endpoint=None, query=None):
        api_url = f'{self._API_BASE}/{video_id}'
        if endpoint:
            api_url += f'/{endpoint}'

        return self._download_json(api_url, video_id, query=query)

    def _real_extract(self, url):
        video_type, video_id = self._match_valid_url(url).group('type', 'id')
        live_info = self._call_api(video_id)
        if err_code := traverse_obj(live_info, (
            'error_code', {str}, filter,
        )):
            err_msg = traverse_obj(live_info, (
                'error_message', {clean_html}, filter))
            raise ExtractorError(join_nonempty(err_code, err_msg, delim=': '))

        live_status_key = traverse_obj(live_info, ('live', 'live_status', {str}))
        live_status = {
            'DELETED': 'was_live',
            'FINISHED': 'was_live',
            'PUBLISHING': 'is_live',
        }.get(live_status_key)
        user_path = traverse_obj(live_info, ('live', 'user', 'user_path', {str}))

        if video_type == 'archives':
            if live_status_key == 'DELETED':
                raise ExtractorError(
                    'This video is no longer available', expected=True)

            stream_info = self._call_api(video_id, 'play_archive')
            playback_data = traverse_obj(live_info, {
                'duration': ('live', 'running_time', {int_or_none}),
                'view_count': ('archive_play_count', {int_or_none}),
            })
        else:
            if live_status != 'is_live':
                raise UserNotLive(video_id=user_path)

            stream_info = self._call_api(video_id, 'watch_info', query={'hls': 'true'})
            playback_data = traverse_obj(live_info, ('live', {
                'concurrent_view_count': ('view_count', {int_or_none}),
                'view_count': ('total_view_count', {int_or_none}),
            }))

        m3u8_url = traverse_obj(stream_info, (
            'hls_url', {url_or_none}, {require('m3u8 URL')}))
        formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4')
        for fmt in formats:
            fmt.update(parse_resolution(fmt['url'], parse_fps=True))
            if self.get_param('live_from_start'):
                fmt.setdefault('downloader_options', {}).update({'ffmpeg_args': ['-live_start_index', '0']})
                fmt['is_from_start'] = True

        return {
            'id': video_id,
            'comment_count': traverse_obj(live_info, ('comment_count', {int_or_none})),
            'formats': formats,
            'live_status': live_status,
            'uploader_url': f'https://whowatch.tv/profile/{user_path}',
            **playback_data,
            **traverse_obj(live_info, ('live', {
                'title': ('title', {clean_html}, filter),
                'categories': ('category', 'name', {clean_html}, filter, all, filter),
                'description': ('telop', {clean_html}, filter),
                'like_count': ('nice_info', 'total_count', {int_or_none}),
                'thumbnail': ('latest_thumbnail_url', {url_or_none}),
                'timestamp': ('started_at', {int_or_none(scale=1000)}),
            })),
            **traverse_obj(live_info, ('live', 'user', {
                'uploader': ('name', {clean_html}, filter),
                'uploader_id': ('account_name', {str}),
            })),
        }
