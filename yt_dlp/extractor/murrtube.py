import functools

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    urlencode_postdata,
    extract_attributes
)


class MurrtubeIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                        (?:
                            murrtube:|
                            https?://murrtube\.net/v/|
                            https?://murrtube\.net/videos/(?P<slug>[a-z0-9\-]+?)\-
                        )
                        (?P<id>[A-Z0-9]{4}|[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})
                    '''

    _TESTS = [
        {
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
        },
        {
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
            }
        }
    ]

    def _real_initialize(self):
        homepage = self._download_webpage(
            'https://murrtube.net', None, note='Getting session token')
        data = self._hidden_inputs(homepage)
        self._download_webpage(
            'https://murrtube.net/accept_age_check', None, 'Set age cookie', data=urlencode_postdata(data))

    def _real_extract(self, url):
        video_id = self._match_valid_url(url)
        video_page = self._download_webpage(url, video_id)
        video_attrs = extract_attributes(self._search_regex(r'(<video[^>]+>)', video_page, 'video'))
        playlist = video_attrs['data-url'].split('?')[0]
        video_id = self._search_regex(r'https://storage.murrtube.net/murrtube-production/.+/(?P<id>.+)/index.m3u8', playlist, 'id', default=None)
        formats = self._extract_m3u8_formats(playlist, video_id, 'mp4', entry_protocol='m3u8_native', fatal=False)
        view_str = self._search_regex(r'(?P<views>[\d,]+) <span class="has-text-white">Views<\/span>', video_page, 'views', default=None)
        like_str = self._search_regex(r'(?P<likes>[\d,]+) <span class="has-text-white">Likes<\/span>', video_page, 'likes', default=None)
        comment_str = self._search_regex(r'(?P<comment>[\d,]+) <span class="has-text-white">Comments<\/span>', video_page, 'comment', default=None)
        return {
            'id': video_id,
            'title': self._og_search_title(video_page).split(' - Murrtube')[0],
            'age_limit': 18,
            'formats': formats,
            'description': self._og_search_description(video_page),
            'thumbnail': self._og_search_thumbnail(video_page).split('?')[0],
            'uploader': self._html_search_regex(
                r'<span class="pl-1 is-size-6 has-text-lighter">(.+?)</span>', video_page, 'uploader', default=None),
            'view_count': int(view_str.replace(',', '')) if view_str else None,
            'like_count': int(like_str.replace(',', '')) if like_str else None,
            'comment_count': int(comment_str.replace(',', '')) if comment_str else None
        }


class MurrtubeUserIE(MurrtubeIE):  # XXX: Do not subclass from concrete IE
    _WORKING = False
    IE_DESC = 'Murrtube user profile'
    _VALID_URL = r'https?://murrtube\.net/(?P<id>[^/]+)$'
    _TESTS = [
        {
            'url': 'https://murrtube.net/stormy',
            'info_dict': {
                'id': 'stormy',
            },
            'playlist_mincount': 27,
        }
    ]
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
