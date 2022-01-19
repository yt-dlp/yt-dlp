from __future__ import unicode_literals

import json

from .common import InfoExtractor
from ..utils import (
    try_get,
    int_or_none,
    url_or_none,
    float_or_none,
    unified_timestamp,
)


class BannedVideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?banned\.video/watch\?id=(?P<id>[0-f]{24})'
    _TESTS = [{
        'url': 'https://banned.video/watch?id=5e7a859644e02200c6ef5f11',
        'md5': '14b6e81d41beaaee2215cd75c6ed56e4',
        'info_dict': {
            'id': '5e7a859644e02200c6ef5f11',
            'ext': 'mp4',
            'title': 'China Discovers Origin of Corona Virus: Issues Emergency Statement',
            'thumbnail': r're:^https?://(?:www\.)?assets\.infowarsmedia.com/images/',
            'description': 'md5:560d96f02abbebe6c6b78b47465f6b28',
            'upload_date': '20200324',
            'timestamp': 1585087895,
        }
    }]

    _GRAPHQL_GETMETADATA_QUERY = '''
query GetVideoAndComments($id: String!) {
    getVideo(id: $id) {
        streamUrl
        directUrl
        unlisted
        live
        tags {
            name
        }
        title
        summary
        playCount
        largeImage
        videoDuration
        channel {
            _id
            title
        }
        createdAt
    }
    getVideoComments(id: $id, limit: 999999, offset: 0) {
        _id
        content
        user {
            _id
            username
        }
        voteCount {
            positive
        }
        createdAt
        replyCount
    }
}'''

    _GRAPHQL_GETCOMMENTSREPLIES_QUERY = '''
query GetCommentReplies($id: String!) {
    getCommentReplies(id: $id, limit: 999999, offset: 0) {
        _id
        content
        user {
            _id
            username
        }
        voteCount {
            positive
        }
        createdAt
        replyCount
    }
}'''

    _GRAPHQL_QUERIES = {
        'GetVideoAndComments': _GRAPHQL_GETMETADATA_QUERY,
        'GetCommentReplies': _GRAPHQL_GETCOMMENTSREPLIES_QUERY,
    }

    def _call_api(self, video_id, id, operation, note):
        return self._download_json(
            'https://api.infowarsmedia.com/graphql', video_id, note=note,
            headers={
                'Content-Type': 'application/json; charset=utf-8'
            }, data=json.dumps({
                'variables': {'id': id},
                'operationName': operation,
                'query': self._GRAPHQL_QUERIES[operation]
            }).encode('utf8')).get('data')

    def _get_comments(self, video_id, comments, comment_data):
        yield from comments
        for comment in comment_data.copy():
            comment_id = comment.get('_id')
            if comment.get('replyCount') > 0:
                reply_json = self._call_api(
                    video_id, comment_id, 'GetCommentReplies',
                    f'Downloading replies for comment {comment_id}')
                for reply in reply_json.get('getCommentReplies'):
                    yield self._parse_comment(reply, comment_id)

    @staticmethod
    def _parse_comment(comment_data, parent):
        return {
            'id': comment_data.get('_id'),
            'text': comment_data.get('content'),
            'author': try_get(comment_data, lambda x: x['user']['username']),
            'author_id': try_get(comment_data, lambda x: x['user']['_id']),
            'timestamp': unified_timestamp(comment_data.get('createdAt')),
            'parent': parent,
            'like_count': try_get(comment_data, lambda x: x['voteCount']['positive']),
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_json = self._call_api(video_id, video_id, 'GetVideoAndComments', 'Downloading video metadata')
        video_info = video_json['getVideo']
        is_live = video_info.get('live')
        comments = [self._parse_comment(comment, 'root') for comment in video_json.get('getVideoComments')]

        formats = [{
            'format_id': 'direct',
            'quality': 1,
            'url': video_info.get('directUrl'),
            'ext': 'mp4',
        }] if url_or_none(video_info.get('directUrl')) else []
        if video_info.get('streamUrl'):
            formats.extend(self._extract_m3u8_formats(
                video_info.get('streamUrl'), video_id, 'mp4',
                entry_protocol='m3u8_native', m3u8_id='hls', live=True))
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': video_info.get('title')[:-1],
            'formats': formats,
            'is_live': is_live,
            'description': video_info.get('summary'),
            'channel': try_get(video_info, lambda x: x['channel']['title']),
            'channel_id': try_get(video_info, lambda x: x['channel']['_id']),
            'view_count': int_or_none(video_info.get('playCount')),
            'thumbnail': url_or_none(video_info.get('largeImage')),
            'duration': float_or_none(video_info.get('videoDuration')),
            'timestamp': unified_timestamp(video_info.get('createdAt')),
            'tags': [tag.get('name') for tag in video_info.get('tags')],
            'availability': self._availability(is_unlisted=video_info.get('unlisted')),
            'comments': comments,
            '__post_extractor': self.extract_comments(video_id, comments, video_json.get('getVideoComments'))
        }
