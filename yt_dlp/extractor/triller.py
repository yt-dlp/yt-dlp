import itertools
import json
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    HEADRequest,
    UnsupportedError,
    determine_ext,
    int_or_none,
    parse_resolution,
    str_or_none,
    traverse_obj,
    unified_timestamp,
    url_basename,
    urljoin,
    url_or_none,
)


class TrillerBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'triller'
    _API_BASE_URL = 'https://social.triller.co/v1.5'
    _API_HEADERS = {'Origin': 'https://triller.co'}

    def _perform_login(self, username, password):
        if self._API_HEADERS.get('Authorization'):
            return

        headers = {**self._API_HEADERS, 'Content-Type': 'application/json'}
        user_check = traverse_obj(self._download_json(
            f'{self._API_BASE_URL}/api/user/is-valid-username', None, note='Checking username',
            fatal=False, expected_status=400, headers=headers,
            data=json.dumps({'username': username}, separators=(',', ':')).encode()), 'status')

        if user_check:  # endpoint returns `"status":false` if username exists
            raise ExtractorError('Unable to login: Invalid username', expected=True)

        login = self._download_json(
            f'{self._API_BASE_URL}/user/auth', None, note='Logging in', fatal=False,
            expected_status=400, headers=headers, data=json.dumps({
                'username': username,
                'password': password,
            }, separators=(',', ':')).encode()) or {}

        if not login.get('auth_token'):
            if login.get('error') == 1008:
                raise ExtractorError('Unable to login: Incorrect password', expected=True)
            raise ExtractorError('Unable to login')

        self._API_HEADERS['Authorization'] = f'Bearer {login["auth_token"]}'

    def _get_comments(self, video_id, limit=15):
        comment_info = self._download_json(
            f'{self._API_BASE_URL}/api/videos/{video_id}/comments_v2',
            video_id, fatal=False, note='Downloading comments API JSON',
            headers=self._API_HEADERS, query={'limit': limit}) or {}
        if not comment_info.get('comments'):
            return
        yield from traverse_obj(comment_info, ('comments', ..., {
            'id': ('id', {str_or_none}),
            'text': 'body',
            'author': ('author', 'username'),
            'author_id': ('author', 'user_id'),
            'timestamp': ('timestamp', {unified_timestamp}),
        }))

    def _check_user_info(self, user_info):
        if user_info.get('private') and not user_info.get('followed_by_me'):
            raise ExtractorError('This video is private', expected=True)
        elif traverse_obj(user_info, 'blocked_by_user', 'blocking_user'):
            raise ExtractorError('The author of the video is blocked', expected=True)
        return user_info

    def _parse_video_info(self, video_info, username, user_id, display_id=None):
        video_id = str(video_info['id'])
        display_id = display_id or video_info.get('video_uuid')

        if traverse_obj(video_info, (
                None, ('transcoded_url', 'video_url', 'stream_url', 'audio_url'),
                {lambda x: re.search(r'/copyright/', x)}), get_all=False):
            self.raise_no_formats('This video has been removed due to licensing restrictions', expected=True)

        def format_info(url):
            return {
                'url': url,
                'ext': determine_ext(url),
                'format_id': url_basename(url).split('.')[0],
            }

        formats = []

        if determine_ext(video_info.get('transcoded_url')) == 'm3u8':
            formats.extend(self._extract_m3u8_formats(
                video_info['transcoded_url'], video_id, 'mp4', m3u8_id='hls', fatal=False))

        for video in traverse_obj(video_info, ('video_set', lambda _, v: url_or_none(v['url']))):
            formats.append({
                **format_info(video['url']),
                **parse_resolution(video.get('resolution')),
                'vcodec': video.get('codec'),
                'vbr': int_or_none(video.get('bitrate'), 1000),
            })

        video_url = traverse_obj(video_info, 'video_url', 'stream_url', expected_type=url_or_none)
        if video_url:
            formats.append({
                **format_info(video_url),
                'vcodec': 'h264',
                **traverse_obj(video_info, {
                    'width': 'width',
                    'height': 'height',
                    'filesize': 'filesize',
                }, expected_type=int_or_none),
            })

        audio_url = url_or_none(video_info.get('audio_url'))
        if audio_url:
            formats.append(format_info(audio_url))

        comment_count = traverse_obj(video_info, ('comment_count', {int_or_none}))

        return {
            'id': video_id,
            'display_id': display_id,
            'uploader': username,
            'uploader_id': user_id or traverse_obj(video_info, ('user', 'user_id', {str_or_none})),
            'webpage_url': urljoin(f'https://triller.co/@{username}/video/', display_id),
            'uploader_url': f'https://triller.co/@{username}',
            'extractor_key': TrillerIE.ie_key(),
            'extractor': TrillerIE.IE_NAME,
            'formats': formats,
            'comment_count': comment_count,
            '__post_extractor': self.extract_comments(video_id, comment_count),
            **traverse_obj(video_info, {
                'title': ('description', {lambda x: x.replace('\r\n', ' ')}),
                'description': 'description',
                'creator': ((('user'), ('users', lambda _, v: str(v['user_id']) == user_id)), 'name'),
                'thumbnail': ('thumbnail_url', {url_or_none}),
                'timestamp': ('timestamp', {unified_timestamp}),
                'duration': ('duration', {int_or_none}),
                'view_count': ('play_count', {int_or_none}),
                'like_count': ('likes_count', {int_or_none}),
                'artist': 'song_artist',
                'track': 'song_title',
            }, get_all=False),
        }


