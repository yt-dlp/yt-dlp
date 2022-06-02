from .common import InfoExtractor
from ..utils import (
    get_element_by_id,
    js_to_json,
    traverse_obj,
    ExtractorError,
)
import base64

class IxiguaIE(InfoExtractor):
    _VALID_URL = r'https?://www\.ixigua\.com\/(?P<id>[0-9]+)'
    
    _TEST = {
        'url' : 'https://www.ixigua.com/6996881461559165471',
        'info_dict':{
            'id' : 'v0d004g10000c4d1t7jc77ub4g3o88b0',
            'ext' : 'mp4',
        }
    }
    
    def _get_json_data(self, webpage, video_id):
        js_data = get_element_by_id("SSR_HYDRATED_DATA", webpage) 
        #json_string = js_to_json(str(js_data), "window._SSR_HYDRATED_DATA")
        print(js_data)
        
        if not js_data:
            raise ExtractorError(f'{self.IE_NAME} said: json data got {js_data}',)
        
        json_string = js_to_json(str(js_data))
        #print(json_string)
        return self._parse_json(json_string, video_id)
    
    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        json_data = self._get_json_data(webpage, video_id)
        
        #print(json_data)
        
        video_info = traverse_obj(json_data, ('anyVideo','packerData', 'video', 'videoresource'))
        # only get normals video as dash video returned http 403 error
        normals_video = traverse_obj(video_info, ('normal','video_list'))
        thumbnail_url = traverse_obj(json_data, ('anyVideo','packerData', 'video', 'poster_url'))
        
     
        format_ = list()
        for _, video in normals_video.items():
            video_format = {
                'url' : base64.b64decode(video.get('main_utl')).decode(),
                'width' : video.get('vwidth'),
                'height' : video.get('vheight'),
                'fps' : video.get('fps'),
                'vcodec' : video.get('codec_type'),
            }
            format_.append(video_format)
        
        return {
            'id' : traverse_obj(json_data, ('anyVideo','packerData', 'video', 'vid')),
            'title' : traverse_obj(json_data, ('anyVideo','packerData', 'video', 'title')),
            'thumbnail' : traverse_obj(json_data, ('anyVideo','packerData', 'video', 'poster_url')),
            'description' : traverse_obj(json_data, ('anyVideo','packerData', 'video', 'video_abstract')),
        }