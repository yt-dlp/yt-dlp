import base64
import hashlib
import hmac
import itertools
import json
import re
import time
import urllib.error
import urllib.parse
import uuid

from .common import InfoExtractor
from .naver import NaverBaseIE
from .youtube import YoutubeIE
from ..utils import (
    ExtractorError,
    UserNotLive,
    float_or_none,
    int_or_none,
    str_or_none,
    traverse_obj,
    try_call,
    update_url_query,
    url_or_none,
)


class WeverseBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'weverse'
    _ACCOUNT_API_BASE = 'https://accountapi.weverse.io/web/api/v2'
    _API_HEADERS = {
        'Referer': 'https://weverse.io/',
        'WEV-device-Id': str(uuid.uuid4()),
    }

    def _perform_login(self, username, password):
        if self._API_HEADERS.get('Authorization'):
            return

        headers = {
            'x-acc-app-secret': '5419526f1c624b38b10787e5c10b2a7a',
            'x-acc-app-version': '2.2.6',
            'x-acc-language': 'en',
            'x-acc-service-id': 'weverse',
            'x-acc-trace-id': str(uuid.uuid4()),
            'x-clog-user-device-id': str(uuid.uuid4()),
        }
        check_username = self._download_json(
            f'{self._ACCOUNT_API_BASE}/signup/email/status', None,
            note='Checking username', query={'email': username}, headers=headers)
        if not check_username.get('hasPassword'):
            raise ExtractorError('Invalid username provided', expected=True)

        headers['content-type'] = 'application/json'
        try:
            auth = self._download_json(
                f'{self._ACCOUNT_API_BASE}/auth/token/by-credentials', None, data=json.dumps({
                    'email': username,
                    'password': password,
                }, separators=(',', ':')).encode(), headers=headers, note='Logging in')
        except ExtractorError as e:
            if isinstance(e.cause, urllib.error.HTTPError) and e.cause.code == 401:
                raise ExtractorError('Invalid password provided', expected=True)
            raise

        WeverseBaseIE._API_HEADERS['Authorization'] = f'Bearer {auth["accessToken"]}'

    def _real_initialize(self):
        if self._API_HEADERS.get('Authorization'):
            return

        token = try_call(lambda: self._get_cookies('https://weverse.io/')['we2_access_token'].value)
        if not token:
            self.raise_login_required()

        WeverseBaseIE._API_HEADERS['Authorization'] = f'Bearer {token}'

    def _call_api(self, ep, video_id, data=None, note='Downloading API JSON'):
        # Ref: https://ssl.pstatic.net/static/wevweb/2_3_2_11101725/public/static/js/2488.a09b41ff.chunk.js
        # From https://ssl.pstatic.net/static/wevweb/2_3_2_11101725/public/static/js/main.e206f7c1.js:
        key = b'1b9cb6378d959b45714bec49971ade22e6e24e42'
        api_path = update_url_query(ep, {
            'appId': 'be4d79eb8fc7bd008ee82c8ec4ff6fd4',
            'language': 'en',
            'platform': 'WEB',
            'wpf': 'pc',
        })
        wmsgpad = int(time.time() * 1000)
        wmd = base64.b64encode(hmac.HMAC(
            key, f'{api_path[:255]}{wmsgpad}'.encode(), digestmod=hashlib.sha1).digest()).decode()
        headers = {'Content-Type': 'application/json'} if data else {}
        try:
            return self._download_json(
                f'https://global.apis.naver.com/weverse/wevweb{api_path}', video_id, note=note,
                data=data, headers={**self._API_HEADERS, **headers}, query={
                    'wmsgpad': wmsgpad,
                    'wmd': wmd,
                })
        except ExtractorError as e:
            if isinstance(e.cause, urllib.error.HTTPError) and e.cause.code == 401:
                self.raise_login_required(
                    'Session token has expired. Log in again or refresh cookies in browser')
            elif isinstance(e.cause, urllib.error.HTTPError) and e.cause.code == 403:
                raise ExtractorError('Your account does not have access to this content', expected=True)
            raise

    def _call_post_api(self, video_id):
        return self._call_api(f'/post/v1.0/post-{video_id}?fieldSet=postV1', video_id)

    def _get_community_id(self, channel):
        return str(self._call_api(
            f'/community/v1.0/communityIdUrlPathByUrlPathArtistCode?keyword={channel}',
            channel, note='Fetching community ID')['communityId'])

    def _get_formats(self, data, video_id):
        formats = traverse_obj(data, ('videos', 'list', lambda _, v: url_or_none(v['source']), {
            'url': 'source',
            'width': ('encodingOption', 'width', {int_or_none}),
            'height': ('encodingOption', 'height', {int_or_none}),
            'vcodec': 'type',
            'vbr': ('bitrate', 'video', {int_or_none}),
            'abr': ('bitrate', 'audio', {int_or_none}),
            'filesize': ('size', {int_or_none}),
            'format_id': ('encodingOption', 'id', {str_or_none}),
        }))

        for stream in traverse_obj(data, ('streams', lambda _, v: v['type'] == 'HLS' and url_or_none(v['source']))):
            query = {}
            for param in traverse_obj(stream, ('keys', lambda _, v: v['type'] == 'param' and v['name'])):
                query[param['name']] = param.get('value', '')
            fmts = self._extract_m3u8_formats(
                stream['source'], video_id, 'mp4', m3u8_id='hls', fatal=False, query=query)
            if query:
                for fmt in fmts:
                    fmt['url'] = update_url_query(fmt['url'], query)
                    fmt['extra_param_to_segment_url'] = urllib.parse.urlencode(query)
            formats.extend(fmts)

        return formats

    def _get_subs(self, caption_url):
        subs_ext_re = r'\.(?:ttml|vtt)'
        replace_ext = lambda x, y: re.sub(subs_ext_re, y, x)
        if re.search(subs_ext_re, caption_url):
            return [replace_ext(caption_url, '.ttml'), replace_ext(caption_url, '.vtt')]
        return [caption_url]

    def _parse_post_meta(self, metadata):
        return traverse_obj(metadata, {
            'title': ((('extension', 'mediaInfo', 'title'), 'title'), {str}),
            'description': ((('extension', 'mediaInfo', 'body'), 'body'), {str}),
            'uploader': ('author', 'profileName', {str}),
            'uploader_id': ('author', 'memberId', {str}),
            'creator': ('community', 'communityName', {str}),
            'channel_id': (('community', 'author'), 'communityId', {str_or_none}),
            'duration': ('extension', 'video', 'playTime', {float_or_none}),
            'timestamp': ('publishedAt', {lambda x: int_or_none(x, 1000)}),
            'release_timestamp': ('extension', 'video', 'onAirStartAt', {lambda x: int_or_none(x, 1000)}),
            'thumbnail': ('extension', (('mediaInfo', 'thumbnail', 'url'), ('video', 'thumb')), {url_or_none}),
            'view_count': ('extension', 'video', 'playCount', {int_or_none}),
            'like_count': ('extension', 'video', 'likeCount', {int_or_none}),
            'comment_count': ('commentCount', {int_or_none}),
        }, get_all=False)

    def _extract_availability(self, data):
        return self._availability(**traverse_obj(data, ((('extension', 'video'), None), {
            'needs_premium': 'paid',
            'needs_subscription': 'membershipOnly',
        }), get_all=False, expected_type=bool), needs_auth=True)

    def _extract_live_status(self, data):
        data = traverse_obj(data, ('extension', 'video', {dict})) or {}
        if data.get('type') == 'LIVE':
            return traverse_obj({
                'ONAIR': 'is_live',
                'DONE': 'post_live',
                'STANDBY': 'is_upcoming',
                'DELAY': 'is_upcoming',
            }, (data.get('status'), {str})) or 'is_live'
        return 'was_live' if data.get('liveToVod') else 'not_live'


