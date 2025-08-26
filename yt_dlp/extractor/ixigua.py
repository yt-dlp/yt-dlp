import base64

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    get_element_by_id,
    int_or_none,
    js_to_json,
    str_or_none,
    traverse_obj,
)


class IxiguaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:\w+\.)?ixigua\.com/(?:video/)?(?P<id>\d+).+'
    _TESTS = [{
        'url': 'https://www.ixigua.com/6996881461559165471',
        'info_dict': {
            'id': '6996881461559165471',
            'ext': 'mp4',
            'title': '盲目涉水风险大，亲身示范高水位行车注意事项',
            'description': 'md5:8c82f46186299add4a1c455430740229',
            'tags': ['video_car'],
            'like_count': int,
            'dislike_count': int,
            'view_count': int,
            'uploader': '懂车帝原创',
            'uploader_id': '6480145787',
            'thumbnail': r're:^https?://.+\.(avif|webp)',
            'timestamp': 1629088414,
            'duration': 1030,
        },
    }]

    def _get_json_data(self, webpage, video_id):
        js_data = get_element_by_id('SSR_HYDRATED_DATA', webpage)
        if not js_data:
            if self._cookies_passed:
                raise ExtractorError('Failed to get SSR_HYDRATED_DATA')
            raise ExtractorError('Cookies (not necessarily logged in) are needed', expected=True)

        return self._parse_json(
            js_data.replace('window._SSR_HYDRATED_DATA=', ''), video_id, transform_source=js_to_json)

    def _media_selector(self, json_data):
        for path, override in (
            (('video_list', ), {}),
            (('dynamic_video', 'dynamic_video_list'), {'acodec': 'none'}),
            (('dynamic_video', 'dynamic_audio_list'), {'vcodec': 'none', 'ext': 'm4a'}),
        ):
            for media in traverse_obj(json_data, (..., *path, lambda _, v: v['main_url'])):
                yield {
                    'url': base64.b64decode(media['main_url']).decode(),
                    'width': int_or_none(media.get('vwidth')),
                    'height': int_or_none(media.get('vheight')),
                    'fps': int_or_none(media.get('fps')),
                    'vcodec': media.get('codec_type'),
                    'format_id': str_or_none(media.get('quality_type')),
                    'filesize': int_or_none(media.get('size')),
                    'ext': 'mp4',
                    **override,
                }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        json_data = self._get_json_data(webpage, video_id)['anyVideo']['gidInformation']['packerData']['video']

        formats = list(self._media_selector(json_data.get('videoResource')))
        return {
            'id': video_id,
            'title': json_data.get('title'),
            'description': json_data.get('video_abstract'),
            'formats': formats,
            'like_count': json_data.get('video_like_count'),
            'duration': int_or_none(json_data.get('duration')),
            'tags': [json_data.get('tag')],
            'uploader_id': traverse_obj(json_data, ('user_info', 'user_id')),
            'uploader': traverse_obj(json_data, ('user_info', 'name')),
            'view_count': json_data.get('video_watch_count'),
            'dislike_count': json_data.get('video_unlike_count'),
            'timestamp': int_or_none(json_data.get('video_publish_time')),
        }
