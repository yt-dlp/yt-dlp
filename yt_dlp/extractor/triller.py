import itertools
import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    str_or_none,
    traverse_obj,
    unified_strdate,
    unified_timestamp,
    url_basename,
)


class TrillerBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'triller'
    _API_BASE_URL = 'https://social.triller.co/v1.5'
    _API_HEADERS = {'Origin': 'https://triller.co'}

    def _perform_login(self, username, password):
        if self._API_HEADERS.get('Authorization'):
            return

        user_check = self._download_json(
            f'{self._API_BASE_URL}/api/user/is-valid-username', None, note='Checking username',
            fatal=False, expected_status=400, headers={
                'Content-Type': 'application/json',
                'Origin': 'https://triller.co',
            }, data=json.dumps({'username': username}, separators=(',', ':')).encode('utf-8'))
        if user_check.get('status'):  # endpoint returns "status":false if username exists
            raise ExtractorError('Unable to login: Invalid username', expected=True)

        credentials = {
            'username': username,
            'password': password,
        }
        login = self._download_json(
            f'{self._API_BASE_URL}/user/auth', None, note='Logging in',
            fatal=False, expected_status=400, headers={
                'Content-Type': 'application/json',
                'Origin': 'https://triller.co',
            }, data=json.dumps(credentials, separators=(',', ':')).encode('utf-8'))
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
        for comment_dict in comment_info['comments']:
            yield {
                'author': traverse_obj(comment_dict, ('author', 'username')),
                'author_id': traverse_obj(comment_dict, ('author', 'user_id')),
                'id': comment_dict.get('id'),
                'text': comment_dict.get('body'),
                'timestamp': unified_timestamp(comment_dict.get('timestamp')),
            }

    def _check_user_info(self, user_info):
        if not user_info:
            self.report_warning('Unable to extract user info')
        elif user_info.get('private') and not user_info.get('followed_by_me'):
            raise ExtractorError('This video is private', expected=True)
        elif traverse_obj(user_info, 'blocked_by_user', 'blocking_user'):
            raise ExtractorError('The author of the video is blocked', expected=True)
        return user_info

    def _parse_video_info(self, video_info, username, user_info=None):
        video_uuid = video_info.get('video_uuid')
        video_id = video_info.get('id')

        formats = []
        video_url = traverse_obj(video_info, 'video_url', 'stream_url')
        if video_url:
            formats.append({
                'url': video_url,
                'ext': 'mp4',
                'vcodec': 'h264',
                'width': video_info.get('width'),
                'height': video_info.get('height'),
                'format_id': url_basename(video_url).split('.')[0],
                'filesize': video_info.get('filesize'),
            })
        video_set = video_info.get('video_set') or []
        for video in video_set:
            resolution = video.get('resolution') or ''
            formats.append({
                'url': video['url'],
                'ext': 'mp4',
                'vcodec': video.get('codec'),
                'vbr': int_or_none(video.get('bitrate'), 1000),
                'width': int_or_none(resolution.split('x')[0]),
                'height': int_or_none(resolution.split('x')[1]),
                'format_id': url_basename(video['url']).split('.')[0],
            })
        audio_url = video_info.get('audio_url')
        if audio_url:
            formats.append({
                'url': audio_url,
                'ext': 'm4a',
                'format_id': url_basename(audio_url).split('.')[0],
            })

        manifest_url = video_info.get('transcoded_url')
        if manifest_url:
            formats.extend(self._extract_m3u8_formats(
                manifest_url, video_id, 'mp4', entry_protocol='m3u8_native',
                m3u8_id='hls', fatal=False))

        comment_count = int_or_none(video_info.get('comment_count'))

        user_info = user_info or traverse_obj(video_info, 'user', default={})

        return {
            'id': str_or_none(video_id) or video_uuid,
            'title': video_info.get('description') or f'Video by {username}',
            'thumbnail': video_info.get('thumbnail_url'),
            'description': video_info.get('description'),
            'uploader': str_or_none(username),
            'uploader_id': str_or_none(user_info.get('user_id')),
            'creator': str_or_none(user_info.get('name')),
            'timestamp': unified_timestamp(video_info.get('timestamp')),
            'upload_date': unified_strdate(video_info.get('timestamp')),
            'duration': int_or_none(video_info.get('duration')),
            'view_count': int_or_none(video_info.get('play_count')),
            'like_count': int_or_none(video_info.get('likes_count')),
            'artist': str_or_none(video_info.get('song_artist')),
            'track': str_or_none(video_info.get('song_title')),
            'webpage_url': f'https://triller.co/@{username}/video/{video_uuid}',
            'uploader_url': f'https://triller.co/@{username}',
            'extractor_key': TrillerIE.ie_key(),
            'extractor': TrillerIE.IE_NAME,
            'formats': formats,
            'comment_count': comment_count,
            '__post_extractor': self.extract_comments(video_id, comment_count),
        }


