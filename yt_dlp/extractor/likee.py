import json

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    js_to_json,
    parse_iso8601,
    str_or_none,
    traverse_obj,
)


class LikeeIE(InfoExtractor):
    IE_NAME = 'likee'
    _VALID_URL = r'(?x)https?://(www\.)?likee\.video/(?:(?P<channel_name>[^/]+)/video/|v/)(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://likee.video/@huynh_hong_quan_/video/7093444807096327263',
        'info_dict': {
            'id': '7093444807096327263',
            'ext': 'mp4',
            'title': '🤴🤴🤴',
            'description': 'md5:9a7ebe816f0e78722ee5ed76f75983b4',
            'thumbnail': r're:^https?://.+\.jpg',
            'uploader': 'Huỳnh Hồng Qu&acirc;n ',
            'artist': 'Huỳnh Hồng Qu&acirc;n ',
            'timestamp': 1651571320,
            'upload_date': '20220503',
            'view_count': int,
            'uploader_id': 'huynh_hong_quan_',
            'duration': 12374,
            'comment_count': int,
            'like_count': int,
        },
    }, {
        'url': 'https://likee.video/@649222262/video/7093167848050058862',
        'info_dict': {
            'id': '7093167848050058862',
            'ext': 'mp4',
            'title': 'likee video #7093167848050058862',
            'description': 'md5:3f971c8c6ee8a216f2b1a9094c5de99f',
            'thumbnail': r're:^https?://.+\.jpg',
            'comment_count': int,
            'like_count': int,
            'uploader': 'Vương Phước Nhi',
            'timestamp': 1651506835,
            'upload_date': '20220502',
            'duration': 60024,
            'artist': 'Vương Phước Nhi',
            'uploader_id': '649222262',
            'view_count': int,
        },
    }, {
        'url': 'https://likee.video/@fernanda_rivasg/video/6932224568407629502',
        'info_dict': {
            'id': '6932224568407629502',
            'ext': 'mp4',
            'title': 'Un trend viejito🔥 #LIKEE #Ferlovers #trend ',
            'description': 'md5:c42b903a72a99d6d8b73e3d1126fbcef',
            'thumbnail': r're:^https?://.+\.jpg',
            'comment_count': int,
            'duration': 9684,
            'uploader_id': 'fernanda_rivasg',
            'view_count': int,
            'artist': 'La Cami La✨',
            'like_count': int,
            'uploader': 'Fernanda Rivas🎶',
            'timestamp': 1614034308,
            'upload_date': '20210222',
        },
    }, {
        'url': 'https://likee.video/v/k6QcOp',
        'info_dict': {
            'id': 'k6QcOp',
            'ext': 'mp4',
            'title': '#AguaChallenge t&uacute; ya lo intentaste?😱🤩',
            'description': 'md5:b0cc462689d4ff2b624daa4dba7640d9',
            'thumbnail': r're:^https?://.+\.jpg',
            'comment_count': int,
            'duration': 18014,
            'view_count': int,
            'timestamp': 1611694774,
            'like_count': int,
            'uploader': 'Fernanda Rivas🎶',
            'uploader_id': 'fernanda_rivasg',
            'artist': 'ʟᴇʀɪᴋ_ᴜɴɪᴄᴏʀɴ♡︎',
            'upload_date': '20210126',
        },
    }, {
        'url': 'https://www.likee.video/@649222262/video/7093167848050058862',
        'only_matching': True,
    }, {
        'url': 'https://www.likee.video/v/k6QcOp',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        info = self._parse_json(
            self._search_regex(r'window\.data\s=\s({.+?});', webpage, 'video info'),
            video_id, transform_source=js_to_json)
        video_url = traverse_obj(info, 'video_url', ('originVideoInfo', 'video_url'))
        if not video_url:
            self.raise_no_formats('Video was deleted', expected=True)
        formats = [{
            'format_id': 'mp4-with-watermark',
            'url': video_url,
            'height': info.get('video_height'),
            'width': info.get('video_width'),
        }, {
            'format_id': 'mp4-without-watermark',
            'url': video_url.replace('_4', ''),
            'height': info.get('video_height'),
            'width': info.get('video_width'),
            'quality': 1,
        }]
        return {
            'id': video_id,
            'title': info.get('msgText'),
            'description': info.get('share_desc'),
            'view_count': int_or_none(info.get('video_count')),
            'like_count': int_or_none(info.get('likeCount')),
            'comment_count': int_or_none(info.get('comment_count')),
            'uploader': str_or_none(info.get('nick_name')),
            'uploader_id': str_or_none(info.get('likeeId')),
            'artist': str_or_none(traverse_obj(info, ('sound', 'owner_name'))),
            'timestamp': parse_iso8601(info.get('uploadDate')),
            'thumbnail': info.get('coverUrl'),
            'duration': int_or_none(traverse_obj(info, ('option_data', 'dur'))),
            'formats': formats,
        }


class LikeeUserIE(InfoExtractor):
    IE_NAME = 'likee:user'
    _VALID_URL = r'https?://(www\.)?likee\.video/(?P<id>[^/]+)/?$'
    _TESTS = [{
        'url': 'https://likee.video/@fernanda_rivasg',
        'info_dict': {
            'id': '925638334',
            'title': 'fernanda_rivasg',
        },
        'playlist_mincount': 500,
    }, {
        'url': 'https://likee.video/@may_hmoob',
        'info_dict': {
            'id': '2943949041',
            'title': 'may_hmoob',
        },
        'playlist_mincount': 80,
    }]
    _PAGE_SIZE = 50
    _API_GET_USER_VIDEO = 'https://api.like-video.com/likee-activity-flow-micro/videoApi/getUserVideo'

    def _entries(self, user_name, user_id):
        last_post_id = ''
        while True:
            user_videos = self._download_json(
                self._API_GET_USER_VIDEO, user_name,
                data=json.dumps({
                    'uid': user_id,
                    'count': self._PAGE_SIZE,
                    'lastPostId': last_post_id,
                    'tabType': 0,
                }).encode('utf-8'),
                headers={'content-type': 'application/json'},
                note=f'Get user info with lastPostId #{last_post_id}')
            items = traverse_obj(user_videos, ('data', 'videoList'))
            if not items:
                break
            for item in items:
                last_post_id = item['postId']
                yield self.url_result(f'https://likee.video/{user_name}/video/{last_post_id}')

    def _real_extract(self, url):
        user_name = self._match_id(url)
        webpage = self._download_webpage(url, user_name)
        info = self._parse_json(
            self._search_regex(r'window\.data\s*=\s*({.+?});', webpage, 'user info'),
            user_name, transform_source=js_to_json)
        user_id = traverse_obj(info, ('userinfo', 'uid'))
        return self.playlist_result(self._entries(user_name, user_id), user_id, traverse_obj(info, ('userinfo', 'user_name')))
