import functools
import urllib.parse
import hashlib

from .common import InfoExtractor, SearchInfoExtractor
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    int_or_none,
    mimetype2ext,
    parse_qs,
    traverse_obj,
    unified_timestamp,
)


class IwaraIE(InfoExtractor):
    IE_NAME = 'iwara'
    _VALID_URL = r'https?://(?:www\.)?iwara\.tv/video/(?P<id>[a-zA-Z0-9]+)'
    _TESTS = [{
        # this video cannot be played because of migration
        'only_matching': True,
        'url': 'https://www.iwara.tv/video/k2ayoueezfkx6gvq',
        'info_dict': {
            'id': 'k2ayoueezfkx6gvq',
            'ext': 'mp4',
            'age_limit': 18,
            'title': 'Defeat of Irybelda - アイリベルダの敗北',
            'description': 'md5:70278abebe706647a8b4cb04cf23e0d3',
            'uploader': 'Inwerwm',
            'uploader_id': 'inwerwm',
            'tags': 'count:1',
            'like_count': 6133,
            'view_count': 1050343,
            'comment_count': 1,
            'timestamp': 1677843869,
            'modified_timestamp': 1679056362,
        },
    }, {
        'url': 'https://iwara.tv/video/1ywe1sbkqwumpdxz5/',
        'md5': '20691ce1473ec2766c0788e14c60ce66',
        'info_dict': {
            'id': '1ywe1sbkqwumpdxz5',
            'ext': 'mp4',
            'age_limit': 18,
            'title': 'Aponia 阿波尼亚SEX  Party Tonight 手动脱衣 大奶 裸腿',
            'description': 'md5:0c4c310f2e0592d68b9f771d348329ca',
            'uploader': '龙也zZZ',
            'uploader_id': 'user792540',
            'tags': [
                'uncategorized'
            ],
            'like_count': 1809,
            'view_count': 25156,
            'comment_count': 1,
            'timestamp': 1678732213,
            'modified_timestamp': 1679110271,
        },
    }]

    def _extract_formats(self, video_id, fileurl):
        up = urllib.parse.urlparse(fileurl)
        q = urllib.parse.parse_qs(up.query)
        paths = up.path.rstrip('/').split('/')
        # https://github.com/yt-dlp/yt-dlp/issues/6549#issuecomment-1473771047
        x_version = hashlib.sha1('_'.join((paths[-1], q['expires'][0], '5nFp9kmbNnHdAFhaqMvt')).encode()).hexdigest()

        files = self._download_json(fileurl, video_id, headers={'X-Version': x_version})
        for fmt in files:
            yield traverse_obj(fmt, {
                'format_id': 'name',
                'url': ('src', ('view', 'download'), {self._proto_relative_url}),
                'ext': ('type', {mimetype2ext}),
                'quality': ('name', {lambda x: int_or_none(x) or 1e4}),
                'height': ('name', {int_or_none}),
            }, get_all=False)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_data = self._download_json(f'http://api.iwara.tv/video/{video_id}', video_id)

        return {
            'id': video_id,
            'age_limit': 18 if video_data.get('rating') == 'ecchi' else 0,  # ecchi is 'sexy' in Japanese
            **traverse_obj(video_data, {
                'title': 'title',
                'description': 'body',
                'uploader': ('user', 'name'),
                'uploader_id': ('user', 'username'),
                'tags': ('tags', ..., 'id'),
                'like_count': 'numLikes',
                'view_count': 'numViews',
                'comment_count': 'numComments',
                'timestamp': ('createdAt', {unified_timestamp}),
                'modified_timestamp': ('updatedAt', {unified_timestamp}),
                'thumbnail': ('file', 'id', {str}, {
                    lambda x: f'https://files.iwara.tv/image/thumbnail/{x}/thumbnail-00.jpg'}),
            }),
            'formats': list(self._extract_formats(video_id, video_data.get('fileUrl'))),
        }


class IwaraPlaylistBaseIE(InfoExtractor):
    _PER_PAGE = 32

    def _request_page(self, page, *args):
        raise NotImplementedError('This method must be implemented by subclasses')

    def _entries(self, *args):
        *args, first_page, page = args
        videos = self._request_page(page, *args) if page or not first_page else first_page
        for x in traverse_obj(videos, ('results', ..., 'id')):
            yield self.url_result(f'https://iwara.tv/video/{x}')

    def _paged_list(self, playlist_id, playlist_title, first_page, *eargs):
        return self.playlist_result(
            OnDemandPagedList(
                functools.partial(self._entries, *eargs, first_page),
                self._PER_PAGE),
            playlist_id, playlist_title)


