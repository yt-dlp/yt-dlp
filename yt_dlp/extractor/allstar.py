import functools
import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    UnsupportedError,
    int_or_none,
    parse_qs,
    traverse_obj,
    urljoin,
)


_FIELDS = '''
    _id
    clipImageThumb
    clipLink
    clipLinkHLS
    clipTitle
    createdDate
    shareId
    user { _id }
    username
    views'''

_EXTRA_FIELDS = '''
    clipLength
    clipSizeBytes
    game'''

_QUERIES = {
    'clip': '''query ($id: String!) {
        video: getClip(clipIdentifier: $id) {
            %s %s
        }
    }''' % (_FIELDS, _EXTRA_FIELDS),
    'montage': '''query ($id: String!) {
        video: getMontage(clipIdentifier: $id) {
            %s
        }
    }''' % _FIELDS,
    'Clips': '''query ($page: Int!, $user: String!, $game: Int) {
        videos: clips(search: createdDate, page: $page, user: $user, mobile: false, game: $game) {
            data { %s %s }
        }
    }''' % (_FIELDS, _EXTRA_FIELDS),
    'Montages': '''query ($page: Int!, $user: String!) {
        videos: montages(search: createdDate, page: $page, user: $user) {
            data { %s }
        }
    }''' % _FIELDS,
    'Mobile Clips': '''query ($page: Int!, $user: String!) {
        videos: clips(search: createdDate, page: $page, user: $user, mobile: true) {
            data { %s %s }
        }
    }''' % (_FIELDS, _EXTRA_FIELDS),
}


class AllstarBaseIE(InfoExtractor):
    @staticmethod
    def _parse_video_data(video_data):
        def _media_url_or_none(path):
            return urljoin('https://media.allstar.gg/', path)

        def _profile_url_or_none(path):
            return urljoin('https:/allstar.gg/u/', path)

        return traverse_obj(video_data, {
            'id': ('_id', {str}),
            'display_id': ('shareId', {str}),
            'title': ('clipTitle', {str}),
            'url': ('clipLink', {_media_url_or_none}),
            'thumbnail': ('clipImageThumb', {_media_url_or_none}),
            'duration': ('clipLength', {int_or_none}),
            'filesize': ('clipSizeBytes', {int_or_none}),
            'timestamp': ('createdDate', {int_or_none}),
            'uploader': ('username', {str}),
            'uploader_id': ('user', '_id', {str}),
            'uploader_url': ('user', '_id', {_profile_url_or_none}),
            'view_count': ('views', {int_or_none}),
        })

    def _send_query(self, query, variables={}, path=(), video_id=None, note=None):
        response = self._download_json(
            'https://a1.allstar.gg/graphql', video_id, note=note,
            headers={'content-type': 'application/json'},
            data=json.dumps({'variables': variables, 'query': query}).encode())

        errors = response.get('errors')
        if errors:
            raise ExtractorError(errors, expected=True)

        return traverse_obj(response, path)


class AllstarIE(AllstarBaseIE):
    _VALID_URL = r'https?://(?:www\.)?allstar\.gg/(?P<type>(?:clip|montage))\?(?P=type)=(?P<id>[^/?#&]+)'

    _TESTS = [{
        'url': 'https://allstar.gg/clip?clip=64482c2da9eec30008a67d1b',
        'info_dict': {
            'id': '64482c2da9eec30008a67d1b',
            'title': '4K on Inferno',
            'url': 'md5:66befb5381eef0c9456026386c25fa55',
            'thumbnail': 'md5:33c520f681627826a95ac43b092ecd2b',
            'uploader': 'chrk.',
            'ext': 'mp4',
            'duration': 20,
            'filesize': 21199257,
            'timestamp': 1682451501555,
            'uploader_id': '62b8bdfc9021052f7905882d',
            'view_count': int,
        }
    }, {
        'url': 'https://allstar.gg/clip?clip=8LJLY4JKB',
        'info_dict': {
            'id': '64a1ec6b887f4c0008dc50b8',
            'display_id': '8LJLY4JKB',
            'title': 'AK-47 3K on Mirage',
            'url': 'md5:dde224fd12f035c0e2529a4ae34c4283',
            'ext': 'mp4',
            'thumbnail': 'md5:90564b121f5fd7a4924920ef45614634',
            'duration': 16,
            'filesize': 30175859,
            'timestamp': 1688333419392,
            'uploader': 'cherokee',
            'uploader_id': '62b8bdfc9021052f7905882d',
            'view_count': int,
        }
    }, {
        'url': 'https://allstar.gg/montage?montage=643e64089da7e9363e1fa66c',
        'info_dict': {
            'id': '643e64089da7e9363e1fa66c',
            'display_id': 'APQLGM2IMXW',
            'title': 'cherokee Rapid Fire Snipers Montage',
            'url': 'md5:a3ee356022115db2b27c81321d195945',
            'thumbnail': 'md5:f1a5e811864e173f180b738d956356f4',
            'ext': 'mp4',
            'timestamp': 1681810448040,
            'uploader': 'cherokee',
            'uploader_id': '62b8bdfc9021052f7905882d',
            'view_count': int,
        }
    }, {
        'url': 'https://allstar.gg/montage?montage=RILJMH6QOS',
        'info_dict': {
            'id': '64a2697372ce3703de29e868',
            'display_id': 'RILJMH6QOS',
            'title': 'cherokee Rapid Fire Snipers Montage',
            'url': 'md5:d5672e6f88579730c2310a80fdbc4030',
            'thumbnail': 'md5:60872f0d236863bb9a6f3dff1623403c',
            'uploader': 'cherokee',
            'ext': 'mp4',
            'timestamp': 1688365434271,
            'uploader_id': '62b8bdfc9021052f7905882d',
            'view_count': int,
        }
    }]

    def _real_extract(self, url):
        query_id, video_id = self._match_valid_url(url).group('type', 'id')

        return self._parse_video_data(
            self._send_query(
                _QUERIES.get(query_id), {'id': video_id},
                ('data', 'video'), video_id))


