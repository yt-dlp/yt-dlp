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
            'id': 'ca885d8456b95de529b6723b158032e11115d',
            'ext': 'mp4',
            'title': 'Inferno X Skyler',
            'description': 'Humping a very good slutty sheppy (roomate)',
            'uploader': 'Inferno Wolf',
            'age_limit': 18,
            'thumbnail': 'https://storage.murrtube.net/murrtube-production/ekbs3zcfvuynnqfx72nn2tkokvsd',
            'comment_count': int,
            'view_count': int,
            'like_count': int,
        },
    }, {
        'url': 'https://murrtube.net/v/0J2Q',
        'md5': '31262f6ac56f0ca75e5a54a0f3fefcb6',
        'info_dict': {
            'id': '8442998c52134968d9caa36e473e1a6bac6ca',
            'ext': 'mp4',
            'uploader': 'Hayel',
            'title': 'Who\'s in charge now?',
            'description': 'md5:795791e97e5b0f1805ea84573f02a997',
            'age_limit': 18,
            'thumbnail': 'https://storage.murrtube.net/murrtube-production/fb1ojjwiucufp34ya6hxu5vfqi5s',
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
        video_attrs = extract_attributes(get_element_html_by_id('video', video_page))
        playlist = update_url(video_attrs['data-url'], query=None)
        video_id = self._search_regex(r'/([\da-f]+)/index.m3u8', playlist, 'video id')

        return {
            'id': video_id,
            'title': remove_end(self._og_search_title(video_page), ' - Murrtube'),
            'age_limit': 18,
            'formats': self._extract_m3u8_formats(playlist, video_id, 'mp4'),
            'description': self._og_search_description(video_page),
            'thumbnail': update_url(self._og_search_thumbnail(video_page, default=''), query=None) or None,
            'uploader': clean_html(get_element_by_class('pl-1 is-size-6 has-text-lighter', video_page)),
            'view_count': self._extract_count('Views', video_page),
            'like_count': self._extract_count('Likes', video_page),
            'comment_count': self._extract_count('Comments', video_page),
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
