from .common import InfoExtractor
from ..utils import (
    get_element_by_id,
    int_or_none,
    js_to_json,
    traverse_obj,
    ExtractorError,
)
import base64


class IxiguaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:\w+\.)?ixigua\.com/(?:video/)?(?P<id>[0-9]+).+'
    _TEST = {
        'url': 'https://www.ixigua.com/6996881461559165471',
        'info_dict': {
            'id': '6996881461559165471',
            'ext': 'mp4',
            'title': '盲目涉水风险大，亲身示范高水位行车注意事项',
            'description': '本期《懂车帝评测》，我们将尝试验证一个夏日大家可能会遇到的关键性问题：如果突发暴雨，我们不得不涉水行车，如何做才能更好保障生命安全。',
            'tag': 'video_car',
            'like_count': int,
            'dislike_count': int,
            'view_count': int,
            'uploader': '懂车帝原创',
            'uploader_id': '6480145787',
            'thumbnail': r're:^https?://.*\.(avif|webp)(?:\?.+)',  # still not sure for regex
            'timestamp': 1629088414,
        },
        'skip': 'This Extractor need cookies',
    }

    def _get_json_data(self, webpage, video_id):
        js_data = get_element_by_id('SSR_HYDRATED_DATA', webpage)
        if not js_data:
            raise ExtractorError('Failed to get SSR_HYDRATED_DATA',)

        return self._parse_json(js_data.replace('window._SSR_HYDRATED_DATA=', ''), video_id, transform_source=js_to_json)

    def _get_media_format(self, media_type, media_json):
        media_specific_format = {}
        media_data = []
        if media_type == "dash_video":
            media_data = traverse_obj(media_json, ('dynamic_video', 'dynamic_video_list'))
            media_specific_format = {
                'format_note': 'DASH',
                'acodec': 'none',
            }
        elif media_type == "dash_audio":
            media_data = traverse_obj(media_json, ('dynamic_video', 'dynamic_audio_list'))
            media_specific_format = {
                'format_note': 'DASH',
                'vcodec': 'none',
                'ext': 'mp4a',
            }
        elif media_type == "normal":
            for media in media_json.get('video_list'):
                media_data.append(traverse_obj(media_json, ('video_list', media)))

        return self._get_formats(media_data, media_specific_format)

    def _get_formats(self, media_json, media_specific_format):
        _single_video_format = []
        # This download video only-DASH and mp4 format
        for media in media_json:
            base_format = {
                'url': base64.b64decode(media.get('main_url')).decode(),
                'width': int_or_none(media.get('vwidth')),
                'height': int_or_none(media.get('vheight')),
                'fps': int_or_none(media.get('fps')),
                'vcodec': media.get('codec_type'),
                'format_id': str(media.get('quality_type')),
                'filesize': int_or_none(media.get('size')),
                'ext': 'mp4',
                **media_specific_format
            }
            _single_video_format.append(base_format)
        return _single_video_format

    def _media_selector(self, json_data):
        formats_ = []
        for media in json_data:
            media_data = json_data.get(media)
            if not isinstance(media_data, dict):
                continue
            if media.startswith('dash'):
                video_format = self._get_media_format('dash_video', media_data)
                audio_format = self._get_media_format('dash_audio', media_data)
                formats_.extend(audio_format)
                formats_.extend(video_format)
            else:
                video_format = self._get_media_format('normal', media_data)
                formats_.extend(video_format)

        return formats_

    def _real_extract(self, url):
        video_id = self._match_id(url)
        # need to pass cookie (at least contain __ac_nonce and ttwid)
        webpage = self._download_webpage(url, video_id)
        json_data = self._get_json_data(webpage, video_id)
        video_info = traverse_obj(json_data, ('anyVideo', 'gidInformation', 'packerData', 'video', 'videoResource'))

        format_ = self._media_selector(video_info)
        self._sort_formats(format_)
        return {
            'id': video_id,
            'title': traverse_obj(json_data, ('anyVideo', 'gidInformation', 'packerData', 'video', 'title')),
            'description': traverse_obj(json_data, ('anyVideo', 'gidInformation', 'packerData', 'video', 'video_abstract')),
            'formats': format_,
            'like_count': traverse_obj(json_data, ('anyVideo', 'gidInformation', 'packerData', 'video', 'video_like_count')),
            'duration': int_or_none(traverse_obj(json_data, ('anyVideo', 'gidInformation', 'packerData', 'video', 'video_duration'))),
            'tag': traverse_obj(json_data, ('anyVideo', 'gidInformation', 'packerData', 'video', 'tag')),
            'uploader_id': traverse_obj(json_data, ('anyVideo', 'gidInformation', 'packerData', 'video', 'user_info', 'user_id')),
            'uploader': traverse_obj(json_data, ('anyVideo', 'gidInformation', 'packerData', 'video', 'user_info', 'name')),
            'view_count': traverse_obj(json_data, ('anyVideo', 'gidInformation', 'packerData', 'video', 'video_watch_count')),
            'dislike_count': traverse_obj(json_data, ('anyVideo', 'gidInformation', 'packerData', 'video', 'video_unlike_count')),
            'timestamp': traverse_obj(json_data, ('anyVideo', 'gidInformation', 'packerData', 'video', 'video_publish_time')),
        }
