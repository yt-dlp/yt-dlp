import itertools
import json
import re
import urllib.parse
from datetime import datetime

from .common import InfoExtractor, SearchInfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    float_or_none,
    format_field,
    int_or_none,
    str_or_none,
    traverse_obj,
    try_get,
    unescapeHTML,
    unified_timestamp,
    url_or_none,
    urlencode_postdata,
)

_API_BASE_URL = 'https://prod-api-v2.production.rokfin.com/api/v2/public/'


class RokfinIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rokfin\.com/(?P<id>(?P<type>post|stream)/\d+)'
    _NETRC_MACHINE = 'rokfin'
    _AUTH_BASE = 'https://secure.rokfin.com/auth/realms/rokfin-web/protocol/openid-connect'
    _access_mgmt_tokens = {}  # OAuth 2.0: RFC 6749, Sec. 1.4-5
    _TESTS = [{
        'url': 'https://www.rokfin.com/post/57548/Mitt-Romneys-Crazy-Solution-To-Climate-Change',
        'info_dict': {
            'id': 'post/57548',
            'ext': 'mp4',
            'title': 'Mitt Romney\'s Crazy Solution To Climate Change',
            'thumbnail': r're:https://img\.production\.rokfin\.com/.+',
            'upload_date': '20211023',
            'timestamp': 1634998029,
            'channel': 'Jimmy Dore',
            'channel_id': 65429,
            'channel_url': 'https://rokfin.com/TheJimmyDoreShow',
            'duration': 213.0,
            'availability': 'public',
            'live_status': 'not_live',
            'dislike_count': int,
            'like_count': int,
        }
    }, {
        'url': 'https://rokfin.com/post/223/Julian-Assange-Arrested-Streaming-In-Real-Time',
        'info_dict': {
            'id': 'post/223',
            'ext': 'mp4',
            'title': 'Julian Assange Arrested: Streaming In Real Time',
            'thumbnail': r're:https://img\.production\.rokfin\.com/.+',
            'upload_date': '20190412',
            'timestamp': 1555052644,
            'channel': 'Ron Placone',
            'channel_id': 10,
            'channel_url': 'https://rokfin.com/RonPlacone',
            'availability': 'public',
            'live_status': 'not_live',
            'dislike_count': int,
            'like_count': int,
            'tags': ['FreeThinkingMedia^', 'RealProgressives^'],
        }
    }, {
        'url': 'https://www.rokfin.com/stream/10543/Its-A-Crazy-Mess-Regional-Director-Blows-Whistle-On-Pfizers-Vaccine-Trial-Data',
        'info_dict': {
            'id': 'stream/10543',
            'ext': 'mp4',
            'title': '"It\'s A Crazy Mess" Regional Director Blows Whistle On Pfizer\'s Vaccine Trial Data',
            'thumbnail': r're:https://img\.production\.rokfin\.com/.+',
            'description': 'md5:324ce2d3e3b62e659506409e458b9d8e',
            'channel': 'Ryan Cristián',
            'channel_id': 53856,
            'channel_url': 'https://rokfin.com/TLAVagabond',
            'availability': 'public',
            'is_live': False,
            'was_live': True,
            'live_status': 'was_live',
            'timestamp': 1635874720,
            'release_timestamp': 1635874720,
            'release_date': '20211102',
            'upload_date': '20211102',
            'dislike_count': int,
            'like_count': int,
            'tags': ['FreeThinkingMedia^'],
        }
    }]

    def _real_extract(self, url):
        video_id, video_type = self._match_valid_url(url).group('id', 'type')
        metadata = self._download_json_using_access_token(f'{_API_BASE_URL}{video_id}', video_id)

        scheduled = unified_timestamp(metadata.get('scheduledAt'))
        live_status = ('was_live' if metadata.get('stoppedAt')
                       else 'is_upcoming' if scheduled
                       else 'is_live' if video_type == 'stream'
                       else 'not_live')

        video_url = traverse_obj(metadata, 'url', ('content', 'contentUrl'), expected_type=url_or_none)
        formats, subtitles = [{'url': video_url}] if video_url else [], {}
        if determine_ext(video_url) == 'm3u8':
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                video_url, video_id, fatal=False, live=live_status == 'is_live')

        if not formats:
            if traverse_obj(metadata, 'premiumPlan', 'premium'):
                self.raise_login_required('This video is only available to premium users', True, method='cookies')
            elif scheduled:
                self.raise_no_formats(
                    f'Stream is offline; sheduled for {datetime.fromtimestamp(scheduled).strftime("%Y-%m-%d %H:%M:%S")}',
                    video_id=video_id, expected=True)
        self._sort_formats(formats)

        uploader = traverse_obj(metadata, ('createdBy', 'username'), ('creator', 'username'))
        timestamp = (scheduled or float_or_none(metadata.get('postedAtMilli'), 1000)
                     or unified_timestamp(metadata.get('creationDateTime')))
        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'title': str_or_none(traverse_obj(metadata, 'title', ('content', 'contentTitle'))),
            'duration': float_or_none(traverse_obj(metadata, ('content', 'duration'))),
            'thumbnail': url_or_none(traverse_obj(metadata, 'thumbnail', ('content', 'thumbnailUrl1'))),
            'description': str_or_none(traverse_obj(metadata, 'description', ('content', 'contentDescription'))),
            'like_count': int_or_none(metadata.get('likeCount')),
            'dislike_count': int_or_none(metadata.get('dislikeCount')),
            'channel': str_or_none(traverse_obj(metadata, ('createdBy', 'name'), ('creator', 'name'))),
            'channel_id': traverse_obj(metadata, ('createdBy', 'id'), ('creator', 'id')),
            'channel_url': url_or_none(f'https://rokfin.com/{uploader}') if uploader else None,
            'timestamp': timestamp,
            'release_timestamp': timestamp if live_status != 'not_live' else None,
            'tags': traverse_obj(metadata, ('tags', ..., 'title'), expected_type=str_or_none),
            'live_status': live_status,
            'availability': self._availability(
                needs_premium=bool(traverse_obj(metadata, 'premiumPlan', 'premium')),
                is_private=False, needs_subscription=False, needs_auth=False, is_unlisted=False),
            # 'comment_count': metadata.get('numComments'), # Data provided by website is wrong
            '__post_extractor': self.extract_comments(video_id) if video_type == 'post' else None,
        }

    def _get_comments(self, video_id):
        pages_total = None
        for page_n in itertools.count():
            raw_comments = self._download_json(
                f'{_API_BASE_URL}comment?postId={video_id[5:]}&page={page_n}&size=50',
                video_id, note=f'Downloading viewer comments page {page_n + 1}{format_field(pages_total, template=" of %s")}',
                fatal=False) or {}

            for comment in raw_comments.get('content') or []:
                yield {
                    'text': str_or_none(comment.get('comment')),
                    'author': str_or_none(comment.get('name')),
                    'id': comment.get('commentId'),
                    'author_id': comment.get('userId'),
                    'parent': 'root',
                    'like_count': int_or_none(comment.get('numLikes')),
                    'dislike_count': int_or_none(comment.get('numDislikes')),
                    'timestamp': unified_timestamp(comment.get('postedAt'))
                }

            pages_total = int_or_none(raw_comments.get('totalPages')) or None
            is_last = raw_comments.get('last')
            if not raw_comments.get('content') or is_last or (page_n > pages_total if pages_total else is_last is not False):
                return

    def _perform_login(self, username, password):
        # https://openid.net/specs/openid-connect-core-1_0.html#CodeFlowAuth (Sec. 3.1)
        login_page = self._download_webpage(
            f'{self._AUTH_BASE}/auth?client_id=web&redirect_uri=https%3A%2F%2Frokfin.com%2Ffeed&response_mode=fragment&response_type=code&scope=openid',
            None, note='loading login page', errnote='error loading login page')
        authentication_point_url = unescapeHTML(self._search_regex(
            r'<form\s+[^>]+action\s*=\s*"(https://secure\.rokfin\.com/auth/realms/rokfin-web/login-actions/authenticate\?[^"]+)"',
            login_page, name='Authentication URL'))

        resp_body = self._download_webpage(
            authentication_point_url, None, note='logging in', fatal=False, expected_status=404,
            data=urlencode_postdata({'username': username, 'password': password, 'rememberMe': 'off', 'credentialId': ''}))
        if not self._authentication_active():
            if re.search(r'(?i)(invalid\s+username\s+or\s+password)', resp_body or ''):
                raise ExtractorError('invalid username/password', expected=True)
            raise ExtractorError('Login failed')

        urlh = self._request_webpage(
            f'{self._AUTH_BASE}/auth', None,
            note='granting user authorization', errnote='user authorization rejected by Rokfin',
            query={
                'client_id': 'web',
                'prompt': 'none',
                'redirect_uri': 'https://rokfin.com/silent-check-sso.html',
                'response_mode': 'fragment',
                'response_type': 'code',
                'scope': 'openid',
            })
        self._access_mgmt_tokens = self._download_json(
            f'{self._AUTH_BASE}/token', None,
            note='getting access credentials', errnote='error getting access credentials',
            data=urlencode_postdata({
                'code': urllib.parse.parse_qs(urllib.parse.urldefrag(urlh.geturl()).fragment).get('code')[0],
                'client_id': 'web',
                'grant_type': 'authorization_code',
                'redirect_uri': 'https://rokfin.com/silent-check-sso.html'
            }))

    def _authentication_active(self):
        return not (
            {'KEYCLOAK_IDENTITY', 'KEYCLOAK_IDENTITY_LEGACY', 'KEYCLOAK_SESSION', 'KEYCLOAK_SESSION_LEGACY'}
            - set(self._get_cookies(self._AUTH_BASE)))

    def _get_auth_token(self):
        return try_get(self._access_mgmt_tokens, lambda x: ' '.join([x['token_type'], x['access_token']]))

    def _download_json_using_access_token(self, url_or_request, video_id, headers={}, query={}):
        assert 'authorization' not in headers
        headers = headers.copy()
        auth_token = self._get_auth_token()
        refresh_token = self._access_mgmt_tokens.get('refresh_token')
        if auth_token:
            headers['authorization'] = auth_token

        json_string, urlh = self._download_webpage_handle(
            url_or_request, video_id, headers=headers, query=query, expected_status=401)
        if not auth_token or urlh.code != 401 or refresh_token is None:
            return self._parse_json(json_string, video_id)

        self._access_mgmt_tokens = self._download_json(
            f'{self._AUTH_BASE}/token', video_id,
            note='User authorization expired or canceled by Rokfin. Re-authorizing ...', errnote='Failed to re-authorize',
            data=urlencode_postdata({
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': 'web'
            }))
        headers['authorization'] = self._get_auth_token()
        if headers['authorization'] is None:
            raise ExtractorError('User authorization lost', expected=True)

        return self._download_json(url_or_request, video_id, headers=headers, query=query)


