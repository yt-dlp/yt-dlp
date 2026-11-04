import base64
import json
import random
import re
import time
import urllib.parse

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    float_or_none,
    jwt_decode_hs256,
    parse_qs,
    str_or_none,
    traverse_obj,
    url_or_none,
    urlencode_postdata,
)


class PelotonIE(InfoExtractor):
    IE_NAME = 'peloton'
    _NETRC_MACHINE = 'peloton'
    _VALID_URL = r'https?://members\.onepeloton\.com/classes/player/(?P<id>[a-f0-9]+)'
    _TESTS = [{
        'url': 'https://members.onepeloton.com/classes/player/0e9653eb53544eeb881298c8d7a87b86',
        'info_dict': {
            'id': '0e9653eb53544eeb881298c8d7a87b86',
            'title': '20 min Chest & Back Strength',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.+\.jpg',
            'description': 'md5:fcd5be9b9eda0194b470e13219050a66',
            'creator': 'Chase Tucker',
            'release_timestamp': 1556141400,
            'timestamp': 1556141400,
            'upload_date': '20190424',
            'duration': 1389,
            'categories': ['Strength'],
            'tags': ['Workout Mat', 'Light Weights', 'Medium Weights'],
            'is_live': False,
            'chapters': 'count:1',
            'subtitles': {'en': [{
                'url': r're:^https?://.+',
                'ext': 'vtt',
            }]},
        }, 'params': {
            'skip_download': 'm3u8',
        },
        'skip': 'Account needed',
    }, {
        'url': 'https://members.onepeloton.com/classes/player/26603d53d6bb4de1b340514864a6a6a8',
        'info_dict': {
            'id': '26603d53d6bb4de1b340514864a6a6a8',
            'title': '30 min Earth Day Run',
            'ext': 'm4a',
            'thumbnail': r're:https://.+\.jpg',
            'description': 'md5:adc065a073934d7ee0475d217afe0c3d',
            'creator': 'Selena Samuela',
            'release_timestamp': 1587567600,
            'timestamp': 1587567600,
            'upload_date': '20200422',
            'duration': 1802,
            'categories': ['Running'],
            'is_live': False,
            'chapters': 'count:3',
        }, 'params': {
            'skip_download': 'm3u8',
        },
        'skip': 'Account needed',
    }]

    _MANIFEST_URL_TEMPLATE = '%s?hdnea=%s'
    _LOGIN_BASE_URL = 'https://auth.onepeloton.com'
    _ACCESS_TOKEN = None
    _REFRESH_TOKEN = None
    _CACHE_KEY = 'pelotondata'

    def _start_session(self, video_id):
        self._download_webpage('https://api.onepeloton.com/api/started_client_session', video_id, note='Starting session')

    def random_code_generator(self, length=43):
        valid_char = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_~.'
        return ''.join(random.choice(valid_char) for _ in range(length))

    def _is_jwt_expired(self, token):
        return jwt_decode_hs256(token)['exp'] - time.time() < 300

    def get_cached_access_token(self):
        if self._ACCESS_TOKEN and not self._is_jwt_expired(self._ACCESS_TOKEN):
            return self._ACCESS_TOKEN
        self._ACCESS_TOKEN, self._REFRESH_TOKEN = self.cache.load(self._NETRC_MACHINE, self._CACHE_KEY, default=[None, None])
        if self._ACCESS_TOKEN and self._REFRESH_TOKEN:
            if not self._is_jwt_expired(self._ACCESS_TOKEN):
                return self._ACCESS_TOKEN
            else:
                self.to_screen('Refreshing access token')
                return self.refresh_token()
        return None

    def store_tokens(self, data):
        self._ACCESS_TOKEN = data.get('access_token')
        if not self._ACCESS_TOKEN:
            raise ExtractorError('Unable to login')
        self._REFRESH_TOKEN = data.get('refresh_token')
        self.cache.store(self._NETRC_MACHINE, self._CACHE_KEY, [self._ACCESS_TOKEN, self._REFRESH_TOKEN])
        return self._ACCESS_TOKEN

    def refresh_token(self):
        if not self._REFRESH_TOKEN:
            return self._login(*self._get_login_info())

        data = self._download_json(
            f'{self._LOGIN_BASE_URL}/oauth/token',
            None, 'fetching auth token',
            data=urlencode_postdata({
                'client_id': 'WVoJxVDdPoFx4RNewvvg6ch2mZ7bwnsM',
                'refresh_token': self._REFRESH_TOKEN,
                'grant_type': 'refresh_token',
                'redirect_uri': 'https://members.onepeloton.com/callback',
            }),
        )
        return self.store_tokens(data)

    def fetch_auth_token(self, webpage, auth_url):
        _, urlh = self._download_webpage_handle(
            f'{self._LOGIN_BASE_URL}/login/callback',
            None, 'login callback',
            data=urlencode_postdata({**self._hidden_inputs(webpage)}),
            headers={
                'referer': auth_url,
            },
        )
        code = parse_qs(urlh.url).get('code', [''])
        if not code:
            raise ExtractorError('Unable to login')
        code = code[0]
        data = self._download_json(
            f'{self._LOGIN_BASE_URL}/oauth/token',
            None, 'fetching auth token',
            data=urlencode_postdata({
                'client_id': 'WVoJxVDdPoFx4RNewvvg6ch2mZ7bwnsM',
                'code_verifier': self.random_code_generator(),
                'grant_type': 'authorization_code',
                'redirect_uri': 'https://members.onepeloton.com/callback',
                'code': code,
            }),
        )
        return self.store_tokens(data)

    def _login(self, video_id):
        username, password = self._get_login_info()
        if not (username and password):
            self.raise_login_required()
        if self.get_cached_access_token():
            return

        urlh = self._request_webpage(
            f'{self._LOGIN_BASE_URL}/authorize',
            None, note='Getting required cookies',
            query={
                'client_id': 'WVoJxVDdPoFx4RNewvvg6ch2mZ7bwnsM',  # Source https://members.onepeloton.com/_next/static/chunks/pages/_app-19d8241f56d3ba57.js
                'scope': 'openid offline_access',
                'audience': 'https://api.onepeloton.com/',
                'redirect_uri': 'https://members.onepeloton.com/callback',
                'response_type': 'code',
                'response_mode': 'query',
                'auth0Client': 'eyJuYW1lIjoiYXV0aDAtc3BhLWpzIiwidmVyc2lvbiI6IjIuMS4zIn0=',
            },
            headers={
                'peloton-client-details': 'eyJEZXZpY2UgVHlwZSI6IldlYiIsIkFwcCBWZXJzaW9uIjoiMS4wLjAifQ==',
                'referer': 'https://members.onepeloton.com/',
            },
        )
        auth_url = urlh.url
        state = parse_qs(auth_url).get('state', [''])[0] or base64.urlsafe_b64encode(self.random_code_generator().encode()).decode()
        csrf = self._get_cookies(self._LOGIN_BASE_URL).get('_csrf')
        try:
            data, _ = self._download_webpage_handle(
                'https://auth.onepeloton.com/usernamepassword/login', video_id, note='Logging in',
                data=json.dumps({
                    'password': password,
                    'username': username,
                    'state': state,
                    '_csrf': csrf,
                    'redirect_uri': 'https://members.onepeloton.com/callback',
                    'tenant': 'peloton-prod',
                    '_intstate': 'deprecated',
                    'audience': 'https://api.onepeloton.com/',
                    'client_id': 'WVoJxVDdPoFx4RNewvvg6ch2mZ7bwnsM',
                    'connection': 'pelo-user-password',
                    'response_type': 'code',
                    'scope': 'offline_access openid peloton-api.members:default',
                }).encode(),
                headers={'Content-Type': 'application/json', 'referer': auth_url})
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 401:
                json_string = self._webpage_read_content(e.cause.response, None, video_id)
                res = self._parse_json(json_string, video_id)
                if res['code'] == 'invalid_user_password':
                    raise ExtractorError('Invalid Username/password', expected=True)
                raise ExtractorError(res['message'])
            raise
        return self.fetch_auth_token(data, auth_url)

    def _download_webpage_handle(self, url_or_request, video_id, note=None, **kwargs):
        if self._ACCESS_TOKEN:
            kwargs['headers'] = {'Authorization': f'Bearer {self._ACCESS_TOKEN}'}
        return super()._download_webpage_handle(url_or_request, video_id, note, **kwargs)

    def _get_token(self, video_id):
        try:
            subscription = self._download_json(
                'https://api.onepeloton.com/api/subscription/stream', video_id, note='Downloading token',
                data=json.dumps({}).encode(), headers={'Content-Type': 'application/json'})
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 403:
                json_string = self._webpage_read_content(e.cause.response, None, video_id)
                res = self._parse_json(json_string, video_id)
                raise ExtractorError(res['message'], expected=res['message'] == 'Stream limit reached')
            else:
                raise
        return subscription['token']

    def _real_extract(self, url):
        video_id = self._match_id(url)
        try:
            self._start_session(video_id)
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 401:
                self._login(video_id)
                self._start_session(video_id)
            else:
                raise

        metadata = self._download_json(f'https://api.onepeloton.com/api/ride/{video_id}/details?stream_source=multichannel', video_id)
        ride_data = metadata.get('ride')
        if not ride_data:
            raise ExtractorError('Missing stream metadata')
        token = self._get_token(video_id)

        is_live = False
        if ride_data.get('content_format') == 'audio':
            url = self._MANIFEST_URL_TEMPLATE % (ride_data.get('vod_stream_url'), urllib.parse.quote(token))
            formats = [{
                'url': url,
                'ext': 'm4a',
                'format_id': 'audio',
                'vcodec': 'none',
            }]
            subtitles = {}
        else:
            if ride_data.get('vod_stream_url'):
                url = 'https://members.onepeloton.com/.netlify/functions/m3u8-proxy?displayLanguage=en&acceptedSubtitles={}&url={}?hdnea={}'.format(
                    ','.join([re.sub('^([a-z]+)-([A-Z]+)$', r'\1', caption) for caption in ride_data['captions']]),
                    ride_data['vod_stream_url'],
                    urllib.parse.quote(urllib.parse.quote(token)))
            elif ride_data.get('live_stream_url'):
                url = self._MANIFEST_URL_TEMPLATE % (ride_data.get('live_stream_url'), urllib.parse.quote(token))
                is_live = True
            else:
                raise ExtractorError('Missing video URL')
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(url, video_id, 'mp4')

        if metadata.get('instructor_cues'):
            subtitles['cues'] = [{
                'data': json.dumps(metadata.get('instructor_cues')),
                'ext': 'json',
            }]

        category = ride_data.get('fitness_discipline_display_name')
        chapters = [{
            'start_time': segment.get('start_time_offset'),
            'end_time': segment.get('start_time_offset') + segment.get('length'),
            'title': segment.get('name'),
        } for segment in traverse_obj(metadata, ('segments', 'segment_list'))]

        return {
            'id': video_id,
            'title': ride_data.get('title'),
            'formats': formats,
            'thumbnail': url_or_none(ride_data.get('image_url')),
            'description': str_or_none(ride_data.get('description')),
            'creator': traverse_obj(ride_data, ('instructor', 'name')),
            'release_timestamp': ride_data.get('original_air_time'),
            'timestamp': ride_data.get('original_air_time'),
            'subtitles': subtitles,
            'duration': float_or_none(ride_data.get('length')),
            'categories': [category] if category else None,
            'tags': traverse_obj(ride_data, ('equipment_tags', ..., 'name')),
            'is_live': is_live,
            'chapters': chapters,
        }


