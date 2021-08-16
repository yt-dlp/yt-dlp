from __future__ import unicode_literals

import json

from .common import InfoExtractor

from ..utils import (
    try_get,
    int_or_none,
    url_or_none,
    float_or_none,
    unified_timestamp,
    unified_strdate,
)


class BannedVideoIE(InfoExtractor):
    _GRAPHQL_API = 'https://api.infowarsmedia.com/graphql'
    _GRAPHQL_HEADERS = {
        'Content-Type': 'application/json; charset=utf-8'
    }
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
    _VALID_URL = r'https?://(?:www\.)?banned\.video/watch\?id=(?P<id>[0-f]{24})'
    _TEST = {
        'url': 'https://banned.video/watch?id=5e7a859644e02200c6ef5f11',
        'md5': '14b6e81d41beaaee2215cd75c6ed56e4',
        'info_dict': {
            'id': '5e7a859644e02200c6ef5f11',
            'ext': 'mp4',
            'title': 'China Discovers Origin of Corona Virus: Issues Emergency Statement',
            'thumbnail': r're:^https?://(?:www\.)?assets\.infowarsmedia.com/images/',
            'description': 'The Chinese Communist Party Official Spokesperson At the Ministry of Truth Released Their Statement Exclusively To Alex Jones and Infowars.com',
            'upload_date': '20200324',
            'timestamp': 1585087895,
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_info = try_get(
            self._download_json(
                self._GRAPHQL_API,
                video_id,
                headers=self._GRAPHQL_HEADERS,
                data=json.dumps({
                    'variables': {
                        'id': video_id
                    },
                    'operationName': 'GetVideo',
                    'query': self._GRAPHQL_GETVIDEO_QUERY
                }).encode('utf8')),
            lambda x: x['data']['getVideo'])
        video_comments = try_get(
            self._download_json(
                self._GRAPHQL_API,
                video_id,
                headers=self._GRAPHQL_HEADERS,
                data=json.dumps({
                    'variables': {
                        'id': video_id
                    },
                    'operationName': 'GetVideoComments',
                    'query': self._GRAPHQL_GETCOMMENTS_QUERY
                }).encode('utf8')),
            lambda x: x['data']['getVideoComments'])
        upload_date = video_info.get('createdAt')
        metadata = {}
        metadata['id'] = video_id
        metadata['title'] = video_info.get('title')[:-1]
        metadata['description'] = video_info.get('summary')
        metadata['channel'] = video_info.get('channel').get('title')
        metadata['channel_id'] = video_info.get('channel').get('_id')
        metadata['view_count'] = int_or_none(video_info.get('playCount'))
        metadata['thumbnail'] = url_or_none(video_info.get('largeImage'))
        metadata['duration'] = float_or_none(video_info.get('videoDuration'), scale=1000)
        metadata['upload_date'] = unified_strdate(upload_date)
        metadata['timestamp'] = unified_timestamp(upload_date)
        tags = []

        for tag in video_info.get('tags'):
            tags.append(tag.get('name'))

        metadata['tags'] = tags

        is_live = video_info.get('live')

        if is_live:
            formats = []
            formats.extend(self._extract_m3u8_formats(
                video_info.get('streamUrl'),
                video_id,
                'mp4',
                entry_protocol='m3u8_native',
                m3u8_id='hls',
                live=True))
            metadata['formats'] = formats
        else:
            metadata['url'] = video_info.get('directUrl')

        metadata['is_live'] = is_live
        comments = []

        for comment in video_comments:
            comments.append({
                'id': comment.get('_id'),
                'text': comment.get('content'),
                'author': comment.get('user').get('username'),
                'author_id': comment.get('user').get('_id'),
                'timestamp': unified_timestamp(comment.get('createdAt')),
                'parent': 'root'
            })
            if comment.get('replyCount') > 0:
                replies = try_get(
                    self._download_json(
                        self._GRAPHQL_API,
                        video_id,
                        headers=self._GRAPHQL_HEADERS,
                        data=json.dumps({
                            'variables': {
                                'id': comment.get('_id')
                            },
                            'operationName': 'GetCommentReplies',
                            'query': self._GRAPHQL_GETCOMMENTSREPLIES_QUERY
                        }).encode('utf8')),
                    lambda x: x['data']['getCommentReplies'])
                for reply in replies:
                    comments.append({
                        'id': reply.get('_id'),
                        'text': reply.get('content'),
                        'author': reply.get('user').get('username'),
                        'author_id': reply.get('user').get('_id'),
                        'timestamp': unified_timestamp(reply.get('createdAt')),
                        'parent': comment.get('_id')
                    })
        metadata["comments"] = comments
        return metadata
