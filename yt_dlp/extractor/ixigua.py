from .common import InfoExtractor
from ..utils import (
    get_element_by_id,
    js_to_json,
    traverse_obj,
    ExtractorError,
)
import base64

class IxiguaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:\w+\.)?ixigua\.com/(?:video/)?(?P<id>[0-9]+).+'
    
    _TEST = {
        'url' : 'https://www.ixigua.com/6996881461559165471',
        'info_dict':{
            'id' : 'v0d004g10000c4d1t7jc77ub4g3o88b0',
            'ext' : 'unknown_video',
            
        }
    }
    
    HEADER = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.63 Safari/537.36 Edg/102.0.1245.30',
        'Cookie': '__ac_nonce=06299682f00c705b21766;ttwid=1|wF-euYewq9nEpSxYnKBF0oEl4sLgpXLtnLBqsOLADV8|1654217384|b12118e45bb2370b50f859623a80f5dd828588fb76258035861fc3266c0316c5',
        'Accept': 'application/json'
        
    }
    
    def _get_json_data(self, webpage, video_id):
        js_data = get_element_by_id("SSR_HYDRATED_DATA", webpage) 
        #json_string = js_to_json(str(js_data), "window._SSR_HYDRATED_DATA")
        #print(js_data)
        
        if not js_data:
            raise ExtractorError(f'{self.IE_NAME} said: json data got {js_data}',)
        
        js_data = js_data.replace("window._SSR_HYDRATED_DATA=","")
        #print(json_string)
        return self._parse_json(js_data, video_id, transform_source=js_to_json)
    
    def _real_extract(self, url):
        video_id = self._match_id(url)
        # need to pass cookie
        webpage = self._download_webpage(url, video_id, headers=self.HEADER)
        
        json_data = self._get_json_data(webpage, video_id)
        #print(json_data)
        
        video_info = traverse_obj(json_data, ('anyVideo','gidInformation','packerData', 'video', 'videoResource'))
        # only get normals video as dash video returned http 403 error
        normals_video = traverse_obj(video_info, ('normal','video_list'))
        thumbnail_url = traverse_obj(json_data, ('anyVideo','gidInformation','packerData', 'video', 'poster_url'))
        
     
        format_ = list()
        for _, video in normals_video.items():
            print(video)
            video_format = {
                'url' : base64.b64decode(video.get('main_url')).decode(),
                'width' : video.get('vwidth'),
                'height' : video.get('vheight'),
                'fps' : video.get('fps'),
                'vcodec' : video.get('codec_type'),
            }
            format_.append(video_format)
        
        return {
            'id' : traverse_obj(json_data, ('anyVideo','gidInformation','packerData', 'video', 'vid')),
            'title' : traverse_obj(json_data, ('anyVideo','gidInformation','packerData', 'video', 'title')),
            'thumbnail' : str(traverse_obj(json_data, ('anyVideo','gidInformation','packerData', 'video', 'poster_url'))),
            'description' : traverse_obj(json_data, ('anyVideo','gidInformation','packerData', 'video', 'video_abstract')),
            'formats' : format_,
        }