class TrillerIE(TrillerBaseIE):
    _VALID_URL = r'''(?x)
            https?://(?:www\.)?triller\.co/
            @(?P<username>[\w.]+)/video/(?P<id>[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12})
        '''
    _TESTS = [{
        'url': 'https://triller.co/@theestallion/video/2358fcd7-3df2-4c77-84c8-1d091610a6cf',
        'md5': '228662d783923b60d78395fedddc0a20',
        'info_dict': {
            'id': '71595734',
            'ext': 'mp4',
            'title': 'md5:9a2bf9435c5c4292678996a464669416',
            'thumbnail': r're:^https://uploads\.cdn\.triller\.co/.+\.jpg$',
            'description': 'md5:9a2bf9435c5c4292678996a464669416',
            'uploader': 'theestallion',
            'uploader_id': '18992236',
            'creator': 'Megan Thee Stallion',
            'timestamp': 1660598222,
            'upload_date': '20220815',
            'duration': 47,
            'view_count': int,
            'like_count': int,
            'artist': 'Megan Thee Stallion',
            'track': 'Her',
            'uploader_url': 'https://triller.co/@theestallion',
            'comment_count': int,
        },
        'skip': 'This video has been removed due to licensing restrictions',
    }, {
        'url': 'https://triller.co/@charlidamelio/video/46c6fcfa-aa9e-4503-a50c-68444f44cddc',
        'md5': '874055f462af5b0699b9dbb527a505a0',
        'info_dict': {
            'id': '71621339',
            'ext': 'mp4',
            'title': 'md5:4c91ea82760fe0fffb71b8c3aa7295fc',
            'display_id': '46c6fcfa-aa9e-4503-a50c-68444f44cddc',
            'thumbnail': r're:^https://uploads\.cdn\.triller\.co/.+\.jpg$',
            'description': 'md5:4c91ea82760fe0fffb71b8c3aa7295fc',
            'uploader': 'charlidamelio',
            'uploader_id': '1875551',
            'creator': 'charli damelio',
            'timestamp': 1660773354,
            'upload_date': '20220817',
            'duration': 16,
            'view_count': int,
            'like_count': int,
            'artist': 'Dixie',
            'track': 'Someone to Blame',
            'uploader_url': 'https://triller.co/@charlidamelio',
            'comment_count': int,
        },
    }, {
        'url': 'https://triller.co/@theestallion/video/07f35f38-1f51-48e2-8c5f-f7a8e829988f',
        'md5': 'af7b3553e4b8bfca507636471ee2eb41',
        'info_dict': {
            'id': '71837829',
            'ext': 'mp4',
            'title': 'UNGRATEFUL VIDEO OUT NOW 👏🏾👏🏾👏🏾 💙💙 link my bio  #womeninhiphop',
            'display_id': '07f35f38-1f51-48e2-8c5f-f7a8e829988f',
            'thumbnail': r're:^https://uploads\.cdn\.triller\.co/.+\.jpg$',
            'description': 'UNGRATEFUL VIDEO OUT NOW 👏🏾👏🏾👏🏾 💙💙 link my bio\r\n #womeninhiphop',
            'uploader': 'theestallion',
            'uploader_id': '18992236',
            'creator': 'Megan Thee Stallion',
            'timestamp': 1662486178,
            'upload_date': '20220906',
            'duration': 30,
            'view_count': int,
            'like_count': int,
            'artist': 'Unknown',
            'track': 'Unknown',
            'uploader_url': 'https://triller.co/@theestallion',
            'comment_count': int,
        },
    }]

    def _real_extract(self, url):
        username, display_id = self._match_valid_url(url).group('username', 'id')

        video_info = self._download_json(
            f'{self._API_BASE_URL}/api/videos/{display_id}', display_id,
            headers=self._API_HEADERS)['videos'][0]

        self._check_user_info(video_info.get('user') or {})

        return self._parse_video_info(video_info, username, None, display_id)


