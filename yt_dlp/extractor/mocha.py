from urllib.parse import quote 
from .common import InfoExtractor
from ..utils import (
    str_or_none,
    traverse_obj,
)

class MochaVideoIE(InfoExtractor):
    _VALID_URL =r'http://video.mocha.com.vn/(?P<video_slug>\w+)'
    _TESTS = [{
        'url': 'http://video.mocha.com.vn/chuyen-meo-gia-su-tu-thong-diep-cuoc-song-v18694039',
        'info_dict': {
            'id': '18694039',
            'title': 'Chuyện mèo giả sư tử | Thông điệp cuộc sống'
        }
    }]
    
    def _real_extract(self, url):
        video_slug = self._match_valid_url(url).group('video_slug')
        json_data = self._download_json(
            'http://apivideo.mocha.com.vn:8081/onMediaBackendBiz/mochavideo/getVideoDetail',
            video_slug, query = {'url' : f'{url}', 'token': ''})
        videoDetails = json_data['data']['videoDetail'] 
        video_url = videoDetails.get('list_resolution') or videoDetails.get('original_path')
        formats = []
        if isinstance(video_url, str):
            data = {
                'url': video_url,
            }
            formats.append(data)
        else :
            for video in video_url:
                vid_url = self._extract_m3u8_formats(video['video_path'], video_slug)
                #print(vid_url)
                formats.extend(vid_url)
        
        self._sort_formats(formats)
        
        return {
            'id': str(videoDetails['id']),
            'title': traverse_obj(json_data, ('data', 'videoDetails', 'name')),
            'formats': formats,
        }