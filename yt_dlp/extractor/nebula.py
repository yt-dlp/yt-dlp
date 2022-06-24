import itertools
import json
import time
import urllib.error
import urllib.parse

from .common import InfoExtractor
from ..utils import ExtractorError, parse_iso8601, try_get


class NebulaBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'watchnebula'

    _nebula_api_token = None
    _nebula_bearer_token = None
    _zype_access_token = None

    def _perform_nebula_auth(self, username, password):
        if not username or not password:
            self.raise_login_required()

        data = json.dumps({'email': username, 'password': password}).encode('utf8')
        response = self._download_json(
            'https://api.watchnebula.com/api/v1/auth/login/',
            data=data, fatal=False, video_id=None,
            headers={
                'content-type': 'application/json',
                # Submitting the 'sessionid' cookie always causes a 403 on auth endpoint
                'cookie': ''
            },
            note='Logging in to Nebula with supplied credentials',
            errnote='Authentication failed or rejected')
        if not response or not response.get('key'):
            self.raise_login_required()

        # save nebula token as cookie
        self._set_cookie(
            'nebula.app', 'nebula-auth',
            urllib.parse.quote(
                json.dumps({
                    "apiToken": response["key"],
                    "isLoggingIn": False,
                    "isLoggingOut": False,
                }, separators=(",", ":"))),
            expire_time=int(time.time()) + 86400 * 365,
        )

        return response['key']

    def _retrieve_nebula_api_token(self, username=None, password=None):
        """
        Check cookie jar for valid token. Try to authenticate using credentials if no valid token
        can be found in the cookie jar.
        """
        nebula_cookies = self._get_cookies('https://nebula.app')
        nebula_cookie = nebula_cookies.get('nebula-auth')
        if nebula_cookie:
            self.to_screen('Authenticating to Nebula with token from cookie jar')
            nebula_cookie_value = urllib.parse.unquote(nebula_cookie.value)
            nebula_api_token = self._parse_json(nebula_cookie_value, None).get('apiToken')
            if nebula_api_token:
                return nebula_api_token

        return self._perform_nebula_auth(username, password)

    def _call_nebula_api(self, url, video_id=None, method='GET', auth_type='api', note=''):
        assert method in ('GET', 'POST',)
        assert auth_type in ('api', 'bearer',)

        def inner_call():
            authorization = f'Token {self._nebula_api_token}' if auth_type == 'api' else f'Bearer {self._nebula_bearer_token}'
            return self._download_json(
                url, video_id, note=note, headers={'Authorization': authorization},
                data=b'' if method == 'POST' else None)

        try:
            return inner_call()
        except ExtractorError as exc:
            # if 401 or 403, attempt credential re-auth and retry
            if exc.cause and isinstance(exc.cause, urllib.error.HTTPError) and exc.cause.code in (401, 403):
                self.to_screen(f'Reauthenticating to Nebula and retrying, because last {auth_type} call resulted in error {exc.cause.code}')
                self._perform_login()
                return inner_call()
            else:
                raise

    def _fetch_nebula_bearer_token(self):
        """
        Get a Bearer token for the Nebula API. This will be required to fetch video meta data.
        """
        response = self._call_nebula_api('https://api.watchnebula.com/api/v1/authorization/',
                                         method='POST',
                                         note='Authorizing to Nebula')
        return response['token']

    def _fetch_zype_access_token(self):
        """
        Get a Zype access token, which is required to access video streams -- in our case: to
        generate video URLs.
        """
        user_object = self._call_nebula_api('https://api.watchnebula.com/api/v1/auth/user/', note='Retrieving Zype access token')

        access_token = try_get(user_object, lambda x: x['zype_auth_info']['access_token'], str)
        if not access_token:
            if try_get(user_object, lambda x: x['is_subscribed'], bool):
                # TODO: Reimplement the same Zype token polling the Nebula frontend implements
                # see https://github.com/ytdl-org/youtube-dl/pull/24805#issuecomment-749231532
                raise ExtractorError(
                    'Unable to extract Zype access token from Nebula API authentication endpoint. '
                    'Open an arbitrary video in a browser with this account to generate a token',
                    expected=True)
            raise ExtractorError('Unable to extract Zype access token from Nebula API authentication endpoint')
        return access_token

    def _build_video_info(self, episode):
        zype_id = episode['zype_id']
        zype_video_url = f'https://player.zype.com/embed/{zype_id}.html?access_token={self._zype_access_token}'
        channel_slug = episode['channel_slug']
        return {
            'id': episode['zype_id'],
            'display_id': episode['slug'],
            '_type': 'url_transparent',
            'ie_key': 'Zype',
            'url': zype_video_url,
            'title': episode['title'],
            'description': episode['description'],
            'timestamp': parse_iso8601(episode['published_at']),
            'thumbnails': [{
                # 'id': tn.get('name'),  # this appears to be null
                'url': tn['original'],
                'height': key,
            } for key, tn in episode['assets']['thumbnail'].items()],
            'duration': episode['duration'],
            'channel': episode['channel_title'],
            'channel_id': channel_slug,
            'channel_url': f'https://nebula.app/{channel_slug}',
            'uploader': episode['channel_title'],
            'uploader_id': channel_slug,
            'uploader_url': f'https://nebula.app/{channel_slug}',
            'series': episode['channel_title'],
            'creator': episode['channel_title'],
        }

    def _perform_login(self, username=None, password=None):
        self._nebula_api_token = self._retrieve_nebula_api_token(username, password)
        self._nebula_bearer_token = self._fetch_nebula_bearer_token()
        self._zype_access_token = self._fetch_zype_access_token()