class WeverseIE(WeverseBaseIE):
    _VALID_URL = r'https?://(?:www\.|m\.)?weverse.io/(?P<artist>[^/?#]+)/live/(?P<id>[\d-]+)'
    _TESTS = [{
        'url': 'https://weverse.io/billlie/live/0-107323480',
        'md5': '1fa849f00181eef9100d3c8254c47979',
        'info_dict': {
            'id': '0-107323480',
            'ext': 'mp4',
            'title': '행복한 평이루💜',
            'description': '',
            'uploader': 'Billlie',
            'uploader_id': '5ae14aed7b7cdc65fa87c41fe06cc936',
            'channel': 'billlie',
            'channel_id': '72',
            'channel_url': 'https://weverse.io/billlie',
            'creator': 'Billlie',
            'timestamp': 1666262062,
            'upload_date': '20221020',
            'release_timestamp': 1666262058,
            'release_date': '20221020',
            'duration': 3102,
            'thumbnail': r're:^https?://.*\.jpe?g$',
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'availability': 'needs_auth',
            'live_status': 'was_live',
        },
    }, {
        'url': 'https://weverse.io/lesserafim/live/2-102331763',
        'md5': 'e46125c08b13a6c8c1f4565035cca987',
        'info_dict': {
            'id': '2-102331763',
            'ext': 'mp4',
            'title': '🎂김채원 생신🎂',
            'description': '🎂김채원 생신🎂',
            'uploader': 'LE SSERAFIM ',
            'uploader_id': 'd26ddc1e258488a0a2b795218d14d59d',
            'channel': 'lesserafim',
            'channel_id': '47',
            'channel_url': 'https://weverse.io/lesserafim',
            'creator': 'LE SSERAFIM',
            'timestamp': 1659353400,
            'upload_date': '20220801',
            'release_timestamp': 1659353400,
            'release_date': '20220801',
            'duration': 3006,
            'thumbnail': r're:^https?://.*\.jpe?g$',
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'availability': 'needs_auth',
            'live_status': 'was_live',
            'subtitles': {
                'id_ID': 'count:2',
                'en_US': 'count:2',
                'es_ES': 'count:2',
                'vi_VN': 'count:2',
                'th_TH': 'count:2',
                'zh_CN': 'count:2',
                'zh_TW': 'count:2',
                'ja_JP': 'count:2',
                'ko_KR': 'count:2',
            },
        },
    }, {
        'url': 'https://weverse.io/treasure/live/2-117230416',
        'info_dict': {
            'id': '2-117230416',
            'ext': 'mp4',
            'title': r're:스껄도려님 첫 스무살 생파🦋',
            'description': '',
            'uploader': 'TREASURE',
            'uploader_id': '77eabbc449ca37f7970054a136f60082',
            'channel': 'treasure',
            'channel_id': '20',
            'channel_url': 'https://weverse.io/treasure',
            'creator': 'TREASURE',
            'timestamp': 1680667651,
            'upload_date': '20230405',
            'release_timestamp': 1680667639,
            'release_date': '20230405',
            'thumbnail': r're:^https?://.*\.jpe?g$',
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'availability': 'needs_auth',
            'live_status': 'is_live',
        },
        'skip': 'Livestream has ended',
    }]

    def _real_extract(self, url):
        channel, video_id = self._match_valid_url(url).group('artist', 'id')
        post = self._call_post_api(video_id)
        api_video_id = post['extension']['video']['videoId']
        availability = self._extract_availability(post)
        live_status = self._extract_live_status(post)
        video_info, formats = {}, []

        if live_status == 'is_upcoming':
            self.raise_no_formats('Livestream has not yet started', expected=True)

        elif live_status == 'is_live':
            video_info = self._call_api(
                f'/video/v1.0/lives/{api_video_id}/playInfo?preview.format=json&preview.version=v2',
                video_id, note='Downloading live JSON')
            playback = self._parse_json(video_info['lipPlayback'], video_id)
            m3u8_url = traverse_obj(playback, (
                'media', lambda _, v: v['protocol'] == 'HLS', 'path', {url_or_none}), get_all=False)
            formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', m3u8_id='hls', live=True)

        elif live_status == 'post_live':
            if availability in ('premium_only', 'subscriber_only'):
                self.report_drm(video_id)
            self.raise_no_formats(
                'Livestream has ended and downloadable VOD is not available', expected=True)

        else:
            infra_video_id = post['extension']['video']['infraVideoId']
            in_key = self._call_api(
                f'/video/v1.0/vod/{api_video_id}/inKey?preview=false', video_id,
                data=b'{}', note='Downloading VOD API key')['inKey']

            video_info = self._download_json(
                f'https://global.apis.naver.com/rmcnmv/rmcnmv/vod/play/v2.0/{infra_video_id}',
                video_id, note='Downloading VOD JSON', query={
                    'key': in_key,
                    'sid': traverse_obj(post, ('extension', 'video', 'serviceId')) or '2070',
                    'pid': str(uuid.uuid4()),
                    'nonce': int(time.time() * 1000),
                    'devt': 'html5_pc',
                    'prv': 'Y' if post.get('membershipOnly') else 'N',
                    'aup': 'N',
                    'stpb': 'N',
                    'cpl': 'en',
                    'env': 'prod',
                    'lc': 'en',
                    'adi': '[{"adSystem":"null"}]',
                    'adu': '/',
                })

            formats = self._get_formats(video_info, video_id)
            has_drm = traverse_obj(video_info, ('meta', 'provider', 'name', {str.lower})) == 'drm'
            if has_drm and formats:
                self.report_warning(
                    'Requested content is DRM-protected, only a 30-second preview is available', video_id)
            elif has_drm and not formats:
                self.report_drm(video_id)

        return {
            'id': video_id,
            'channel': channel,
            'channel_url': f'https://weverse.io/{channel}',
            'formats': formats,
            'availability': availability,
            'live_status': live_status,
            **self._parse_post_meta(post),
            **NaverBaseIE.process_subtitles(video_info, self._get_subs),
        }