class IwaraUserIE(IwaraPlaylistBaseIE):
    _VALID_URL = r'https?://(?:www\.)?iwara\.tv/profile/(?P<id>[^/?#&]+)'
    IE_NAME = 'iwara:user'

    _TESTS = [{
        'url': 'https://iwara.tv/profile/user792540/videos',
        'info_dict': {
            'id': 'user792540',
        },
        'playlist_mincount': 80,
    }, {
        'url': 'https://iwara.tv/profile/theblackbirdcalls/videos',
        'info_dict': {
            'id': 'theblackbirdcalls',
        },
        'playlist_mincount': 723,
    }, {
        'url': 'https://iwara.tv/profile/user792540',
        'only_matching': True,
    }, {
        'url': 'https://iwara.tv/profile/theblackbirdcalls',
        'only_matching': True,
    }]

    def _request_page(self, page, playlist_id, user_id):
        return self._download_json(
            'https://api.iwara.tv/videos', playlist_id,
            note=f'Downloading page {page}',
            query={
                'page': page,
                'sort': 'date',
                'user': user_id,
                'limit': self._PER_PAGE,
            })

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        user_info = self._download_json(
            f'https://api.iwara.tv/profile/{playlist_id}', playlist_id,
            note='Requesting user info')
        user_id = traverse_obj(user_info, ('user', 'id'))

        return self._paged_list(playlist_id, traverse_obj(user_info, ('user', 'name')), None, playlist_id, user_id)


class IwaraPlaylistIE(IwaraPlaylistBaseIE):
    # the ID is an UUID but I don't think it's necessary to write concrete regex
    _VALID_URL = r'https?://(?:www\.)?iwara\.tv/playlist/(?P<id>[0-9a-f-]+)'
    IE_NAME = 'iwara:playlist'

    _TESTS = [{
        'url': 'https://iwara.tv/playlist/458e5486-36a4-4ac0-b233-7e9eef01025f',
        'info_dict': {
            'id': '458e5486-36a4-4ac0-b233-7e9eef01025f',
        },
        'playlist_mincount': 3,
    }]

    def _request_page(self, page, playlist_id):
        return self._download_json(
            f'https://api.iwara.tv/playlist/{playlist_id}', playlist_id, f'Downloading page {page}' if page else 'Requesting playlist info',
            query={'page': page, 'limit': self._PER_PAGE})

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        page_0 = self._request_page(0, playlist_id)
        return self._paged_list(
            playlist_id, traverse_obj(page_0, ('title', 'name')),
            page_0, playlist_id)


class IwaraSearchBaseIE(IwaraPlaylistBaseIE):
    def _request_page(self, page, playlist_id):
        return self._download_json(
            'https://api.iwara.tv/search', playlist_id,
            note=f'Downloading page {page}',
            query={
                'type': 'video',
                'query': playlist_id,
                'page': page,
                'limit': self._PER_PAGE,
            })


class IwaraSearchIE(IwaraSearchBaseIE, SearchInfoExtractor):
    IE_NAME = 'iwara:search'
    _SEARCH_KEY = 'iwara'

    _TESTS = [{
        'url': 'iwaraall:version',
        'info_dict': {
            'id': 'version',
        },
        'playlist_mincount': 11000,
    }]

    def _search_results(self, query):
        return self._paged_list(query, query, None, query)['entries']


class IwaraSearchURLIE(IwaraSearchBaseIE):
    _VALID_URL = r'https?://(?:www\.)?iwara\.tv/search\?query=(?P<id>[^&#]+)'
    IE_DESC = None  # do not list

    _TESTS = [{
        'url': 'https://www.iwara.tv/search?query=version',
        'info_dict': {
            'id': 'version',
        },
        'playlist_mincount': 11000,
    }]

    def _real_extract(self, url):
        playlist_id = traverse_obj(parse_qs(url), ('query', 0)) or urllib.parse.unquote(self._match_id(url))
        return self._paged_list(playlist_id, playlist_id, None, playlist_id)