class TrillerUserIE(TrillerBaseIE):
    _VALID_URL = r'https?://(?:www\.)?triller\.co/@(?P<id>[\w.]+)/?(?:$|[#?])'
    _TESTS = [{
        'url': 'https://triller.co/@theestallion',
        'playlist_mincount': 12,
        'info_dict': {
            'id': '18992236',
            'title': 'theestallion',
            'thumbnail': r're:^https://uploads\.cdn\.triller\.co/.+\.jpg$',
        },
    }, {
        'url': 'https://triller.co/@charlidamelio',
        'playlist_mincount': 150,
        'info_dict': {
            'id': '1875551',
            'title': 'charlidamelio',
            'thumbnail': r're:^https://uploads\.cdn\.triller\.co/.+\.jpg$',
        },
    }]

    def _real_initialize(self):
        if not self._API_HEADERS.get('Authorization'):
            guest = self._download_json(
                f'{self._API_BASE_URL}/user/create_guest', None,
                note='Creating guest session', data=b'', headers=self._API_HEADERS, query={
                    'platform': 'Web',
                    'app_version': '',
                })
            if not guest.get('auth_token'):
                raise ExtractorError('Unable to fetch required auth token for user extraction')

            self._API_HEADERS['Authorization'] = f'Bearer {guest["auth_token"]}'

    def _entries(self, username, user_id, limit=6):
        query = {'limit': limit}
        for page in itertools.count(1):
            videos = self._download_json(
                f'{self._API_BASE_URL}/api/users/{user_id}/videos',
                username, note=f'Downloading user video list page {page}',
                headers=self._API_HEADERS, query=query)

            for video in traverse_obj(videos, ('videos', ...)):
                yield self._parse_video_info(video, username, user_id)

            query['before_time'] = traverse_obj(videos, ('videos', -1, 'timestamp'))
            if not query['before_time']:
                break

    def _real_extract(self, url):
        username = self._match_id(url)

        user_info = self._check_user_info(self._download_json(
            f'{self._API_BASE_URL}/api/users/by_username/{username}',
            username, note='Downloading user info', headers=self._API_HEADERS)['user'])

        user_id = str_or_none(user_info.get('user_id'))
        if not user_id:
            raise ExtractorError('Unable to extract user ID')

        return self.playlist_result(
            self._entries(username, user_id), user_id, username, thumbnail=user_info.get('avatar_url'))


class TrillerShortIE(InfoExtractor):
    _VALID_URL = r'https?://v\.triller\.co/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://v.triller.co/WWZNWk',
        'md5': '5eb8dc2c971bd8cd794ec9e8d5e9d101',
        'info_dict': {
            'id': '66210052',
            'ext': 'mp4',
            'title': 'md5:2dfc89d154cd91a4a18cd9582ba03e16',
            'display_id': 'f4480e1f-fb4e-45b9-a44c-9e6c679ce7eb',
            'thumbnail': r're:^https://uploads\.cdn\.triller\.co/.+\.jpg$',
            'description': 'md5:2dfc89d154cd91a4a18cd9582ba03e16',
            'uploader': 'statefairent',
            'uploader_id': '487545193',
            'creator': 'Official Summer Fair of LA',
            'timestamp': 1629655457,
            'upload_date': '20210822',
            'duration': 19,
            'view_count': int,
            'like_count': int,
            'artist': 'Unknown',
            'track': 'Unknown',
            'uploader_url': 'https://triller.co/@statefairent',
            'comment_count': int,
        },
    }]

    def _real_extract(self, url):
        real_url = self._request_webpage(HEADRequest(url), self._match_id(url)).geturl()
        if self.suitable(real_url):  # Prevent infinite loop in case redirect fails
            raise UnsupportedError(real_url)
        return self.url_result(real_url)
