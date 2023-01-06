from .common import InfoExtractor
from ..compat import compat_b64decode
from ..utils import (
    ExtractorError,
    int_or_none,
    js_to_json,
    parse_count,
    parse_duration,
    traverse_obj,
    try_get,
    unified_timestamp,
)


class DaftsexIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?daft\.sex/watch/(?P<id>-?\d+_\d+)'
    _TESTS = [{
        'url': 'https://daft.sex/watch/-35370899_456246186',
        'md5': '64c04ef7b4c7b04b308f3b0c78efe7cd',
        'info_dict': {
            'id': '-35370899_456246186',
            'ext': 'mp4',
            'title': 'just relaxing',
            'description': 'just relaxing – Watch video Watch video in high quality',
            'upload_date': '20201113',
            'timestamp': 1605261911,
            'thumbnail': r're:^https?://.*\.jpg$',
            'age_limit': 18,
            'duration': 15.0,
            'view_count': int
        },
    }, {
        'url': 'https://daft.sex/watch/-156601359_456242791',
        'info_dict': {
            'id': '-156601359_456242791',
            'ext': 'mp4',
            'title': 'Skye Blue - Dinner And A Show',
            'description': 'Skye Blue - Dinner And A Show - Watch video Watch video in high quality',
            'upload_date': '20200916',
            'timestamp': 1600250735,
            'thumbnail': 'https://psv153-1.crazycloud.ru/videos/-156601359/456242791/thumb.jpg?extra=i3D32KaBbBFf9TqDRMAVmQ',
        },
        'skip': 'deleted / private'
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        title = self._html_search_meta('name', webpage, 'title')
        timestamp = unified_timestamp(self._html_search_meta('uploadDate', webpage, 'Upload Date', default=None))
        description = self._html_search_meta('description', webpage, 'Description', default=None)

        duration = parse_duration(self._search_regex(
            r'Duration: ((?:[0-9]{2}:){0,2}[0-9]{2})',
            webpage, 'duration', fatal=False))
        views = parse_count(self._search_regex(
            r'Views: ([0-9 ]+)',
            webpage, 'views', fatal=False))

        player_hash = self._search_regex(
            r'DaxabPlayer\.Init\({[\s\S]*hash:\s*"([0-9a-zA-Z_\-]+)"[\s\S]*}',
            webpage, 'player hash')
        player_color = self._search_regex(
            r'DaxabPlayer\.Init\({[\s\S]*color:\s*"([0-9a-z]+)"[\s\S]*}',
            webpage, 'player color', fatal=False) or ''

        embed_page = self._download_webpage(
            'https://dxb.to/player/%s?color=%s' % (player_hash, player_color),
            video_id, headers={'Referer': url})
        video_params = self._parse_json(
            self._search_regex(
                r'window\.globParams\s*=\s*({[\S\s]+})\s*;\s*<\/script>',
                embed_page, 'video parameters'),
            video_id, transform_source=js_to_json)

        server_domain = 'https://%s' % compat_b64decode(video_params['server'][::-1]).decode('utf-8')

        cdn_files = traverse_obj(video_params, ('video', 'cdn_files')) or {}
        if cdn_files:
            formats = []
            for format_id, format_data in cdn_files.items():
                ext, height = format_id.split('_')
                formats.append({
                    'format_id': format_id,
                    'url': f'{server_domain}/videos/{video_id.replace("_", "/")}/{height}.mp4?extra={format_data.split(".")[-1]}',
                    'height': int_or_none(height),
                    'ext': ext,
                })

            return {
                'id': video_id,
                'title': title,
                'formats': formats,
                'description': description,
                'duration': duration,
                'thumbnail': try_get(video_params, lambda vi: 'https:' + compat_b64decode(vi['video']['thumb']).decode('utf-8')),
                'timestamp': timestamp,
                'view_count': views,
                'age_limit': 18,
            }

        items = self._download_json(
            f'{server_domain}/method/video.get/{video_id}', video_id,
            headers={'Referer': url}, query={
                'token': video_params['video']['access_token'],
                'videos': video_id,
                'ckey': video_params['c_key'],
                'credentials': video_params['video']['credentials'],
            })['response']['items']

        if not items:
            raise ExtractorError('Video is not available', video_id=video_id, expected=True)

        item = items[0]
        formats = []
        for f_id, f_url in item.get('files', {}).items():
            if f_id == 'external':
                return self.url_result(f_url)
            ext, height = f_id.split('_')
            height_extra_key = traverse_obj(video_params, ('video', 'partial', 'quality', height))
            if height_extra_key:
                formats.append({
                    'format_id': f'{height}p',
                    'url': f'{server_domain}/{f_url[8:]}&videos={video_id}&extra_key={height_extra_key}',
                    'height': int_or_none(height),
                    'ext': ext,
                })

        thumbnails = []
        for k, v in item.items():
            if k.startswith('photo_') and v:
                width = k.replace('photo_', '')
                thumbnails.append({
                    'id': width,
                    'url': v,
                    'width': int_or_none(width),
                })

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'comment_count': int_or_none(item.get('comments')),
            'description': description,
            'duration': duration,
            'thumbnails': thumbnails,
            'timestamp': timestamp,
            'view_count': views,
            'age_limit': 18,
        }
