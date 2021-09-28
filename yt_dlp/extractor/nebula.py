# coding: utf-8
from __future__ import unicode_literals

import json
import time

from urllib.error import HTTPError
from .common import InfoExtractor
from ..compat import compat_str, compat_urllib_parse_unquote, compat_urllib_parse_quote, compat_urllib_request
from ..utils import (
    ExtractorError,
    parse_iso8601,
    try_get,
)


class NebulaBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'watchnebula'

    _nebula_api_token = None
    _nebula_bearer_token = None
    _zype_access_token = None

    def _retrieve_nebula_auth(self):
        username, password = self._get_login_info()
        if not (username and password):
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
            compat_urllib_parse_quote(
                json.dumps({
                    "apiToken": response["key"],
                    "isLoggingIn": False,
                    "isLoggingOut": False,
                }, separators=(",", ":"))),
            expire_time=int(time.time()) + 86400 * 365,
        )

        return response['key']

    def _call_nebula_api(self, url, video_id=None, method='GET', auth_type='api', note=''):
        assert method in ('GET', 'POST',)
        assert auth_type in ('api', 'bearer',)
        authorization = 'Token {api_token}'.format(api_token=self._nebula_api_token) \
            if auth_type == 'api' \
            else 'Bearer {bearer_token}'.format(bearer_token=self._nebula_bearer_token)
        url_or_request = url \
            if method == 'GET' \
            else compat_urllib_request.Request(url, method='POST', data={})
        return self._download_json(url_or_request, video_id, headers={'Authorization': authorization}, note=note)

    def _fetch_zype_access_token(self):
        try:
            user_object = self._call_nebula_api('https://api.watchnebula.com/api/v1/auth/user/', note='Retrieving Zype access token')
        except ExtractorError as exc:
            # if 401, attempt credential auth and retry
            if exc.cause and isinstance(exc.cause, HTTPError) and exc.cause.code == 401:
                self._nebula_api_token = self._retrieve_nebula_auth()
                user_object = self._call_nebula_api('https://api.watchnebula.com/api/v1/auth/user/', note='Retrieving Zype access token')
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

    def _fetch_nebula_bearer_token(self):
        response = self._call_nebula_api('https://api.watchnebula.com/api/v1/authorization/',
                                         method='POST',
                                         note='Authorizing to Nebula')
        return response['token']

    def _build_video_info(self, episode):
        zype_video_url = 'https://player.zype.com/embed/%s.html?access_token=%s' % (episode['zype_id'], self._zype_access_token)
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
            'channel_id': episode['channel_slug'],
            'channel_url': 'https://nebula.app/{channel_slug}'.format(channel_slug=episode['channel_slug']),
            'uploader': episode['channel_title'],
            'uploader_id': episode['channel_slug'],
            'uploader_url': 'https://nebula.app/{channel_slug}'.format(channel_slug=episode['channel_slug']),
            'series': episode['channel_title'],
            'creator': episode['channel_title'],
        }

    def _real_initialize(self):
        # check cookie jar for valid token
        nebula_cookies = self._get_cookies('https://nebula.app')
        nebula_cookie = nebula_cookies.get('nebula-auth')
        if nebula_cookie:
            self.to_screen('Authenticating to Nebula with token from cookie jar')
            nebula_cookie_value = compat_urllib_parse_unquote(nebula_cookie.value)
            self._nebula_api_token = self._parse_json(nebula_cookie_value, None).get('apiToken')

        # try to authenticate using credentials if no valid token has been found
        if not self._nebula_api_token:
            self._nebula_api_token = self._retrieve_nebula_auth()

        # get a Bearer token for the Nebula API, that we need to fetch meta data
        self._nebula_bearer_token = self._fetch_nebula_bearer_token()

        # get a Zype access token which is required to access video streams (for us: to generate video URLs)
        self._zype_access_token = self._fetch_zype_access_token()


class NebulaIE(NebulaBaseIE):
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
                'channel_id': 'lindsayellis',
                'uploader': 'Lindsay Ellis',
                'uploader_id': 'lindsayellis',
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
                'channel': 'Real Engineering',
                'channel_id': 'realengineering',
                'uploader': 'Real Engineering',
                'uploader_id': 'realengineering',
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
                'channel_id': 'tom-scott-presents-money',
                'uploader': 'Tom Scott Presents: Money',
                'uploader_id': 'tom-scott-presents-money',
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

    def _fetch_video_metadata(self, slug):
        return self._call_nebula_api('https://content.watchnebula.com/video/{slug}/'.format(slug=slug),
                                     video_id=slug,
                                     auth_type='bearer',
                                     note='Fetching video meta data')

    def _real_extract(self, url):
        slug = self._match_id(url)
        video = self._fetch_video_metadata(slug)
        return self._build_video_info(video)


class NebulaCollectionIE(NebulaBaseIE):
    IE_NAME = 'nebula:collection'
    _VALID_URL = r'https?://(?:www\.)?(?:watchnebula\.com|nebula\.app)/(?P<id>[-\w]+)'
    _TESTS = [
        {
            'url': 'https://nebula.app/tom-scott-presents-money',
            'info_dict': {
                'id': 'tom-scott-presents-money',
                'title': 'Tom Scott Presents: Money',
                'description': 'Tom Scott hosts a series all about trust, negotiation and money.',
            },
            'playlist_count': 5,
            'params': {
                'usenetrc': True,
            },
            'skip': 'All Nebula content requires authentication',
        }, {
            'url': 'https://nebula.app/lindsayellis',
            'info_dict': {
                'id': 'lindsayellis',
                'title': 'Lindsay Ellis',
                'description': 'Enjoy these hottest of takes on Disney, Transformers, and Musicals.',
            },
            'playlist_mincount': 100,
            'params': {
                'usenetrc': True,
            },
            'skip': 'All Nebula content requires authentication',
        },
    ]

    def _fetch_collection(self, collection_id):
        page_nr = 1
        next_url = 'https://content.watchnebula.com/video/channels/{collection_id}/'.format(collection_id=collection_id)
        episodes = []
        channel_details = None
        while next_url:
            channel = self._call_nebula_api(next_url, collection_id, auth_type='bearer',
                                            note='Retrieving channel page {page_nr}'.format(page_nr=page_nr))
            if not channel_details:
                channel_details = channel['details']
            episodes.extend(channel['episodes']['results'])
            next_url = channel['episodes']['next']
            page_nr += 1

        return channel_details, episodes

    def _real_extract(self, url):
        collection_id = self._match_id(url)
        channel_details, episodes = self._fetch_collection(collection_id)

        return self.playlist_result(
            entries=[
                self._build_video_info(episode) for episode in episodes
            ],
            playlist_id=collection_id,
            playlist_title=channel_details['title'],
            playlist_description=channel_details['description']
        )