class AllstarProfileIE(AllstarBaseIE):
    _VALID_URL = r'https?://(?:www\.)?allstar\.gg/(?:profile\?user=|u/)(?P<id>[^/?#&]+)'

    _TESTS = [{
        'url': 'https://allstar.gg/profile?user=62b8bdfc9021052f7905882d',
        'info_dict': {
            'id': '62b8bdfc9021052f7905882d',
            'title': 'cherokee - Clips',
        },
        'playlist_mincount': 15
    }, {
        'url': 'https://allstar.gg/u/cherokee?game=730&view=Clips',
        'info_dict': {
            'id': '62b8bdfc9021052f7905882d',
            'title': 'cherokee - Clips',
        },
        'playlist_mincount': 15
    }, {
        'url': 'https://allstar.gg/u/62b8bdfc9021052f7905882d?view=Montages',
        'info_dict': {
            'id': '62b8bdfc9021052f7905882d',
            'title': 'cherokee - Montages',
        },
        'playlist_mincount': 4
    }, {
        'url': 'https://allstar.gg/profile?user=cherokee&view=Mobile Clips',
        'info_dict': {
            'id': '62b8bdfc9021052f7905882d',
            'title': 'cherokee - Mobile Clips',
        },
        'playlist_mincount': 1
    }]

    _PAGE_SIZE = 10

    @staticmethod
    def _set_webpage_url(info_dict):
        video_id = info_dict.get('id')
        video_url = info_dict.get('url')

        if video_url is None or video_id is None:
            return info_dict

        base_name = 'clip' if '/clips/' in video_url else 'montage'
        info_dict['webpage_url'] = f'https://allstar.gg/{base_name}?{base_name}={video_id}'
        info_dict['webpage_url_basename'] = base_name

        return info_dict

    def _get_page(self, user_id, display_id, game, query, page_num):
        page_num += 1

        for video_data in self._send_query(
                query, {
                    'user': user_id,
                    'page': page_num,
                    'game': game,
                }, ('data', 'videos', 'data'), display_id, f'Downloading page {page_num}'):
            yield self._set_webpage_url(self._parse_video_data(video_data))

    def _real_extract(self, url):
        display_id = self._match_id(url)
        profile_data = self._download_json(
            urljoin('https://api.allstar.gg/v1/users/profile/', display_id), display_id)
        user_id = traverse_obj(profile_data, ('data', ('_id'), {str}))

        if user_id is None:
            raise ExtractorError('Can not extract the user_id')

        username = traverse_obj(profile_data, ('data', 'profile', ('username'), {str}))
        url_query = parse_qs(url)
        game = traverse_obj(url_query, ('game', 0, {int}))
        query_id = traverse_obj(url_query, ('view', 0), default='Clips')

        if query_id not in ('Clips', 'Montages', 'Mobile Clips'):
            raise UnsupportedError(url)

        return self.playlist_result(
            OnDemandPagedList(
                functools.partial(
                    self._get_page, user_id, display_id, game, _QUERIES.get(query_id)), self._PAGE_SIZE),
            user_id, f'{username or display_id} - {query_id}')