class NebulaIE(NebulaBaseIE):
    _VALID_URL = r'https?://(?:www\.)?(?:watchnebula\.com|nebula\.app)/videos/(?P<id>[-\w]+)'
    _TESTS = [
        {
            'url': 'https://nebula.app/videos/that-time-disney-remade-beauty-and-the-beast',
            'md5': '14944cfee8c7beeea106320c47560efc',
            'info_dict': {
                'id': '5c271b40b13fd613090034fd',
                'ext': 'mp4',
                'title': 'That Time Disney Remade Beauty and the Beast',
                'description': 'Note: this video was originally posted on YouTube with the sponsor read included. We weren’t able to remove it without reducing video quality, so it’s presented here in its original context.',
                'upload_date': '20180731',
                'timestamp': 1533009600,
                'channel': 'Lindsay Ellis',
                'channel_id': 'lindsayellis',
                'uploader': 'Lindsay Ellis',
                'uploader_id': 'lindsayellis',
                'timestamp': 1533009600,
                'uploader_url': 'https://nebula.app/lindsayellis',
                'series': 'Lindsay Ellis',
                'average_rating': int,
                'display_id': 'that-time-disney-remade-beauty-and-the-beast',
                'channel_url': 'https://nebula.app/lindsayellis',
                'creator': 'Lindsay Ellis',
                'duration': 2212,
                'view_count': int,
                'thumbnail': r're:https://\w+\.cloudfront\.net/[\w-]+\.jpeg?.*',
            },
        },
        {
            'url': 'https://nebula.app/videos/the-logistics-of-d-day-landing-craft-how-the-allies-got-ashore',
            'md5': 'd05739cf6c38c09322422f696b569c23',
            'info_dict': {
                'id': '5e7e78171aaf320001fbd6be',
                'ext': 'mp4',
                'title': 'Landing Craft - How The Allies Got Ashore',
                'description': r're:^In this episode we explore the unsung heroes of D-Day, the landing craft.',
                'upload_date': '20200327',
                'timestamp': 1585348140,
                'channel': 'Real Engineering',
                'channel_id': 'realengineering',
                'uploader': 'Real Engineering',
                'uploader_id': 'realengineering',
                'view_count': int,
                'series': 'Real Engineering',
                'average_rating': int,
                'display_id': 'the-logistics-of-d-day-landing-craft-how-the-allies-got-ashore',
                'creator': 'Real Engineering',
                'duration': 841,
                'channel_url': 'https://nebula.app/realengineering',
                'uploader_url': 'https://nebula.app/realengineering',
                'thumbnail': r're:https://\w+\.cloudfront\.net/[\w-]+\.jpeg?.*',
            },
        },
        {
            'url': 'https://nebula.app/videos/money-episode-1-the-draw',
            'md5': 'ebe28a7ad822b9ee172387d860487868',
            'info_dict': {
                'id': '5e779ebdd157bc0001d1c75a',
                'ext': 'mp4',
                'title': 'Episode 1: The Draw',
                'description': r'contains:There’s free money on offer… if the players can all work together.',
                'upload_date': '20200323',
                'timestamp': 1584980400,
                'channel': 'Tom Scott Presents: Money',
                'channel_id': 'tom-scott-presents-money',
                'uploader': 'Tom Scott Presents: Money',
                'uploader_id': 'tom-scott-presents-money',
                'uploader_url': 'https://nebula.app/tom-scott-presents-money',
                'duration': 825,
                'channel_url': 'https://nebula.app/tom-scott-presents-money',
                'view_count': int,
                'series': 'Tom Scott Presents: Money',
                'display_id': 'money-episode-1-the-draw',
                'thumbnail': r're:https://\w+\.cloudfront\.net/[\w-]+\.jpeg?.*',
                'average_rating': int,
                'creator': 'Tom Scott Presents: Money',
            },
        },
        {
            'url': 'https://watchnebula.com/videos/money-episode-1-the-draw',
            'only_matching': True,
        },
    ]

    def _fetch_video_metadata(self, slug):
        return self._call_nebula_api(f'https://content.watchnebula.com/video/{slug}/',
                                     video_id=slug,
                                     auth_type='bearer',
                                     note='Fetching video meta data')

    def _real_extract(self, url):
        slug = self._match_id(url)
        video = self._fetch_video_metadata(slug)
        return self._build_video_info(video)


