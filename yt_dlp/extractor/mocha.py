from .common import InfoExtractor
from ..utils import int_or_none, traverse_obj


class MochaVideoIE(InfoExtractor):
    _VALID_URL = r'https?://video.mocha.com.vn/(?P<video_slug>[\w-]+)'
    _TESTS = [{
        'url': 'http://video.mocha.com.vn/chuyen-meo-gia-su-tu-thong-diep-cuoc-song-v18694039',
        'info_dict': {
            'id': '18694039',
            'title': 'Chuyện mèo giả sư tử | Thông điệp cuộc sống',
            'ext': 'mp4',
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'display_id': 'chuyen-meo-gia-su-tu-thong-diep-cuoc-song',
            'thumbnail': 'http://mcvideomd1fr.keeng.net/playnow/images/20220505/ad0a055d-2f69-42ca-b888-4790041fe6bc_640x480.jpg',
            'description': '',
            'duration': 70,
            'timestamp': 1652254203,
            'upload_date': '20220511',
            'comment_count': int,
            'categories': ['Kids']
        }
    }]

    def _real_extract(self, url):
        video_slug = self._match_valid_url(url).group('video_slug')
        json_data = self._download_json(
            'http://apivideo.mocha.com.vn:8081/onMediaBackendBiz/mochavideo/getVideoDetail',
            video_slug, query={'url': f'{url}', 'token': ''})

        video_url = traverse_obj(json_data, ('data', 'videoDetail', ('list_resolution', 'original_path')))

        formats, subtitles = [], {}
        for video in video_url:
            if isinstance(video, str):
                formats.extend([{'url': video, 'ext': 'mp4'}])
            else:
                vid_url, subs = self._extract_m3u8_formats_and_subtitles(video[0]['video_path'], video_slug, ext='mp4')
                formats.extend(vid_url)
            self._merge_subtitles(subs, target=subtitles)

        self._sort_formats(formats)

        return {
            'id': str(json_data['data']['videoDetail']['id']),
            'display_id': traverse_obj(json_data, ('data', 'videoDetail', 'slug')),
            'title': traverse_obj(json_data, ('data', 'videoDetail', 'name')),
            'formats': formats,
            'subtitles': subtitles,
            'description': traverse_obj(json_data, ('data', 'videoDetail', 'description')),
            'duration': traverse_obj(json_data, ('data', 'videoDetail', 'durationS')),
            'view_count': traverse_obj(json_data, ('data', 'videoDetail', 'total_view')),
            'like_count': traverse_obj(json_data, ('data', 'videoDetail', 'total_like')),
            'dislike_count': traverse_obj(json_data, ('data', 'videoDetail', 'total_unlike')),
            'thumbnail': traverse_obj(json_data, ('data', 'videoDetail', 'image_path_thumb')),
            'timestamp': int_or_none(traverse_obj(json_data, ('data', 'videoDetail', 'publish_time')), scale=1000),
            'is_live': traverse_obj(json_data, ('data', 'videoDetail', 'isLive')),
            'channel': traverse_obj(json_data, ('data', 'videoDetail', 'channels', '0', 'name')),
            'channel_id': traverse_obj(json_data, ('data', 'videoDetail', 'channels', '0', 'id')),
            'channel_follower_count': traverse_obj(json_data, ('data', 'videoDetail', 'channels', '0', 'numfollow')),
            'categories': traverse_obj(json_data, ('data', 'videoDetail', 'categories', ..., 'categoryname')),
            'comment_count': traverse_obj(json_data, ('data', 'videoDetail', 'total_comment')),
        }
