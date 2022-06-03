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
            'ext': 'unknown_video',
            'title': '盲目涉水风险大，亲身示范高水位行车注意事项',
            'description': '本期《懂车帝评测》，我们将尝试验证一个夏日大家可能会遇到的关键性问题：如果突发暴雨，我们不得不涉水行车，如何做才能更好保障生命安全。',
            'tag' : 'video_car'
            # thumbnail url keep changing
        }
    }

    def _get_json_data(self, webpage, video_id):
        js_data = get_element_by_id('SSR_HYDRATED_DATA', webpage)
        if not js_data:
            raise ExtractorError(f'Failed to get SSR_HYDRATED_DATA',)

        return self._parse_json(js_data.replace('window._SSR_HYDRATED_DATA=', ''), video_id, transform_source=js_to_json)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        # need to pass cookie (at least contain __ac_nonce and ttwid)
        webpage = self._download_webpage(url, video_id)

        json_data = self._get_json_data(webpage, video_id)
        video_info = traverse_obj(json_data, ('anyVideo', 'gidInformation', 'packerData', 'video', 'videoResource'))
        # only get normals video as dash video returned http 403 error
        normals_video = traverse_obj(video_info, ('normal', 'video_list'))
        # thumbnail_url = traverse_obj(json_data, ('anyVideo','gidInformation','packerData', 'video', 'poster_url'))
        format_ = list()
        for _, video in normals_video.items():
            video_format = {
                'url': base64.b64decode(video.get('main_url')).decode(),
                'width': int_or_none(video.get('vwidth')),
                'height': int_or_none(video.get('vheight')),
                'fps': int_or_none(video.get('fps')),
                'vcodec': video.get('codec_type'),
            }
            format_.append(video_format)
        
        self._sort_formats(format_)
        return {
            'id': video_id,
            'title': traverse_obj(json_data, ('anyVideo', 'gidInformation', 'packerData', 'video', 'title')),
            'description': traverse_obj(json_data, ('anyVideo', 'gidInformation', 'packerData', 'video', 'video_abstract')),
            'formats': format_,
            'tag' : traverse_obj(json_data, ('anyVideo', 'gidInformation', 'packerData', 'video', 'tag')),
        }
