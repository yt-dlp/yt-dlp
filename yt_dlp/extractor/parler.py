from .common import InfoExtractor
from .youtube import YoutubeIE
from ..utils import (
    clean_html,
    format_field,
    int_or_none,
    strip_or_none,
    traverse_obj,
    unified_timestamp,
    urlencode_postdata,
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
                'timestamp': 1659744000,
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
            'https://parler.com/open-api/ParleyDetailEndpoint.php', video_id,
            data=urlencode_postdata({'uuid': video_id}))['data'][0]
        primary = data['primary']

        embed = self._parse_json(primary.get('V2LINKLONG') or '', video_id, fatal=False)
        if embed:
            return self.url_result(embed[0], YoutubeIE)

        return {
            'id': video_id,
            'url': traverse_obj(primary, ('video_data', 'videoSrc')),
            'thumbnail': traverse_obj(primary, ('video_data', 'thumbnailUrl')),
            'title': '',
            'description': strip_or_none(clean_html(primary.get('full_body'))) or None,
            'timestamp': unified_timestamp(primary.get('date_created')),
            'uploader': strip_or_none(primary.get('name')),
            'uploader_id': strip_or_none(primary.get('username')),
            'uploader_url': format_field(strip_or_none(primary.get('username')), None, 'https://parler.com/%s'),
            'view_count': int_or_none(primary.get('view_count')),
            'comment_count': int_or_none(traverse_obj(data, ('engagement', 'commentCount'))),
            'repost_count': int_or_none(traverse_obj(data, ('engagement', 'echoCount'))),
        }