class RokfinPlaylistBaseIE(InfoExtractor):
    _TYPES = {
        'video': 'post',
        'audio': 'post',
        'stream': 'stream',
        'dead_stream': 'stream',
        'stack': 'stack',
    }

    def _get_video_data(self, metadata):
        for content in metadata.get('content') or []:
            media_type = self._TYPES.get(content.get('mediaType'))
            video_id = content.get('id') if media_type == 'post' else content.get('mediaId')
            if not media_type or not video_id:
                continue

            yield self.url_result(f'https://rokfin.com/{media_type}/{video_id}', video_id=f'{media_type}/{video_id}',
                                  video_title=str_or_none(traverse_obj(content, ('content', 'contentTitle'))))


class RokfinStackIE(RokfinPlaylistBaseIE):
    IE_NAME = 'rokfin:stack'
    IE_DESC = 'Rokfin Stacks'
    _VALID_URL = r'https?://(?:www\.)?rokfin\.com/stack/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://www.rokfin.com/stack/271/Tulsi-Gabbard-Portsmouth-Townhall-FULL--Feb-9-2020',
        'playlist_count': 8,
        'info_dict': {
            'id': '271',
        },
    }]

    def _real_extract(self, url):
        list_id = self._match_id(url)
        return self.playlist_result(self._get_video_data(
            self._download_json(f'{_API_BASE_URL}stack/{list_id}', list_id)), list_id)


