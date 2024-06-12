import itertools
import json

from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
    traverse_obj,
    try_get,
    unified_timestamp,
    url_or_none,
)


class BannedVideoBaseIE(InfoExtractor):
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

    _GRAPHQL_GETCHANNEL_QUERY = '''
query GetChannel($id: String!) {
    getChannelByIdOrTitle(id: $id) {
      _id
      title
      summary
      avatar
      coverImage
    }
}'''

    _GRAPHQL_GETCHANNELVIDEOS_QUERY = '''
query GetChannelVideos($id: String!, $limit: Float, $offset: Float) {
  getChannel(id: $id) {
    videos(limit: $limit, offset: $offset) {
      ...DisplayVideoFields
    }
  }
}

fragment DisplayVideoFields on Video {
  _id
}'''

    _GRAPHQL_GETPLAYLIST_QUERY = '''
query GetPlaylist($id: String!) {
    getPlaylist(id: $id) {
      title
      summary
    }
  }'''

    _GRAPHQL_GETPLAYLISTVIDEOS_QUERY = '''
query GetPlaylistVideos($id: String!, $limit: Float, $offset: Float) {
  getPlaylist(id: $id) {
    videos(limit: $limit, offset: $offset) {
      ...DisplayVideoFields
    }
  }
}

fragment DisplayVideoFields on Video {
  _id
}'''

    _GRAPHQL_QUERIES = {
        'GetVideoAndComments': _GRAPHQL_GETMETADATA_QUERY,
        'GetCommentReplies': _GRAPHQL_GETCOMMENTSREPLIES_QUERY,
        'GetChannel': _GRAPHQL_GETCHANNEL_QUERY,
        'GetChannelVideos': _GRAPHQL_GETCHANNELVIDEOS_QUERY,
        'GetPlaylist': _GRAPHQL_GETPLAYLIST_QUERY,
        'GetPlaylistVideos': _GRAPHQL_GETPLAYLISTVIDEOS_QUERY,
    }

    _API_HEADERS = {
        'apollographql-client-name': 'banned-web',
        'apollographql-client-version': '1.3',
        'Content-Type': 'application/json; charset=utf-8',
        'Origin': 'https://banned.video',
        'User-Agent': 'bannedVideoFrontEnd',
    }

    def _call_api(self, video_id, operation, note, variables=None):
        return self._download_json(
            'https://api.banned.video/graphql', video_id, note=note,
            headers=self._API_HEADERS, data=json.dumps({
                'variables': variables or {'id': video_id},
                'operationName': operation,
                'query': self._GRAPHQL_QUERIES[operation],
            }).encode('utf8')).get('data')

    def _paginate(self, playlist_id, query):
        for i in itertools.count(0):
            page_json = self._call_api(
                playlist_id, query, f'Downloading playlist page {i + 1}',
                {'id': playlist_id, 'limit': 1000, 'offset': 1000 * i})

            videos = traverse_obj(page_json, (..., 'videos', ...), expected_type=dict)

            for v in videos:
                yield v['_id']

            if not videos:
                return


class BannedVideoIE(BannedVideoBaseIE):
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

    def _get_comments(self, video_id, comments, comment_data):
        yield from comments
        for comment in comment_data.copy():
            comment_id = comment.get('_id')
            if comment.get('replyCount') > 0:
                reply_json = self._call_api(
                    video_id, 'GetCommentReplies', f'Downloading replies for comment {comment_id}',
                    {'id': comment_id})
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
        video_json = self._call_api(video_id, 'GetVideoAndComments', 'Downloading video metadata')
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
            '__post_extractor': self.extract_comments(video_id, comments, video_json.get('getVideoComments')),
        }


class BannedVideoChannelIE(BannedVideoBaseIE):
    _VALID_URL = r'https?://(?:www\.)?banned\.video/channel/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://banned.video/channel/war-room-with-owen-shroyer',
        'playlist_mincount': 9810,
        'info_dict': {
            'id': '5b9301172abf762e22bc22fd',
            'title': 'War Room With Owen Shroyer',
            'description': 'md5:821d45563613ec1f5a2b68046d13e2ff',
            'thumbnail': 'https://download.assets.video/images/acb63e7e-d23f-4901-9bac-cf3edda8eb89-large.png',
        },
    }, {
        'url': 'https://banned.video/channel/the-best-of-tucker-carlson-',
        'playlist_mincount': 21,
        'info_dict': {
            'thumbnail': 'https://download.assets.video/images/b1416a59-4902-480c-979e-246e62c34861-large.jpg',
            'id': '64598c46b1e3f80b32930313',
            'title': 'The Best of Tucker Carlson ',
            'description': 'Channel dedicated to Tucker',
        },
    }]

    def _real_extract(self, url):
        channel_info = self._call_api(
            self._match_id(url), 'GetChannel', 'Downloading channel metadata')['getChannelByIdOrTitle']
        channel_id = channel_info['_id']

        return self.playlist_result(
            [self.url_result(f'https://banned.video/watch?id={id}', url_transparent=True)
             for id in self._paginate(channel_id, 'GetChannelVideos')],
            channel_id, channel_info['title'], channel_info.get('summary'),
            thumbnail=channel_info.get('coverImage'))


class BannedVideoPlaylistIE(BannedVideoBaseIE):
    _VALID_URL = r'https?://(?:www\.)?banned\.video/playlist/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://banned.video/playlist/5d81058ce2ea200013c01580',
        'playlist_mincount': 1507,
        'info_dict': {
            'title': 'Full Alex Jones Shows',
            'id': '5d81058ce2ea200013c01580',
            'description': '',
        },
    }, {
        'url': 'https://banned.video/playlist/5db8bac40d7a4400199b73ca',
        'playlist_mincount': 92,
        'info_dict': {
            'title': 'Owen Shroyer Man On The Street Interviews',
            'id': '5db8bac40d7a4400199b73ca',
            'description': '',
        },
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        playlist_info = self._call_api(playlist_id, 'GetPlaylist', 'Downloading playlist metadata')['getPlaylist']

        return self.playlist_result(
            [self.url_result(f'https://banned.video/watch?id={id}', url_transparent=True)
             for id in self._paginate(playlist_id, 'GetPlaylistVideos')], playlist_id,
            playlist_info['title'], playlist_info.get('summary'))