class TrillerIE(TrillerBaseIE):
    _VALID_URL = r'''(?x)
            https?://(?:www\.)?triller\.co/
            @(?P<username>[\w\._]+)/video/
            (?P<id>[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})
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
            'height': 3840,
            'width': 2160,
            'view_count': int,
            'like_count': int,
            'artist': 'Megan Thee Stallion',
            'track': 'Her',
            'webpage_url': 'https://triller.co/@theestallion/video/2358fcd7-3df2-4c77-84c8-1d091610a6cf',
            'uploader_url': 'https://triller.co/@theestallion',
            'comment_count': int,
        }
    }, {
        'url': 'https://triller.co/@charlidamelio/video/46c6fcfa-aa9e-4503-a50c-68444f44cddc',
        'md5': '874055f462af5b0699b9dbb527a505a0',
        'info_dict': {
            'id': '71621339',
            'ext': 'mp4',
            'title': 'md5:4c91ea82760fe0fffb71b8c3aa7295fc',
            'thumbnail': r're:^https://uploads\.cdn\.triller\.co/.+\.jpg$',
            'description': 'md5:4c91ea82760fe0fffb71b8c3aa7295fc',
            'uploader': 'charlidamelio',
            'uploader_id': '1875551',
            'creator': 'charli damelio',
            'timestamp': 1660773354,
            'upload_date': '20220817',
            'duration': 16,
            'height': 1920,
            'width': 1080,
            'view_count': int,
            'like_count': int,
            'artist': 'Dixie',
            'track': 'Someone to Blame',
            'webpage_url': 'https://triller.co/@charlidamelio/video/46c6fcfa-aa9e-4503-a50c-68444f44cddc',
            'uploader_url': 'https://triller.co/@charlidamelio',
            'comment_count': int,
        }
    }]

    def _real_extract(self, url):
        username, video_uuid = self._match_valid_url(url).group('username', 'id')

        video_info = traverse_obj(self._download_json(
            f'{self._API_BASE_URL}/api/videos/{video_uuid}',
            video_uuid, note='Downloading video info API JSON',
            errnote='Unable to download video info API JSON',
            headers=self._API_HEADERS), ('videos', 0))
        if not video_info:
            raise ExtractorError('No video info found in API response')

        user_info = self._check_user_info(video_info.get('user') or {})
        return self._parse_video_info(video_info, username, user_info)


class TrillerUserIE(TrillerBaseIE):
    _VALID_URL = r'https?://(?:www\.)?triller\.co/@(?P<id>[\w\._]+)/?(?:$|[#?])'
    _TESTS = [{
        # first videos request only returns 2 videos
        'url': 'https://triller.co/@theestallion',
        'playlist_mincount': 9,
        'info_dict': {
            'id': '18992236',
            'title': 'theestallion',
            'thumbnail': r're:^https://uploads\.cdn\.triller\.co/.+\.jpg$',
        }
    }, {
        'url': 'https://triller.co/@charlidamelio',
        'playlist_mincount': 25,
        'info_dict': {
            'id': '1875551',
            'title': 'charlidamelio',
            'thumbnail': r're:^https://uploads\.cdn\.triller\.co/.+\.jpg$',
        }
    }]

    def _real_initialize(self):
        if not self._API_HEADERS.get('Authorization'):
            guest = self._download_json(
                f'{self._API_BASE_URL}/user/create_guest',
                None, note='Creating guest session', data=b'', headers=self._API_HEADERS, query={
                    'platform': 'Web',
                    'app_version': '',
                })
            if not guest.get('auth_token'):
                raise ExtractorError('Unable to fetch required auth token for user extraction')

            self._API_HEADERS['Authorization'] = f'Bearer {guest["auth_token"]}'

    def _extract_video_list(self, username, user_id, limit=6):
        query = {
            'limit': limit,
        }
        for page in itertools.count(1):
            for retry in self.RetryManager():
                try:
                    video_list = self._download_json(
                        f'{self._API_BASE_URL}/api/users/{user_id}/videos',
                        username, note=f'Downloading user video list page {page}',
                        errnote='Unable to download user video list', headers=self._API_HEADERS,
                        query=query)
                except ExtractorError as e:
                    if isinstance(e.cause, json.JSONDecodeError) and e.cause.pos == 0:
                        retry.error = e
                        continue
                    raise
            if not video_list.get('videos'):
                break
            yield from video_list['videos']
            query['before_time'] = traverse_obj(video_list, ('videos', -1, 'timestamp'))
            if not query['before_time']:
                break

    def _entries(self, videos, username, user_info):
        for video in videos:
            yield self._parse_video_info(video, username, user_info)

    def _real_extract(self, url):
        username = self._match_id(url)
        user_info = self._check_user_info(self._download_json(
            f'{self._API_BASE_URL}/api/users/by_username/{username}',
            username, note='Downloading user info',
            errnote='Failed to download user info', headers=self._API_HEADERS).get('user', {}))

        user_id = str_or_none(user_info.get('user_id'))
        videos = self._extract_video_list(username, user_id)
        thumbnail = user_info.get('avatar_url')

        return self.playlist_result(
            self._entries(videos, username, user_info), user_id, username, thumbnail=thumbnail)