class WeverseMediaIE(WeverseBaseIE):
    _VALID_URL = r'https?://(?:www\.|m\.)?weverse.io/(?P<artist>[^/?#]+)/media/(?P<id>[\d-]+)'
    _TESTS = [{
        'url': 'https://weverse.io/billlie/media/4-116372884',
        'md5': '8efc9cfd61b2f25209eb1a5326314d28',
        'info_dict': {
            'id': 'e-C9wLSQs6o',
            'ext': 'mp4',
            'title': 'Billlie | \'EUNOIA\' Performance Video (heartbeat ver.)',
            'description': 'md5:6181caaf2a2397bca913ffe368c104e5',
            'channel': 'Billlie',
            'channel_id': 'UCyc9sUCxELTDK9vELO5Fzeg',
            'channel_url': 'https://www.youtube.com/channel/UCyc9sUCxELTDK9vELO5Fzeg',
            'uploader': 'Billlie',
            'uploader_id': '@Billlie',
            'uploader_url': 'http://www.youtube.com/@Billlie',
            'upload_date': '20230403',
            'duration': 211,
            'age_limit': 0,
            'playable_in_embed': True,
            'live_status': 'not_live',
            'availability': 'public',
            'view_count': int,
            'comment_count': int,
            'like_count': int,
            'channel_follower_count': int,
            'thumbnail': 'https://i.ytimg.com/vi/e-C9wLSQs6o/maxresdefault.jpg',
            'categories': ['Entertainment'],
            'tags': 'count:7',
        },
    }, {
        'url': 'https://weverse.io/billlie/media/3-102914520',
        'md5': '031551fcbd716bc4f080cb6174a43d8a',
        'info_dict': {
            'id': '3-102914520',
            'ext': 'mp4',
            'title': 'From. SUHYEON🌸',
            'description': 'Billlie 멤버별 독점 영상 공개💙💜',
            'uploader': 'Billlie_official',
            'uploader_id': 'f569c6e92f7eaffef0a395037dcaa54f',
            'channel': 'billlie',
            'channel_id': '72',
            'channel_url': 'https://weverse.io/billlie',
            'creator': 'Billlie',
            'timestamp': 1662174000,
            'upload_date': '20220903',
            'release_timestamp': 1662174000,
            'release_date': '20220903',
            'duration': 17.0,
            'thumbnail': r're:^https?://.*\.jpe?g$',
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'availability': 'needs_auth',
            'live_status': 'not_live',
        },
    }]

    def _real_extract(self, url):
        channel, video_id = self._match_valid_url(url).group('artist', 'id')
        post = self._call_post_api(video_id)
        media_type = traverse_obj(post, ('extension', 'mediaInfo', 'mediaType', {str.lower}))
        youtube_id = traverse_obj(post, ('extension', 'youtube', 'youtubeVideoId', {str}))

        if media_type == 'vod':
            return self.url_result(f'https://weverse.io/{channel}/live/{video_id}', WeverseIE)
        elif media_type == 'youtube' and youtube_id:
            return self.url_result(youtube_id, YoutubeIE)
        elif media_type == 'image':
            self.raise_no_formats('No video content found in webpage', expected=True)
        elif media_type:
            raise ExtractorError(f'Unsupported media type "{media_type}"')

        self.raise_no_formats('No video content found in webpage')


