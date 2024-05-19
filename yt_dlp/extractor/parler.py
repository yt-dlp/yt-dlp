import functools

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
    _VALID_URL = r'https?://parler\.com/feed/(?P<id>[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12})'
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
            'url': 'https://parler.com/feed/f23b85c1-6558-470f-b9ff-02c145f28da5',
            'md5': 'eaba1ff4a10fe281f5ce74e930ab2cb4',
            'info_dict': {
                'id': 'r5vkSaz8PxQ',
                'ext': 'mp4',
                'live_status': 'not_live',
                'comment_count': int,
                'duration': 1267,
                'like_count': int,
                'channel_follower_count': int,
                'channel_id': 'UCox6YeMSY1PQInbCtTaZj_w',
                'upload_date': '20220716',
                'thumbnail': 'https://i.ytimg.com/vi/r5vkSaz8PxQ/maxresdefault.jpg',
                'tags': 'count:17',
                'availability': 'public',
                'categories': ['Entertainment'],
                'playable_in_embed': True,
                'channel': 'Who Knows What! With Mahesh & Friends',
                'title': 'Tom MacDonald Names Reaction',
                'uploader': 'Who Knows What! With Mahesh & Friends',
                'uploader_id': '@maheshchookolingo',
                'age_limit': 0,
                'description': 'md5:33c21f0d35ae6dc2edf3007d6696baea',
                'channel_url': 'https://www.youtube.com/channel/UCox6YeMSY1PQInbCtTaZj_w',
                'view_count': int,
                'uploader_url': 'http://www.youtube.com/@maheshchookolingo',
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._download_json(f'https://api.parler.com/v0/public/parleys/{video_id}',
                                   video_id)['data']
        if data.get('link'):
            return self.url_result(data['link'], YoutubeIE)

        return {
            'id': video_id,
            'title': strip_or_none(data.get('title')) or '',
            **traverse_obj(data, {
                'url': ('video', 'videoSrc'),
                'thumbnail': ('video', 'thumbnailUrl'),
                'description': ('body', {clean_html}),
                'timestamp': ('date_created', {unified_timestamp}),
                'uploader': ('user', 'name', {strip_or_none}),
                'uploader_id': ('user', 'username', {str}),
                'uploader_url': ('user', 'username', {functools.partial(urljoin, 'https://parler.com/')}),
                'view_count': ('views', {int_or_none}),
                'comment_count': ('total_comments', {int_or_none}),
                'repost_count': ('echos', {int_or_none}),
            })
        }