class RokfinChannelIE(RokfinPlaylistBaseIE):
    IE_NAME = 'rokfin:channel'
    IE_DESC = 'Rokfin Channels'
    _VALID_URL = r'https?://(?:www\.)?rokfin\.com/(?!((feed/?)|(discover/?)|(channels/?))$)(?P<id>[^/]+)/?$'
    _TESTS = [{
        'url': 'https://rokfin.com/TheConvoCouch',
        'playlist_mincount': 100,
        'info_dict': {
            'id': '12071-new',
            'title': 'TheConvoCouch - New',
            'description': 'md5:bb622b1bca100209b91cd685f7847f06',
        },
    }]

    _TABS = {
        'new': 'posts',
        'top': 'top',
        'videos': 'video',
        'podcasts': 'audio',
        'streams': 'stream',
        'stacks': 'stack',
    }

    def _real_initialize(self):
        self._validate_extractor_args()

    def _validate_extractor_args(self):
        requested_tabs = self._configuration_arg('tab', None)
        if requested_tabs is not None and (len(requested_tabs) > 1 or requested_tabs[0] not in self._TABS):
            raise ExtractorError(f'Invalid extractor-arg "tab". Must be one of {", ".join(self._TABS)}', expected=True)

    def _entries(self, channel_id, channel_name, tab):
        pages_total = None
        for page_n in itertools.count(0):
            if tab in ('posts', 'top'):
                data_url = f'{_API_BASE_URL}user/{channel_name}/{tab}?page={page_n}&size=50'
            else:
                data_url = f'{_API_BASE_URL}post/search/{tab}?page={page_n}&size=50&creator={channel_id}'
            metadata = self._download_json(
                data_url, channel_name,
                note=f'Downloading video metadata page {page_n + 1}{format_field(pages_total, template=" of %s")}')

            yield from self._get_video_data(metadata)
            pages_total = int_or_none(metadata.get('totalPages')) or None
            is_last = metadata.get('last')
            if is_last or (page_n > pages_total if pages_total else is_last is not False):
                return

    def _real_extract(self, url):
        channel_name = self._match_id(url)
        channel_info = self._download_json(f'{_API_BASE_URL}user/{channel_name}', channel_name)
        channel_id = channel_info['id']
        tab = self._configuration_arg('tab', default=['new'])[0]

        return self.playlist_result(
            self._entries(channel_id, channel_name, self._TABS[tab]),
            f'{channel_id}-{tab}', f'{channel_name} - {tab.title()}', str_or_none(channel_info.get('description')))