class WeverseMomentIE(WeverseBaseIE):
    _VALID_URL = r'https?://(?:www\.|m\.)?weverse.io/(?P<artist>[^/?#]+)/moment/(?P<uid>[\da-f]+)/post/(?P<id>[\d-]+)'
    _TESTS = [{
        'url': 'https://weverse.io/secretnumber/moment/66a07e164b56a696ee71c99315ffe27b/post/1-117229444',
        'md5': '87733ac19a54081b7dfc2442036d282b',
        'info_dict': {
            'id': '1-117229444',
            'ext': 'mp4',
            'title': '今日もめっちゃいい天気☀️🌤️',
            'uploader': '레아',
            'uploader_id': '66a07e164b56a696ee71c99315ffe27b',
            'channel': 'secretnumber',
            'channel_id': '56',
            'creator': 'SECRET NUMBER',
            'duration': 10,
            'upload_date': '20230405',
            'timestamp': 1680653968,
            'thumbnail': r're:^https?://.*\.jpe?g$',
            'like_count': int,
            'comment_count': int,
            'availability': 'needs_auth',
        },
        'skip': 'Moment has expired',
    }]

    def _real_extract(self, url):
        channel, uploader_id, video_id = self._match_valid_url(url).group('artist', 'uid', 'id')
        post = self._call_post_api(video_id)
        api_video_id = post['extension']['moment']['video']['videoId']
        video_info = self._call_api(
            f'/cvideo/v1.0/cvideo-{api_video_id}/playInfo?videoId={api_video_id}', video_id,
            note='Downloading moment JSON')['playInfo']

        return {
            'id': video_id,
            'channel': channel,
            'uploader_id': uploader_id,
            'formats': self._get_formats(video_info, video_id),
            'availability': self._extract_availability(post),
            **traverse_obj(post, {
                'title': ((('extension', 'moment', 'body'), 'body'), {str}),
                'uploader': ('author', 'profileName', {str}),
                'creator': (('community', 'author'), 'communityName', {str}),
                'channel_id': (('community', 'author'), 'communityId', {str_or_none}),
                'duration': ('extension', 'moment', 'video', 'uploadInfo', 'playTime', {float_or_none}),
                'timestamp': ('publishedAt', {lambda x: int_or_none(x, 1000)}),
                'thumbnail': ('extension', 'moment', 'video', 'uploadInfo', 'imageUrl', {url_or_none}),
                'like_count': ('emotionCount', {int_or_none}),
                'comment_count': ('commentCount', {int_or_none}),
            }, get_all=False),
            **NaverBaseIE.process_subtitles(video_info, self._get_subs),
        }


