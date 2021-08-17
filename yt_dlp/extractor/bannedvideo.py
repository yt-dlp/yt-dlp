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

    _GRAPHQL_GETVIDEO_QUERY = '''
query GetVideo($id: String!) {
    getVideo(id: $id) {
        ...DisplayVideoFields
        streamUrl
        directUrl
        unlisted
        live
        tags {
            _id
            name
            __typename
        }
        sale {
            _id
            text
            __typename
        }
        __typename
    }
}
fragment DisplayVideoFields on Video {
    _id
    title
    summary
    playCount
    largeImage
    embedUrl
    published
    videoDuration
    channel {
        _id
        title
        avatar
        __typename
    }
    createdAt
    __typename
}'''
    _GRAPHQL_GETCOMMENTS_QUERY = '''
query GetVideoComments($id: String!, $limit: Float, $offset: Float) {
    getVideoComments(id: $id, limit: $limit, offset: $offset) {
        ...VideoComment
        replyCount
        __typename
    }
}
fragment VideoComment on Comment {
    _id
    content
    liked
    user {
        _id
        username
        __typename
    }
    voteCount {
        positive
        __typename
    }
    linkedUser {
        _id
        username
        __typename
    }
    createdAt
    __typename
}'''
    _GRAPHQL_GETCOMMENTSREPLIES_QUERY = '''
query GetCommentReplies($id: String!, $limit: Float, $offset: Float) {
    getCommentReplies(id: $id, limit: $limit, offset: $offset) {
        ...VideoComment
        replyTo {
            _id
            __typename
        }
        __typename
    }
}
fragment VideoComment on Comment {
    _id
    content
    liked
    user {
        _id
        username
        __typename
    }
    voteCount {
        positive
        __typename
    }
    linkedUser {
        _id
        username
        __typename
    }
    createdAt
    __typename
}'''

    _GRAPHQL_QUERIES = {
        'GetVideo': _GRAPHQL_GETVIDEO_QUERY,
        'GetVideoComments': _GRAPHQL_GETCOMMENTS_QUERY,
        'GetCommentReplies': _GRAPHQL_GETCOMMENTSREPLIES_QUERY,
    }

    def _call_api(self, video_id, id, operation, note):
        field = operation[0].lower() + operation[1:]
        return try_get(self._download_json(
            'https://api.infowarsmedia.com/graphql', video_id, note=note,
            headers={
                'Content-Type': 'application/json; charset=utf-8'
            }, data=json.dumps({
                'variables': {'id': id},
                'operationName': operation,
                'query': self._GRAPHQL_QUERIES[operation]
            }).encode('utf8')), lambda x: x['data'][field])

    def _extract_comments(self, video_id):
        video_comments = self._call_api(video_id, video_id, 'GetVideoComments', 'Downloading comments')
        comments = []
        for comment in video_comments:
            comment_id = comment.get('_id')
            comments.append({
                'id': comment_id,
                'text': comment.get('content'),
                'author': comment.get('user').get('username'),
                'author_id': comment.get('user').get('_id'),
                'timestamp': unified_timestamp(comment.get('createdAt')),
                'parent': 'root'
            })
            if comment.get('replyCount') > 0:
                replies = self._call_api(
                        video_id, comment_id, 'GetCommentReplies',
                        f'Downloading replies for comment {comment_id}')
                for reply in replies:
                    comments.append({
                        'id': reply.get('_id'),
                        'text': reply.get('content'),
                        'author': reply.get('user').get('username'),
                        'author_id': reply.get('user').get('_id'),
                        'timestamp': unified_timestamp(reply.get('createdAt')),
                        'parent': comment.get('_id')
                    })

        return {
            'comments': comments,
            'comment_count': len(comments),
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_info = self._call_api(video_id, video_id, 'GetVideo', 'Downloading video metadata')

        is_live = video_info.get('live')
        if is_live:
            formats = self._extract_m3u8_formats(
                video_info.get('streamUrl'), video_id, 'mp4',
                entry_protocol='m3u8_native', m3u8_id='hls', live=True)
        else:
            formats = [{
                'url': video_info.get('directUrl'),
                'ext': 'mp4',
            }]

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': video_info.get('title')[:-1],
            'formats': formats,
            'description': video_info.get('summary'),
            'channel': video_info.get('channel').get('title'),
            'channel_id': video_info.get('channel').get('_id'),
            'view_count': int_or_none(video_info.get('playCount')),
            'thumbnail': url_or_none(video_info.get('largeImage')),
            'duration': float_or_none(video_info.get('videoDuration'), scale=1000),
            'timestamp': unified_timestamp(video_info.get('createdAt')),
            'tags': [tag.get('name') for tag in video_info.get('tags')],
            'is_live': is_live,
            '__post_extractor': ((lambda: self._extract_comments(video_id))
                                 if self.get_param('getcomments') else None)
        }
