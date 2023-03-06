from .common import InfoExtractor
from .youtube import YoutubeIE
from ..utils import (
    clean_html,
    int_or_none,
    strip_or_none,
    traverse_obj,
    unified_timestamp,
    urljoin,
)


class ParlerIE(InfoExtractor):
    IE_DESC = 'Posts on parler.com'
    _VALID_URL = r'https://parler\.com/feed/(?P<id>[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12})'
    _TESTS = [
        {
            'url': 'https://parler.com/feed/df79fdba-07cc-48fe-b085-3293897520d7',
            'md5': '16e0f447bf186bb3cf64de5bbbf4d22d',
            'info_dict': {
                'id': 'df79fdba-07cc-48fe-b085-3293897520d7',
                'ext': 'mp4',
                'thumbnail': 'https://bl-images.parler.com/videos/6ce7cdf3-a27a-4d72-bf9c-d3e17ce39a66/thumbnail.jpeg',
                'title': 'Parler video #df79fdba-07cc-48fe-b085-3293897520d7',
                'description': 'md5:6f220bde2df4a97cbb89ac11f1fd8197',
                'timestamp': 1659785481,
                'upload_date': '20220806',
                'uploader': 'Tulsi Gabbard',
                'uploader_id': 'TulsiGabbard',
                'uploader_url': 'https://parler.com/TulsiGabbard',
                'view_count': int,
                'comment_count': int,
                'repost_count': int,
            },
        },
        {
            'url': 'https://parler.com/feed/a7406eb4-91e5-4793-b5e3-ade57a24e287',
            'md5': '11687e2f5bb353682cee338d181422ed',
            'info_dict': {
                'id': 'a7406eb4-91e5-4793-b5e3-ade57a24e287',
                'ext': 'mp4',
                'thumbnail': 'https://bl-images.parler.com/videos/317827a8-1e48-4cbc-981f-7dd17d4c1183/thumbnail.jpeg',
                'title': 'Parler video #a7406eb4-91e5-4793-b5e3-ade57a24e287',
                'description': 'This man should run for office',
                'timestamp': 1659657600,
                'upload_date': '20220805',
                'uploader': 'Benny Johnson',
                'uploader_id': 'BennyJohnson',
                'uploader_url': 'https://parler.com/BennyJohnson',
                'view_count': int,
                'comment_count': int,
                'repost_count': int,
            },
        },
        {
            'url': 'https://parler.com/feed/f23b85c1-6558-470f-b9ff-02c145f28da5',
            'md5': 'eaba1ff4a10fe281f5ce74e930ab2cb4',
            'info_dict': {
                'id': 'r5vkSaz8PxQ',
                'ext': 'mp4',
                'thumbnail': 'https://i.ytimg.com/vi_webp/r5vkSaz8PxQ/maxresdefault.webp',
                'title': 'Tom MacDonald Names Reaction',
                'description': 'md5:33c21f0d35ae6dc2edf3007d6696baea',
                'upload_date': '20220716',
                'duration': 1267,
                'uploader': 'Mahesh Chookolingo',
                'uploader_id': 'maheshchookolingo',
                'uploader_url': 'http://www.youtube.com/user/maheshchookolingo',
                'channel': 'Mahesh Chookolingo',
                'channel_id': 'UCox6YeMSY1PQInbCtTaZj_w',
                'channel_url': 'https://www.youtube.com/channel/UCox6YeMSY1PQInbCtTaZj_w',
                'categories': ['Entertainment'],
                'tags': list,
                'availability': 'public',
                'live_status': 'not_live',
                'view_count': int,
                'comment_count': int,
                'like_count': int,
                'channel_follower_count': int,
                'age_limit': 0,
                'playable_in_embed': True,
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._download_json(
            'https://api.parler.com/v0/public/parleys/%s' % video_id, video_id)['data']

        if data.get('link'):
            return self.url_result(data.get('link'), YoutubeIE)

        return {
            'id': video_id,
            **traverse_obj(data, {
                'url': ('video', 'videoSrc'),
                'thumbnail': ('video', 'thumbnailUrl'),
                'title': ('title', {strip_or_none}),
                'description': ('body', {clean_html}, {lambda x: x if x else None}),
                'timestamp': ('date_created', {unified_timestamp}),
                'uploader': ('user', 'name', {strip_or_none}),
                'uploader_id': ('user', 'username', {str}),
                'uploader_url': ('user', 'username', {lambda x: urljoin('https://parler.com/', x)}),
                'view_count': ('views', {int_or_none}),
                'comment_count': ('total_comments', {int_or_none}),
                'repost_count': ('echos', {int_or_none}),
            })
        }
