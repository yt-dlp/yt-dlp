import functools
import hashlib
import json
import time
import urllib.error
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    int_or_none,
    jwt_decode_hs256,
    mimetype2ext,
    qualities,
    traverse_obj,
    try_call,
    unified_timestamp,
)


class IwaraBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'iwara'
    _USERTOKEN = None
    _MEDIATOKEN = None

    def _is_token_expired(self, token, token_type):
        # User token TTL == ~3 weeks, Media token TTL == ~1 hour
        if (try_call(lambda: jwt_decode_hs256(token)['exp']) or 0) <= int(time.time() - 120):
            self.to_screen(f'{token_type} token has expired')
            return True

    def _get_user_token(self):
        username, password = self._get_login_info()
        if not username or not password:
            return

        user_token = IwaraBaseIE._USERTOKEN or self.cache.load(self._NETRC_MACHINE, username)
        if not user_token or self._is_token_expired(user_token, 'User'):
            response = self._download_json(
                'https://api.iwara.tv/user/login', None, note='Logging in',
                headers={'Content-Type': 'application/json'}, data=json.dumps({
                    'email': username,
                    'password': password,
                }).encode(), expected_status=lambda x: True)
            user_token = traverse_obj(response, ('token', {str}))
            if not user_token:
                error = traverse_obj(response, ('message', {str}))
                if 'invalidLogin' in error:
                    raise ExtractorError('Invalid login credentials', expected=True)
                else:
                    raise ExtractorError(f'Iwara API said: {error or "nothing"}')

            self.cache.store(self._NETRC_MACHINE, username, user_token)

        IwaraBaseIE._USERTOKEN = user_token

    def _get_media_token(self):
        self._get_user_token()
        if not IwaraBaseIE._USERTOKEN:
            return  # user has not passed credentials

        if not IwaraBaseIE._MEDIATOKEN or self._is_token_expired(IwaraBaseIE._MEDIATOKEN, 'Media'):
            IwaraBaseIE._MEDIATOKEN = self._download_json(
                'https://api.iwara.tv/user/token', None, note='Fetching media token',
                data=b'', headers={
                    'Authorization': f'Bearer {IwaraBaseIE._USERTOKEN}',
                    'Content-Type': 'application/json',
                })['accessToken']

        return {'Authorization': f'Bearer {IwaraBaseIE._MEDIATOKEN}'}

    def _perform_login(self, username, password):
        self._get_media_token()


class IwaraIE(IwaraBaseIE):
    IE_NAME = 'iwara'
    _VALID_URL = r'https?://(?:www\.|ecchi\.)?iwara\.tv/videos?/(?P<id>[a-zA-Z0-9]+)'
    _TESTS = [{
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
        'skip': 'this video cannot be played because of migration',
    }, {
        'url': 'https://iwara.tv/video/1ywe1sbkqwumpdxz5/',
        'md5': '7645f966f069b8ec9210efd9130c9aad',
        'info_dict': {
            'id': '1ywe1sbkqwumpdxz5',
            'ext': 'mp4',
            'age_limit': 18,
            'title': 'Aponia アポニア SEX  Party Tonight 手の脱衣 巨乳 ',
            'description': 'md5:3f60016fff22060eef1ef26d430b1f67',
            'uploader': 'Lyu ya',
            'uploader_id': 'user792540',
            'tags': [
                'uncategorized',
            ],
            'like_count': int,
            'view_count': int,
            'comment_count': int,
            'timestamp': 1678732213,
            'modified_timestamp': int,
            'thumbnail': 'https://files.iwara.tv/image/thumbnail/581d12b5-46f4-4f15-beb2-cfe2cde5d13d/thumbnail-00.jpg',
            'modified_date': '20230614',
            'upload_date': '20230313',
        },
    }, {
        'url': 'https://iwara.tv/video/blggmfno8ghl725bg',
        'info_dict': {
            'id': 'blggmfno8ghl725bg',
            'ext': 'mp4',
            'age_limit': 18,
            'title': 'お外でおしっこしちゃう猫耳ロリメイド',
            'description': 'md5:0342ba9bf6db09edbbb28729657c3611',
            'uploader': 'Fe_Kurosabi',
            'uploader_id': 'fekurosabi',
            'tags': [
                'pee',
            ],
            'like_count': int,
            'view_count': int,
            'comment_count': int,
            'timestamp': 1598880567,
            'modified_timestamp': int,
            'upload_date': '20200831',
            'modified_date': '20230605',
            'thumbnail': 'https://files.iwara.tv/image/thumbnail/7693e881-d302-42a4-a780-f16d66b5dadd/thumbnail-00.jpg',
            # 'availability': 'needs_auth',
        },
    }]

    def _extract_formats(self, video_id, fileurl):
        up = urllib.parse.urlparse(fileurl)
        q = urllib.parse.parse_qs(up.query)
        paths = up.path.rstrip('/').split('/')
        # https://github.com/yt-dlp/yt-dlp/issues/6549#issuecomment-1473771047
        x_version = hashlib.sha1('_'.join((paths[-1], q['expires'][0], '5nFp9kmbNnHdAFhaqMvt')).encode()).hexdigest()

        preference = qualities(['preview', '360', '540', 'Source'])

        files = self._download_json(fileurl, video_id, headers={'X-Version': x_version})
        for fmt in files:
            yield traverse_obj(fmt, {
                'format_id': 'name',
                'url': ('src', ('view', 'download'), {self._proto_relative_url}),
                'ext': ('type', {mimetype2ext}),
                'quality': ('name', {preference}),
                'height': ('name', {int_or_none}),
            }, get_all=False)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        username, _ = self._get_login_info()
        video_data = self._download_json(
            f'https://api.iwara.tv/video/{video_id}', video_id,
            expected_status=lambda x: True, headers=self._get_media_token())
        errmsg = video_data.get('message')
        # at this point we can actually get uploaded user info, but do we need it?
        if errmsg == 'errors.privateVideo':
            self.raise_login_required('Private video. Login if you have permissions to watch', method='password')
        elif errmsg == 'errors.notFound' and not username:
            self.raise_login_required('Video may need login to view', method='password')
        elif errmsg:  # None if success
            raise ExtractorError(f'Iwara says: {errmsg}')

        if not video_data.get('fileUrl'):
            if video_data.get('embedUrl'):
                return self.url_result(video_data.get('embedUrl'))
            raise ExtractorError('This video is unplayable', expected=True)

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


