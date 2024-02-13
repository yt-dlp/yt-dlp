import functools
import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    int_or_none,
    join_nonempty,
    parse_qs,
    urljoin,
)
from ..utils.traversal import traverse_obj

_FIELDS = '''
    _id
    clipImageSource
    clipImageThumb
    clipLink
    clipTitle
    createdDate
    shareId
    user { _id }
    username
    views'''

_EXTRA_FIELDS = '''
    clipLength
    clipSizeBytes'''

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
        def media_url_or_none(path):
            return urljoin('https://media.allstar.gg/', path)

        info = traverse_obj(video_data, {
            'id': ('_id', {str}),
            'display_id': ('shareId', {str}),
            'title': ('clipTitle', {str}),
            'url': ('clipLink', {media_url_or_none}),
            'thumbnails': (('clipImageThumb', 'clipImageSource'), {'url': {media_url_or_none}}),
            'duration': ('clipLength', {int_or_none}),
            'filesize': ('clipSizeBytes', {int_or_none}),
            'timestamp': ('createdDate', {functools.partial(int_or_none, scale=1000)}),
            'uploader': ('username', {str}),
            'uploader_id': ('user', '_id', {str}),
            'view_count': ('views', {int_or_none}),
        })

        if info.get('id') and info.get('url'):
            basename = 'clip' if '/clips/' in info['url'] else 'montage'
            info['webpage_url'] = f'https://allstar.gg/{basename}?{basename}={info["id"]}'

        info.update({
            'extractor_key': AllstarIE.ie_key(),
            'extractor': AllstarIE.IE_NAME,
            'uploader_url': urljoin('https://allstar.gg/u/', info.get('uploader_id')),
        })

        return info

    def _call_api(self, query, variables, path, video_id=None, note=None):
        response = self._download_json(
            'https://a1.allstar.gg/graphql', video_id, note=note,
            headers={'content-type': 'application/json'},
            data=json.dumps({'variables': variables, 'query': query}).encode())

        errors = traverse_obj(response, ('errors', ..., 'message', {str}))
        if errors:
            raise ExtractorError('; '.join(errors))

        return traverse_obj(response, path)


class AllstarIE(AllstarBaseIE):
    _VALID_URL = r'https?://(?:www\.)?allstar\.gg/(?P<type>(?:clip|montage))\?(?P=type)=(?P<id>[^/?#&]+)'

    _TESTS = [{
        'url': 'https://allstar.gg/clip?clip=64482c2da9eec30008a67d1b',
        'info_dict': {
            'id': '64482c2da9eec30008a67d1b',
            'title': '4K on Inferno',
            'url': 'md5:66befb5381eef0c9456026386c25fa55',
            'thumbnail': r're:https://media\.allstar\.gg/.+\.(?:png|jpg)$',
            'uploader': 'chrk.',
            'ext': 'mp4',
            'duration': 20,
            'filesize': 21199257,
            'timestamp': 1682451501,
            'uploader_id': '62b8bdfc9021052f7905882d',
            'uploader_url': 'https://allstar.gg/u/62b8bdfc9021052f7905882d',
            'upload_date': '20230425',
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
            'thumbnail': r're:https://media\.allstar\.gg/.+\.(?:png|jpg)$',
            'duration': 16,
            'filesize': 30175859,
            'timestamp': 1688333419,
            'uploader': 'cherokee',
            'uploader_id': '62b8bdfc9021052f7905882d',
            'uploader_url': 'https://allstar.gg/u/62b8bdfc9021052f7905882d',
            'upload_date': '20230702',
            'view_count': int,
        }
    }, {
        'url': 'https://allstar.gg/montage?montage=643e64089da7e9363e1fa66c',
        'info_dict': {
            'id': '643e64089da7e9363e1fa66c',
            'display_id': 'APQLGM2IMXW',
            'title': 'cherokee Rapid Fire Snipers Montage',
            'url': 'md5:a3ee356022115db2b27c81321d195945',
            'thumbnail': r're:https://media\.allstar\.gg/.+\.(?:png|jpg)$',
            'ext': 'mp4',
            'timestamp': 1681810448,
            'uploader': 'cherokee',
            'uploader_id': '62b8bdfc9021052f7905882d',
            'uploader_url': 'https://allstar.gg/u/62b8bdfc9021052f7905882d',
            'upload_date': '20230418',
            'view_count': int,
        }
    }, {
        'url': 'https://allstar.gg/montage?montage=RILJMH6QOS',
        'info_dict': {
            'id': '64a2697372ce3703de29e868',
            'display_id': 'RILJMH6QOS',
            'title': 'cherokee Rapid Fire Snipers Montage',
            'url': 'md5:d5672e6f88579730c2310a80fdbc4030',
            'thumbnail': r're:https://media\.allstar\.gg/.+\.(?:png|jpg)$',
            'ext': 'mp4',
            'timestamp': 1688365434,
            'uploader': 'cherokee',
            'uploader_id': '62b8bdfc9021052f7905882d',
            'uploader_url': 'https://allstar.gg/u/62b8bdfc9021052f7905882d',
            'upload_date': '20230703',
            'view_count': int,
        }
    }]

    def _real_extract(self, url):
        query_id, video_id = self._match_valid_url(url).group('type', 'id')

        return self._parse_video_data(
            self._call_api(
                _QUERIES.get(query_id), {'id': video_id}, ('data', 'video'), video_id))