class WeverseTabBaseIE(WeverseBaseIE):
    _ENDPOINT = None
    _PATH = None
    _QUERY = {}
    _RESULT_IE = None

    def _entries(self, channel_id, channel, first_page):
        query = self._QUERY.copy()

        for page in itertools.count(1):
            posts = first_page if page == 1 else self._call_api(
                update_url_query(self._ENDPOINT % channel_id, query), channel,
                note=f'Downloading {self._PATH} tab page {page}')

            for post in traverse_obj(posts, ('data', lambda _, v: v['postId'])):
                yield self.url_result(
                    f'https://weverse.io/{channel}/{self._PATH}/{post["postId"]}',
                    self._RESULT_IE, post['postId'], **self._parse_post_meta(post),
                    channel=channel, channel_url=f'https://weverse.io/{channel}',
                    availability=self._extract_availability(post),
                    live_status=self._extract_live_status(post))

            query['after'] = traverse_obj(posts, ('paging', 'nextParams', 'after', {str}))
            if not query['after']:
                break

    def _real_extract(self, url):
        channel = self._match_id(url)
        channel_id = self._get_community_id(channel)

        first_page = self._call_api(
            update_url_query(self._ENDPOINT % channel_id, self._QUERY), channel,
            note=f'Downloading {self._PATH} tab page 1')

        return self.playlist_result(
            self._entries(channel_id, channel, first_page), f'{channel}-{self._PATH}',
            **traverse_obj(first_page, ('data', ..., {
                'playlist_title': ('community', 'communityName', {str}),
                'thumbnail': ('author', 'profileImageUrl', {url_or_none}),
            }), get_all=False))