class NebulaSubscriptionsIE(NebulaBaseIE):
    IE_NAME = 'nebula:subscriptions'
    _VALID_URL = r'https?://(?:www\.)?(?:watchnebula\.com|nebula\.app)/myshows'
    _TESTS = [
        {
            'url': 'https://nebula.app/myshows',
            'playlist_mincount': 1,
            'info_dict': {
                'id': 'myshows',
            },
        },
    ]

    def _generate_playlist_entries(self):
        next_url = 'https://content.watchnebula.com/library/video/?page_size=100'
        page_num = 1
        while next_url:
            channel = self._call_nebula_api(next_url, 'myshows', auth_type='bearer',
                                            note=f'Retrieving subscriptions page {page_num}')
            for episode in channel['results']:
                yield self._build_video_info(episode)
            next_url = channel['next']
            page_num += 1

    def _real_extract(self, url):
        return self.playlist_result(self._generate_playlist_entries(), 'myshows')


class NebulaChannelIE(NebulaBaseIE):
    IE_NAME = 'nebula:channel'
    _VALID_URL = r'https?://(?:www\.)?(?:watchnebula\.com|nebula\.app)/(?!myshows|videos/)(?P<id>[-\w]+)'
    _TESTS = [
        {
            'url': 'https://nebula.app/tom-scott-presents-money',
            'info_dict': {
                'id': 'tom-scott-presents-money',
                'title': 'Tom Scott Presents: Money',
                'description': 'Tom Scott hosts a series all about trust, negotiation and money.',
            },
            'playlist_count': 5,
        }, {
            'url': 'https://nebula.app/lindsayellis',
            'info_dict': {
                'id': 'lindsayellis',
                'title': 'Lindsay Ellis',
                'description': 'Enjoy these hottest of takes on Disney, Transformers, and Musicals.',
            },
            'playlist_mincount': 100,
        },
    ]

    def _generate_playlist_entries(self, collection_id, channel):
        episodes = channel['episodes']['results']
        for page_num in itertools.count(2):
            for episode in episodes:
                yield self._build_video_info(episode)
            next_url = channel['episodes']['next']
            if not next_url:
                break
            channel = self._call_nebula_api(next_url, collection_id, auth_type='bearer',
                                            note=f'Retrieving channel page {page_num}')
            episodes = channel['episodes']['results']

    def _real_extract(self, url):
        collection_id = self._match_id(url)
        channel_url = f'https://content.watchnebula.com/video/channels/{collection_id}/'
        channel = self._call_nebula_api(channel_url, collection_id, auth_type='bearer', note='Retrieving channel')
        channel_details = channel['details']

        return self.playlist_result(
            entries=self._generate_playlist_entries(collection_id, channel),
            playlist_id=collection_id,
            playlist_title=channel_details['title'],
            playlist_description=channel_details['description']
        )
