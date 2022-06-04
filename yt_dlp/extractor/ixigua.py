from .common import InfoExtractor
from ..utils import (
    get_element_by_id,
    int_or_none,
    js_to_json,
    traverse_obj,
    ExtractorError,
)
import base64
from urllib.parse import parse_qs

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
    
    def _get_video_format(self, video_type, video_type_json):
        # select video data based on video type
        video_type_based_format = {}
        if video_type.startswith('dash'):
            video_data = traverse_obj(video_type_json, ('dynamic_video', 'dynamic_video_list'))
            video_type_based_format = {
                'format_note': 'DASH video',
            }
        else:
            video_data = video_type_json.get('video_list')
            
        _single_video_format = list()
        for video in video_data:
            # print(video)
            if isinstance(video, str) and video.startswith('video_'):
                video = video_data.get(video)
            video_url = base64.b64decode(video.get('main_url')).decode() 
            base_format = {
                'url': video_url,
                'width': int_or_none(video.get('vwidth')),
                'height': int_or_none(video.get('vheight')),
                'fps': int_or_none(video.get('fps')),
                'vcodec': video.get('codec_type'),
                'format_id' : str(video.get('quality_type')),
                'ext' : 'mp4' if parse_qs(video_url).get('mime_type')[0] == 'video_mp4' else None,
                **video_type_based_format
            }
            
            _single_video_format.append(base_format)
        return _single_video_format
    
    def _real_extract(self, url):
        video_id = self._match_id(url)
        # need to pass cookie (at least contain __ac_nonce and ttwid)
        webpage = self._download_webpage(url, video_id)

        json_data = self._get_json_data(webpage, video_id)
        video_info = traverse_obj(json_data, ('anyVideo', 'gidInformation', 'packerData', 'video', 'videoResource'))
         
        format_ = list()
        for video_type, json_ in video_info.items():
            if not isinstance(json_, dict):
                continue
            video_format = self._get_video_format(video_type, json_)
            format_.extend(video_format)
        
        self._sort_formats(format_)
        return {
            'id': video_id,
            'title': traverse_obj(json_data, ('anyVideo', 'gidInformation', 'packerData', 'video', 'title')),
            'description': traverse_obj(json_data, ('anyVideo', 'gidInformation', 'packerData', 'video', 'video_abstract')),
            'formats': format_,
            'like_count': traverse_obj(json_data, ('anyVideo', 'gidInformation', 'packerData', 'video', 'video_like_count')),
            'duration' : int_or_none(traverse_obj(json_data, ('anyVideo', 'gidInformation', 'packerData', 'video', 'video_duration'))),
            'tag' : traverse_obj(json_data, ('anyVideo', 'gidInformation', 'packerData', 'video', 'tag')),
            
        }