class IwaraUserIE(IwaraBaseIE):
    _VALID_URL = r'https?://(?:www\.)?iwara\.tv/profile/(?P<id>[^/?#&]+)'
    IE_NAME = 'iwara:user'
    _PER_PAGE = 32

    _TESTS = [{
        'url': 'https://iwara.tv/profile/user792540/videos',
        'info_dict': {
            'id': 'user792540',
            'title': 'Lyu ya',
        },
        'playlist_mincount': 70,
    }, {
        'url': 'https://iwara.tv/profile/theblackbirdcalls/videos',
        'info_dict': {
            'id': 'theblackbirdcalls',
            'title': 'TheBlackbirdCalls',
        },
        'playlist_mincount': 723,
    }, {
        'url': 'https://iwara.tv/profile/user792540',
        'only_matching': True,
    }, {
        'url': 'https://iwara.tv/profile/theblackbirdcalls',
        'only_matching': True,
    }, {
        'url': 'https://www.iwara.tv/profile/lumymmd',
        'info_dict': {
            'id': 'lumymmd',
            'title': 'Lumy MMD',
        },
        'playlist_mincount': 1,
    }]

    def _entries(self, playlist_id, user_id, page):
        videos = self._download_json(
            'https://api.iwara.tv/videos', playlist_id,
            note=f'Downloading page {page}',
            query={
                'page': page,
                'sort': 'date',
                'user': user_id,
                'limit': self._PER_PAGE,
            }, headers=self._get_media_token())
        for x in traverse_obj(videos, ('results', ..., 'id')):
            yield self.url_result(f'https://iwara.tv/video/{x}')

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        user_info = self._download_json(
            f'https://api.iwara.tv/profile/{playlist_id}', playlist_id,
            note='Requesting user info')
        user_id = traverse_obj(user_info, ('user', 'id'))

        return self.playlist_result(
            OnDemandPagedList(
                functools.partial(self._entries, playlist_id, user_id),
                self._PER_PAGE),
            playlist_id, traverse_obj(user_info, ('user', 'name')))


class IwaraPlaylistIE(IwaraBaseIE):
    _VALID_URL = r'https?://(?:www\.)?iwara\.tv/playlist/(?P<id>[0-9a-f-]+)'
    IE_NAME = 'iwara:playlist'
    _PER_PAGE = 32

    _TESTS = [{
        'url': 'https://iwara.tv/playlist/458e5486-36a4-4ac0-b233-7e9eef01025f',
        'info_dict': {
            'id': '458e5486-36a4-4ac0-b233-7e9eef01025f',
        },
        'playlist_mincount': 3,
    }]

    def _entries(self, playlist_id, first_page, page):
        videos = self._download_json(
            'https://api.iwara.tv/videos', playlist_id, f'Downloading page {page}',
            query={'page': page, 'limit': self._PER_PAGE},
            headers=self._get_media_token()) if page else first_page
        for x in traverse_obj(videos, ('results', ..., 'id')):
            yield self.url_result(f'https://iwara.tv/video/{x}')

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        page_0 = self._download_json(
            f'https://api.iwara.tv/playlist/{playlist_id}?page=0&limit={self._PER_PAGE}', playlist_id,
            note='Requesting playlist info', headers=self._get_media_token())

        return self.playlist_result(
            OnDemandPagedList(
                functools.partial(self._entries, playlist_id, page_0),
                self._PER_PAGE),
            playlist_id, traverse_obj(page_0, ('title', 'name')))
