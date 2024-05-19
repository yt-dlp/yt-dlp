import functools
import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    determine_ext,
    int_or_none,
    try_get,
)


class MurrtubeIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'''(?x)
                        (?:
                            murrtube:|
                            https?://murrtube\.net/videos/(?P<slug>[a-z0-9\-]+)\-
                        )
                        (?P<id>[a-f0-9]{8}\-[a-f0-9]{4}\-[a-f0-9]{4}\-[a-f0-9]{4}\-[a-f0-9]{12})
                    '''
    _TEST = {
        'url': 'https://murrtube.net/videos/inferno-x-skyler-148b6f2a-fdcc-4902-affe-9c0f41aaaca0',
        'md5': '169f494812d9a90914b42978e73aa690',
        'info_dict': {
            'id': '148b6f2a-fdcc-4902-affe-9c0f41aaaca0',
            'ext': 'mp4',
            'title': 'Inferno X Skyler',
            'description': 'Humping a very good slutty sheppy (roomate)',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 284,
            'uploader': 'Inferno Wolf',
            'age_limit': 18,
            'comment_count': int,
            'view_count': int,
            'like_count': int,
            'tags': ['hump', 'breed', 'Fursuit', 'murrsuit', 'bareback'],
        }
    }

    def _download_gql(self, video_id, op, note=None, fatal=True):
        result = self._download_json(
            'https://murrtube.net/graphql',
            video_id, note, data=json.dumps(op).encode(), fatal=fatal,
            headers={'Content-Type': 'application/json'})
        return result['data']

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._download_gql(video_id, {
            'operationName': 'Medium',
            'variables': {
                'id': video_id,
            },
            'query': '''\
query Medium($id: ID!) {
  medium(id: $id) {
    title
    description
    key
    duration
    commentsCount
    likesCount
    viewsCount
    thumbnailKey
    tagList
    user {
      name
      __typename
    }
    __typename
  }
}'''})
        meta = data['medium']

        storage_url = 'https://storage.murrtube.net/murrtube/'
        format_url = storage_url + meta.get('key', '')
        thumbnail = storage_url + meta.get('thumbnailKey', '')

        if determine_ext(format_url) == 'm3u8':
            formats = self._extract_m3u8_formats(
                format_url, video_id, 'mp4', entry_protocol='m3u8_native', fatal=False)
        else:
            formats = [{'url': format_url}]

        return {
            'id': video_id,
            'title': meta.get('title'),
            'description': meta.get('description'),
            'formats': formats,
            'thumbnail': thumbnail,
            'duration': int_or_none(meta.get('duration')),
            'uploader': try_get(meta, lambda x: x['user']['name']),
            'view_count': meta.get('viewsCount'),
            'like_count': meta.get('likesCount'),
            'comment_count': meta.get('commentsCount'),
            'tags': meta.get('tagList'),
            'age_limit': 18,
        }


class MurrtubeUserIE(MurrtubeIE):  # XXX: Do not subclass from concrete IE
    _WORKING = False
    IE_DESC = 'Murrtube user profile'
    _VALID_URL = r'https?://murrtube\.net/(?P<id>[^/]+)$'
    _TEST = {
        'url': 'https://murrtube.net/stormy',
        'info_dict': {
            'id': 'stormy',
        },
        'playlist_mincount': 27,
    }
    _PAGE_SIZE = 10

    def _fetch_page(self, username, user_id, page):
        data = self._download_gql(username, {
            'operationName': 'Media',
            'variables': {
                'limit': self._PAGE_SIZE,
                'offset': page * self._PAGE_SIZE,
                'sort': 'latest',
                'userId': user_id,
            },
            'query': '''\
query Media($q: String, $sort: String, $userId: ID, $offset: Int!, $limit: Int!) {
  media(q: $q, sort: $sort, userId: $userId, offset: $offset, limit: $limit) {
    id
    __typename
  }
}'''},
            'Downloading page {0}'.format(page + 1))
        if data is None:
            raise ExtractorError(f'Failed to retrieve video list for page {page + 1}')

        media = data['media']

        for entry in media:
            yield self.url_result('murrtube:{0}'.format(entry['id']), MurrtubeIE.ie_key())

    def _real_extract(self, url):
        username = self._match_id(url)
        data = self._download_gql(username, {
            'operationName': 'User',
            'variables': {
                'id': username,
            },
            'query': '''\
query User($id: ID!) {
  user(id: $id) {
    id
    __typename
  }
}'''},
            'Downloading user info')
        if data is None:
            raise ExtractorError('Failed to fetch user info')

        user = data['user']

        entries = OnDemandPagedList(functools.partial(
            self._fetch_page, username, user.get('id')), self._PAGE_SIZE)

        return self.playlist_result(entries, username)