class WeverseLiveTabIE(WeverseTabBaseIE):
    _VALID_URL = r'https?://(?:www\.|m\.)?weverse.io/(?P<id>[^/?#]+)/live/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://weverse.io/billlie/live/',
        'playlist_mincount': 55,
        'info_dict': {
            'id': 'billlie-live',
            'title': 'Billlie',
            'thumbnail': r're:^https?://.*\.jpe?g$',
        },
    }]

    _ENDPOINT = '/post/v1.0/community-%s/liveTabPosts'
    _PATH = 'live'
    _QUERY = {'fieldSet': 'postsV1'}
    _RESULT_IE = WeverseIE


class WeverseMediaTabIE(WeverseTabBaseIE):
    _VALID_URL = r'https?://(?:www\.|m\.)?weverse.io/(?P<id>[^/?#]+)/media(?:/|/all|/new)?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://weverse.io/billlie/media/',
        'playlist_mincount': 231,
        'info_dict': {
            'id': 'billlie-media',
            'title': 'Billlie',
            'thumbnail': r're:^https?://.*\.jpe?g$',
        },
    }, {
        'url': 'https://weverse.io/lesserafim/media/all',
        'only_matching': True,
    }, {
        'url': 'https://weverse.io/lesserafim/media/new',
        'only_matching': True,
    }]

    _ENDPOINT = '/media/v1.0/community-%s/more'
    _PATH = 'media'
    _QUERY = {'fieldSet': 'postsV1', 'filterType': 'RECENT'}
    _RESULT_IE = WeverseMediaIE


class WeverseLiveIE(WeverseBaseIE):
    _VALID_URL = r'https?://(?:www\.|m\.)?weverse.io/(?P<id>[^/?#]+)/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://weverse.io/purplekiss',
        'info_dict': {
            'id': '3-116560493',
            'ext': 'mp4',
            'title': r're:모하냥🫶🏻',
            'description': '내일은 금요일~><',
            'uploader': '채인',
            'uploader_id': '1ffb1d9d904d6b3db2783f876eb9229d',
            'channel': 'purplekiss',
            'channel_id': '35',
            'channel_url': 'https://weverse.io/purplekiss',
            'creator': 'PURPLE KISS',
            'timestamp': 1680780892,
            'upload_date': '20230406',
            'release_timestamp': 1680780883,
            'release_date': '20230406',
            'thumbnail': 'https://weverse-live.pstatic.net/v1.0/live/62044/thumb',
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'availability': 'needs_auth',
            'live_status': 'is_live',
        },
        'skip': 'Livestream has ended',
    }, {
        'url': 'https://weverse.io/billlie/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        channel = self._match_id(url)
        channel_id = self._get_community_id(channel)

        video_id = traverse_obj(
            self._call_api(update_url_query(f'/post/v1.0/community-{channel_id}/liveTab', {
                'debugMessage': 'true',
                'fields': 'onAirLivePosts.fieldSet(postsV1).limit(10),reservedLivePosts.fieldSet(postsV1).limit(10)',
            }), channel, note='Downloading live JSON'), (
                ('onAirLivePosts', 'reservedLivePosts'), 'data',
                lambda _, v: self._extract_live_status(v) in ('is_live', 'is_upcoming'), 'postId', {str}),
            get_all=False)

        if not video_id:
            raise UserNotLive(video_id=channel)

        return self.url_result(f'https://weverse.io/{channel}/live/{video_id}', WeverseIE)
