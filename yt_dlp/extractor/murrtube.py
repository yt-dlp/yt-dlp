import functools
import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    clean_html,
    extract_attributes,
    get_element_by_class,
    get_element_html_by_id,
    parse_count,
    remove_end,
    update_url,
    urlencode_postdata,
)
from ..utils.traversal import traverse_obj


class MurrtubeIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                        (?:
                            murrtube:|
                            https?://murrtube\.net/(?:v/|videos/(?P<slug>[a-z0-9-]+?)-)
                        )
                        (?P<id>[A-Z0-9]{4}|[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})
                    '''
    _TESTS = [{
        'url': 'https://murrtube.net/videos/inferno-x-skyler-148b6f2a-fdcc-4902-affe-9c0f41aaaca0',
        'md5': '70380878a77e8565d4aea7f68b8bbb35',
        'info_dict': {
            'id': '148b6f2a-fdcc-4902-affe-9c0f41aaaca0',
            'ext': 'mp4',
            'title': 'Inferno X Skyler',
            'description': 'Humping a very good slutty sheppy (roomate)',
            'uploader': 'Inferno Wolf',
            'uploader_id': 'inferno-wolf',
            'age_limit': 18,
            'thumbnail': 'https://storage.murrtube.net/038/ca885d8456b95de529b6723b158032e11115d/thumbnail.jpg',
            'comment_count': int,
            'view_count': int,
            'like_count': int,
        },
    }, {
        'url': 'https://murrtube.net/v/0J2Q',
        'md5': '31262f6ac56f0ca75e5a54a0f3fefcb6',
        'info_dict': {
            'id': 'fcfd303b-0002-4da9-9a9f-bef8ce4c0f0d',
            'ext': 'mp4',
            'uploader': 'Hayel',
            'uploader_id': 'hayel',
            'title': 'Who\'s in charge now?',
            'description': str,
            'age_limit': 18,
            'thumbnail': 'https://storage.murrtube.net/03c/8442998c52134968d9caa36e473e1a6bac6ca/thumbnail.jpg',
            'comment_count': int,
            'view_count': int,
            'like_count': int,
        },
    }]

    def _extract_count(self, name, html):
        return parse_count(self._search_regex(
            rf'([\d,]+)\s+<span[^>]*>{name}</span>', html, name, default=None))

    def _real_initialize(self):
        homepage = self._download_webpage(
            'https://murrtube.net', None, note='Getting session token')
        self._request_webpage(
            'https://murrtube.net/accept_age_check', None, 'Setting age cookie',
            data=urlencode_postdata(self._hidden_inputs(homepage)))

    def _real_extract(self, url):
        video_id = self._match_id(url)
        if video_id.startswith('murrtube:'):
            raise ExtractorError('Support for murrtube: prefix URLs is broken')
        video_page = self._download_webpage(url, video_id)

        props = traverse_obj(
            get_element_html_by_id('app', video_page),
            ({extract_attributes}, 'data-page', {json.loads}, 'props')) or {}

        medium = props.get('medium') or {}
        if not medium:
            raise ExtractorError('Could not find video metadata in page')

        playlist = medium.get('hls_url')
        if not playlist:
            raise ExtractorError('Could not find video stream URL')

        # Extract stable UUID as video ID, or fall back to the one from URL
        video_id = medium.get('id') or video_id

        return {
            'id': video_id,
            'title': medium.get('title'),
            'age_limit': 18,
            'formats': self._extract_m3u8_formats(playlist, video_id, 'mp4'),
            'description': medium.get('description'),
            'thumbnail': update_url(medium.get('thumbnail_url') or '', query=None) or None,
            'uploader': traverse_obj(medium, ('user', 'name')),
            'uploader_id': traverse_obj(medium, ('user', 'slug')),
            'view_count': medium.get('views_count'),
            'like_count': medium.get('likes_count'),
            'comment_count': medium.get('comments_count'),
        }


class MurrtubeUserIE(InfoExtractor):
    _WORKING = False
    IE_DESC = 'Murrtube user profile'
    _VALID_URL = r'https?://murrtube\.net/(?P<id>[^/]+)$'
    _TESTS = [{
        'url': 'https://murrtube.net/stormy',
        'info_dict': {
            'id': 'stormy',
        },
        'playlist_mincount': 27,
    }]
    _PAGE_SIZE = 10

    def _download_gql(self, video_id, op, note=None, fatal=True):
        result = self._download_json(
            'https://murrtube.net/graphql',
            video_id, note, data=json.dumps(op).encode(), fatal=fatal,
            headers={'Content-Type': 'application/json'})
        return result['data']

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
            f'Downloading page {page + 1}')
        if data is None:
            raise ExtractorError(f'Failed to retrieve video list for page {page + 1}')

        media = data['media']

        for entry in media:
            yield self.url_result('murrtube:{}'.format(entry['id']), MurrtubeIE.ie_key())

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
