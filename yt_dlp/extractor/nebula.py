# coding: utf-8
from __future__ import unicode_literals

import json
import time

from urllib.error import HTTPError
from .common import InfoExtractor
from ..compat import compat_str, compat_urllib_parse_unquote, compat_urllib_parse_quote
from ..utils import (
    ExtractorError,
    parse_iso8601,
    try_get,
    urljoin,
)


class NebulaIE(InfoExtractor):

    _VALID_URL = r'https?://(?:www\.)?(?:watchnebula\.com|nebula\.app)/videos/(?P<id>[-\w]+)'
    _TESTS = [
        {
            'url': 'https://nebula.app/videos/that-time-disney-remade-beauty-and-the-beast',
            'md5': 'fe79c4df8b3aa2fea98a93d027465c7e',
            'info_dict': {
                'id': '5c271b40b13fd613090034fd',
                'ext': 'mp4',
                'title': 'That Time Disney Remade Beauty and the Beast',
                'description': 'Note: this video was originally posted on YouTube with the sponsor read included. We weren’t able to remove it without reducing video quality, so it’s presented here in its original context.',
                'upload_date': '20180731',
                'timestamp': 1533009600,
                'channel': 'Lindsay Ellis',
                'uploader': 'Lindsay Ellis',
            },
            'params': {
                'usenetrc': True,
            },
            'skip': 'All Nebula content requires authentication',
        },
        {
            'url': 'https://nebula.app/videos/the-logistics-of-d-day-landing-craft-how-the-allies-got-ashore',
            'md5': '6d4edd14ce65720fa63aba5c583fb328',
            'info_dict': {
                'id': '5e7e78171aaf320001fbd6be',
                'ext': 'mp4',
                'title': 'Landing Craft - How The Allies Got Ashore',
                'description': r're:^In this episode we explore the unsung heroes of D-Day, the landing craft.',
                'upload_date': '20200327',
                'timestamp': 1585348140,
                'channel': 'The Logistics of D-Day',
                'uploader': 'The Logistics of D-Day',
            },
            'params': {
                'usenetrc': True,
            },
            'skip': 'All Nebula content requires authentication',
        },
        {
            'url': 'https://nebula.app/videos/money-episode-1-the-draw',
            'md5': '8c7d272910eea320f6f8e6d3084eecf5',
            'info_dict': {
                'id': '5e779ebdd157bc0001d1c75a',
                'ext': 'mp4',
                'title': 'Episode 1: The Draw',
                'description': r'contains:There’s free money on offer… if the players can all work together.',
                'upload_date': '20200323',
                'timestamp': 1584980400,
                'channel': 'Tom Scott Presents: Money',
                'uploader': 'Tom Scott Presents: Money',
            },
            'params': {
                'usenetrc': True,
            },
            'skip': 'All Nebula content requires authentication',
        },
        {
            'url': 'https://watchnebula.com/videos/money-episode-1-the-draw',
            'only_matching': True,
        },
    ]
    _NETRC_MACHINE = 'watchnebula'

    _nebula_token = None

    def _retrieve_nebula_auth(self):
        """
        Log in to Nebula, and returns a Nebula API token
        """

        username, password = self._get_login_info()
        if not (username and password):
            self.raise_login_required()

        self.report_login()
        data = json.dumps({'email': username, 'password': password}).encode('utf8')
        response = self._download_json(
            'https://api.watchnebula.com/api/v1/auth/login/',
            data=data, fatal=False, video_id=None,
            headers={
                'content-type': 'application/json',
                # Submitting the 'sessionid' cookie always causes a 403 on auth endpoint
                'cookie': ''
            },
            note='Authenticating to Nebula with supplied credentials',
            errnote='Authentication failed or rejected')
        if not response or not response.get('key'):
            self.raise_login_required()

        # save nebula token as cookie
        self._set_cookie(
            'nebula.app', 'nebula-auth',
            compat_urllib_parse_quote(
                json.dumps({
                    "apiToken": response["key"],
                    "isLoggingIn": False,
                    "isLoggingOut": False,
                }, separators=(",", ":"))),
            expire_time=int(time.time()) + 86400 * 365,
        )

        return response['key']

    def _retrieve_zype_api_key(self, page_url, display_id):
        """
        Retrieves the Zype API key
        """

        # Find the js that has the API key from the webpage and download it
        webpage = self._download_webpage(page_url, video_id=display_id)
        main_script_relpath = self._search_regex(
            r'<script[^>]*src="(?P<script_relpath>[^"]*main.[0-9a-f]*.chunk.js)"[^>]*>', webpage,
            group='script_relpath', name='script relative path', fatal=True)
        main_script_abspath = urljoin(page_url, main_script_relpath)
        main_script = self._download_webpage(main_script_abspath, video_id=display_id,
                                             note='Retrieving Zype API key')

        api_key = self._search_regex(
            r'REACT_APP_ZYPE_API_KEY\s*:\s*"(?P<api_key>[\w-]*)"', main_script,
            group='api_key', name='API key', fatal=True)

        return api_key

    def _call_zype_api(self, path, params, video_id, api_key, note):
        """
        A helper for making calls to the Zype API.
        """
        query = {'api_key': api_key, 'per_page': 1}
        query.update(params)
        return self._download_json('https://api.zype.com' + path, video_id, query=query, note=note)

    def _call_nebula_api(self, path, video_id, access_token, note):
        """
        A helper for making calls to the Nebula API.
        """
        return self._download_json('https://api.watchnebula.com/api/v1' + path, video_id, headers={
            'Authorization': 'Token {access_token}'.format(access_token=access_token)
        }, note=note)

    def _fetch_zype_access_token(self, video_id):
        try:
            user_object = self._call_nebula_api('/auth/user/', video_id, self._nebula_token, note='Retrieving Zype access token')
        except ExtractorError as exc:
            # if 401, attempt credential auth and retry
            if exc.cause and isinstance(exc.cause, HTTPError) and exc.cause.code == 401:
                self._nebula_token = self._retrieve_nebula_auth()
                user_object = self._call_nebula_api('/auth/user/', video_id, self._nebula_token, note='Retrieving Zype access token')
            else:
                raise

        access_token = try_get(user_object, lambda x: x['zype_auth_info']['access_token'], compat_str)
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

    def _extract_channel_title(self, video_meta):
        # TODO: Implement the API calls giving us the channel list,
        # so that we can do the title lookup and then figure out the channel URL
        categories = video_meta.get('categories', []) if video_meta else []
        # the channel name is the value of the first category
        for category in categories:
            if category.get('value'):
                return category['value'][0]

    def _real_initialize(self):
        # check cookie jar for valid token
        nebula_cookies = self._get_cookies('https://nebula.app')
        nebula_cookie = nebula_cookies.get('nebula-auth')
        if nebula_cookie:
            self.to_screen('Authenticating to Nebula with token from cookie jar')
            nebula_cookie_value = compat_urllib_parse_unquote(nebula_cookie.value)
            self._nebula_token = self._parse_json(nebula_cookie_value, None).get('apiToken')

        # try to authenticate using credentials if no valid token has been found
        if not self._nebula_token:
            self._nebula_token = self._retrieve_nebula_auth()

    def _real_extract(self, url):
        display_id = self._match_id(url)
        api_key = self._retrieve_zype_api_key(url, display_id)

        response = self._call_zype_api('/videos', {'friendly_title': display_id},
                                       display_id, api_key, note='Retrieving metadata from Zype')
        if len(response.get('response') or []) != 1:
            raise ExtractorError('Unable to find video on Zype API')
        video_meta = response['response'][0]

        video_id = video_meta['_id']
        zype_access_token = self._fetch_zype_access_token(display_id)

        channel_title = self._extract_channel_title(video_meta)

        return {
            'id': video_id,
            'display_id': display_id,
            '_type': 'url_transparent',
            'ie_key': 'Zype',
            'url': 'https://player.zype.com/embed/%s.html?access_token=%s' % (video_id, zype_access_token),
            'title': video_meta.get('title'),
            'description': video_meta.get('description'),
            'timestamp': parse_iso8601(video_meta.get('published_at')),
            'thumbnails': [{
                'id': tn.get('name'),  # this appears to be null
                'url': tn['url'],
                'width': tn.get('width'),
                'height': tn.get('height'),
            } for tn in video_meta.get('thumbnails', [])],
            'duration': video_meta.get('duration'),
            'channel': channel_title,
            'uploader': channel_title,  # we chose uploader = channel name
            # TODO: uploader_url, channel_id, channel_url
        }