class RokfinSearchIE(SearchInfoExtractor):
    IE_NAME = 'rokfin:search'
    IE_DESC = 'Rokfin Search'
    _SEARCH_KEY = 'rkfnsearch'
    _TYPES = {
        'video': (('id', 'raw'), 'post'),
        'audio': (('id', 'raw'), 'post'),
        'stream': (('content_id', 'raw'), 'stream'),
        'dead_stream': (('content_id', 'raw'), 'stream'),
        'stack': (('content_id', 'raw'), 'stack'),
    }
    _TESTS = [{
        'url': 'rkfnsearch5:"zelenko"',
        'playlist_count': 5,
        'info_dict': {
            'id': '"zelenko"',
            'title': '"zelenko"',
        }
    }]
    _db_url = None
    _db_access_key = None

    def _real_initialize(self):
        self._db_url, self._db_access_key = self._downloader.cache.load(self.ie_key(), 'auth', default=(None, None))
        if not self._db_url:
            self._get_db_access_credentials()

    def _search_results(self, query):
        total_pages = None
        for page_number in itertools.count(1):
            search_results = self._run_search_query(
                query, data={'query': query, 'page': {'size': 100, 'current': page_number}},
                note=f'Downloading page {page_number}{format_field(total_pages, template=" of ~%s")}')
            total_pages = traverse_obj(search_results, ('meta', 'page', 'total_pages'), expected_type=int_or_none)

            for result in search_results.get('results') or []:
                video_id_key, video_type = self._TYPES.get(traverse_obj(result, ('content_type', 'raw')), (None, None))
                video_id = traverse_obj(result, video_id_key, expected_type=int_or_none)
                if video_id and video_type:
                    yield self.url_result(url=f'https://rokfin.com/{video_type}/{video_id}')
            if not search_results.get('results'):
                return

    def _run_search_query(self, video_id, data, **kwargs):
        data = json.dumps(data).encode()
        for attempt in range(2):
            search_results = self._download_json(
                self._db_url, video_id, data=data, fatal=(attempt == 1),
                headers={'authorization': self._db_access_key}, **kwargs)
            if search_results:
                return search_results
            self.write_debug('Updating access credentials')
            self._get_db_access_credentials(video_id)

    def _get_db_access_credentials(self, video_id=None):
        auth_data = {'SEARCH_KEY': None, 'ENDPOINT_BASE': None}
        notfound_err_page = self._download_webpage(
            'https://rokfin.com/discover', video_id, expected_status=404, note='Downloading home page')
        for js_file_path in re.findall(r'<script\b[^>]*\ssrc\s*=\s*"(/static/js/[^">]+)"', notfound_err_page):
            js_content = self._download_webpage(
                f'https://rokfin.com{js_file_path}', video_id, note='Downloading JavaScript file', fatal=False)
            auth_data.update(re.findall(
                rf'REACT_APP_({"|".join(auth_data.keys())})\s*:\s*"([^"]+)"', js_content or ''))
            if not all(auth_data.values()):
                continue

            self._db_url = url_or_none(f'{auth_data["ENDPOINT_BASE"]}/api/as/v1/engines/rokfin-search/search.json')
            self._db_access_key = f'Bearer {auth_data["SEARCH_KEY"]}'
            self._downloader.cache.store(self.ie_key(), 'auth', (self._db_url, self._db_access_key))
            return
        raise ExtractorError('Unable to extract access credentials')