class PelotonLiveIE(InfoExtractor):
    IE_NAME = 'peloton:live'
    IE_DESC = 'Peloton Live'
    _VALID_URL = r'https?://members\.onepeloton\.com/player/live/(?P<id>[a-f0-9]+)'
    _TEST = {
        'url': 'https://members.onepeloton.com/player/live/eedee2d19f804a9788f53aa8bd38eb1b',
        'info_dict': {
            'id': '32edc92d28044be5bf6c7b6f1f8d1cbc',
            'title': '30 min HIIT Ride: Live from Home',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.+\.png',
            'description': 'md5:f0d7d8ed3f901b7ee3f62c1671c15817',
            'creator': 'Alex Toussaint',
            'release_timestamp': 1587736620,
            'timestamp': 1587736620,
            'upload_date': '20200424',
            'duration': 2014,
            'categories': ['Cycling'],
            'is_live': False,
            'chapters': 'count:3',
        },
        'params': {
            'skip_download': 'm3u8',
        },
        'skip': 'Account needed',
    }

    def _real_extract(self, url):
        workout_id = self._match_id(url)
        peloton = self._download_json(f'https://api.onepeloton.com/api/peloton/{workout_id}', workout_id)

        if peloton.get('ride_id'):
            if not peloton.get('is_live') or peloton.get('is_encore') or peloton.get('status') != 'PRE_START':
                return self.url_result('https://members.onepeloton.com/classes/player/{}'.format(peloton['ride_id']))
            else:
                raise ExtractorError('Ride has not started', expected=True)
        else:
            raise ExtractorError('Missing video ID')
