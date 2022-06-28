from urllib.parse import quote 
from .common import InfoExtractor
from ..utils import (
    str_or_none,
    traverse_obj,
)

class MochaVideoIE(InfoExtractor):
    _VALID_URL =r'https?://video.mocha.com.vn/(?P<video_slug>\w+)'
    _TESTS = [{
        'url': 'http://video.mocha.com.vn/chuyen-meo-gia-su-tu-thong-diep-cuoc-song-v18694039',
        'info_dict': {
            'id': '18694039',
            'title': 'Chuyện mèo giả sư tử | Thông điệp cuộc sống',
            'ext': 'mp4',
        }
    }]
    
    def _real_extract(self, url):
        video_slug = self._match_valid_url(url).group('video_slug')
        json_data = self._download_json(
            'http://apivideo.mocha.com.vn:8081/onMediaBackendBiz/mochavideo/getVideoDetail',
            video_slug, query = {'url' : f'{url}', 'token': ''})
             
        video_url = (traverse_obj(json_data, ('data', 'videoDetail', 'list_resolution')) or 
                    traverse_obj(json_data, ('data', 'videoDetail', 'original_path'))
                    )
        formats, subtitles = [], {}
        if isinstance(video_url, str):
            data = {
                'url': video_url,
            }
            formats.append(data)
        else :
            for video in video_url:
                vid_url, subs = self._extract_m3u8_formats_and_subtitles(video['video_path'], video_slug)
                # vid_ext = {'ext': 'mp4'}
                # vid_url.update(vid_ext)
                formats.extend(vid_url)
                self._merge_subtitles(subs, target=subtitles)
        
        self._sort_formats(formats)
        
        return {
            'id': str(json_data['data']['videoDetail']['id']),
            'title': traverse_obj(json_data, ('data', 'videoDetail', 'name')),
            'formats': formats,
            'subtitles': subtitles,
            'description': traverse_obj(json_data, ('data', 'videoDetail', 'description')),
            'duration': traverse_obj(json_data, ('data', 'videoDetail', 'durationS')),
            'view_count': traverse_obj(json_data, ('data', 'videoDetail', 'total_view')),
            'like_count': traverse_obj(json_data, ('data', 'videoDetail', 'total_like')),
            'dislike_count': traverse_obj(json_data, ('data', 'videoDetail', 'total_unlike')),
            'thumbnail': traverse_obj(json_data, ('data', 'videoDetail', 'image_path_thumb')),
            
        }