class AllstarProfileIE(AllstarBaseIE):
    _VALID_URL = r'https?://(?:www\.)?allstar\.gg/(?:profile\?user=|u/)(?P<id>[^/?#&]+)'

    _TESTS = [{
        'url': 'https://allstar.gg/profile?user=62b8bdfc9021052f7905882d',
        'info_dict': {
            'id': '62b8bdfc9021052f7905882d-clips',
            'title': 'cherokee - Clips',
        },
        'playlist_mincount': 15
    }, {
        'url': 'https://allstar.gg/u/cherokee?game=730&view=Clips',
        'info_dict': {
            'id': '62b8bdfc9021052f7905882d-clips-730',
            'title': 'cherokee - Clips - 730',
        },
        'playlist_mincount': 15
    }, {
        'url': 'https://allstar.gg/u/62b8bdfc9021052f7905882d?view=Montages',
        'info_dict': {
            'id': '62b8bdfc9021052f7905882d-montages',
            'title': 'cherokee - Montages',
        },
        'playlist_mincount': 4
    }, {
        'url': 'https://allstar.gg/profile?user=cherokee&view=Mobile Clips',
        'info_dict': {
            'id': '62b8bdfc9021052f7905882d-mobile',
            'title': 'cherokee - Mobile Clips',
        },
        'playlist_mincount': 1
    }]

    _PAGE_SIZE = 10

    def _get_page(self, user_id, display_id, game, query, page_num):
        page_num += 1

        for video_data in self._call_api(
                query, {
                    'user': user_id,
                    'page': page_num,
                    'game': game,
                }, ('data', 'videos', 'data'), display_id, f'Downloading page {page_num}'):
            yield self._parse_video_data(video_data)

    def _real_extract(self, url):
        display_id = self._match_id(url)
        profile_data = self._download_json(
            urljoin('https://api.allstar.gg/v1/users/profile/', display_id), display_id)
        user_id = traverse_obj(profile_data, ('data', ('_id'), {str}))
        if not user_id:
            raise ExtractorError('Unable to extract the user id')

        username = traverse_obj(profile_data, ('data', 'profile', ('username'), {str}))
        url_query = parse_qs(url)
        game = traverse_obj(url_query, ('game', 0, {int_or_none}))
        query_id = traverse_obj(url_query, ('view', 0), default='Clips')

        if query_id not in ('Clips', 'Montages', 'Mobile Clips'):
            raise ExtractorError(f'Unsupported playlist URL type {query_id!r}')

        return self.playlist_result(
            OnDemandPagedList(
                functools.partial(
                    self._get_page, user_id, display_id, game, _QUERIES.get(query_id)), self._PAGE_SIZE),
            playlist_id=join_nonempty(user_id, query_id.lower().split()[0], game),
            playlist_title=join_nonempty((username or display_id), query_id, game, delim=' - '))
