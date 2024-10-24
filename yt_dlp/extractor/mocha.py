from .common import InfoExtractor
from ..utils import int_or_none, traverse_obj


class MochaVideoIE(InfoExtractor):
    _VALID_URL = r'https?://video\.mocha\.com\.vn/(?P<video_slug>[\w-]+)'
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
            'categories': ['Kids'],
        },
    }]

    def _real_extract(self, url):
        video_slug = self._match_valid_url(url).group('video_slug')
        json_data = self._download_json(
            'http://apivideo.mocha.com.vn:8081/onMediaBackendBiz/mochavideo/getVideoDetail',
            video_slug, query={'url': url, 'token': ''})['data']['videoDetail']
        video_id = str(json_data['id'])
        video_urls = (json_data.get('list_resolution') or []) + [json_data.get('original_path')]

        formats, subtitles = [], {}
        for video in video_urls:
            if isinstance(video, str):
                formats.extend([{'url': video, 'ext': 'mp4'}])
            else:
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    video.get('video_path'), video_id, ext='mp4')
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)

        return {
            'id': video_id,
            'display_id': json_data.get('slug') or video_slug,
            'title': json_data.get('name'),
            'formats': formats,
            'subtitles': subtitles,
            'description': json_data.get('description'),
            'duration': json_data.get('durationS'),
            'view_count': json_data.get('total_view'),
            'like_count': json_data.get('total_like'),
            'dislike_count': json_data.get('total_unlike'),
            'thumbnail': json_data.get('image_path_thumb'),
            'timestamp': int_or_none(json_data.get('publish_time'), scale=1000),
            'is_live': json_data.get('isLive'),
            'channel': traverse_obj(json_data, ('channels', '0', 'name')),
            'channel_id': traverse_obj(json_data, ('channels', '0', 'id')),
            'channel_follower_count': traverse_obj(json_data, ('channels', '0', 'numfollow')),
            'categories': traverse_obj(json_data, ('categories', ..., 'categoryname')),
            'comment_count': json_data.get('total_comment'),
        }
