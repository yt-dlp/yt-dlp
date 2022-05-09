import json
import re

from .common import InfoExtractor
from ..compat import (
    compat_HTTPError,
    compat_urllib_parse,
)
from ..utils import (
    ExtractorError,
    float_or_none,
    str_or_none,
    traverse_obj,
    url_or_none,
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
                'ext': 'vtt'
            }]},
        }, 'params': {
            'skip_download': 'm3u8',
        },
        '_skip': 'Account needed'
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
            'chapters': 'count:3'
        }, 'params': {
            'skip_download': 'm3u8',
        },
        '_skip': 'Account needed'
    }]

    _MANIFEST_URL_TEMPLATE = '%s?hdnea=%s'

    def _start_session(self, video_id):
        self._download_webpage('https://api.onepeloton.com/api/started_client_session', video_id, note='Starting session')

    def _login(self, video_id):
        username, password = self._get_login_info()
        if not (username and password):
            self.raise_login_required()
        try:
            self._download_json(
                'https://api.onepeloton.com/auth/login', video_id, note='Logging in',
                data=json.dumps({
                    'username_or_email': username,
                    'password': password,
                    'with_pubsub': False
                }).encode(),
                headers={'Content-Type': 'application/json', 'User-Agent': 'web'})
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 401:
                json_string = self._webpage_read_content(e.cause, None, video_id)
                res = self._parse_json(json_string, video_id)
                raise ExtractorError(res['message'], expected=res['message'] == 'Login failed')
            else:
                raise

    def _get_token(self, video_id):
        try:
            subscription = self._download_json(
                'https://api.onepeloton.com/api/subscription/stream', video_id, note='Downloading token',
                data=json.dumps({}).encode(), headers={'Content-Type': 'application/json'})
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 403:
                json_string = self._webpage_read_content(e.cause, None, video_id)
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
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 401:
                self._login(video_id)
                self._start_session(video_id)
            else:
                raise

        metadata = self._download_json('https://api.onepeloton.com/api/ride/%s/details?stream_source=multichannel' % video_id, video_id)
        ride_data = metadata.get('ride')
        if not ride_data:
            raise ExtractorError('Missing stream metadata')
        token = self._get_token(video_id)

        is_live = False
        if ride_data.get('content_format') == 'audio':
            url = self._MANIFEST_URL_TEMPLATE % (ride_data.get('vod_stream_url'), compat_urllib_parse.quote(token))
            formats = [{
                'url': url,
                'ext': 'm4a',
                'format_id': 'audio',
                'vcodec': 'none',
            }]
            subtitles = {}
        else:
            if ride_data.get('vod_stream_url'):
                url = 'https://members.onepeloton.com/.netlify/functions/m3u8-proxy?displayLanguage=en&acceptedSubtitles=%s&url=%s?hdnea=%s' % (
                    ','.join([re.sub('^([a-z]+)-([A-Z]+)$', r'\1', caption) for caption in ride_data['captions']]),
                    ride_data['vod_stream_url'],
                    compat_urllib_parse.quote(compat_urllib_parse.quote(token)))
            elif ride_data.get('live_stream_url'):
                url = self._MANIFEST_URL_TEMPLATE % (ride_data.get('live_stream_url'), compat_urllib_parse.quote(token))
                is_live = True
            else:
                raise ExtractorError('Missing video URL')
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(url, video_id, 'mp4')

        if metadata.get('instructor_cues'):
            subtitles['cues'] = [{
                'data': json.dumps(metadata.get('instructor_cues')),
                'ext': 'json'
            }]

        category = ride_data.get('fitness_discipline_display_name')
        chapters = [{
            'start_time': segment.get('start_time_offset'),
            'end_time': segment.get('start_time_offset') + segment.get('length'),
            'title': segment.get('name')
        } for segment in traverse_obj(metadata, ('segments', 'segment_list'))]

        self._sort_formats(formats)
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
            'chapters': chapters
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
            'chapters': 'count:3'
        },
        'params': {
            'skip_download': 'm3u8',
        },
        '_skip': 'Account needed'
    }

    def _real_extract(self, url):
        workout_id = self._match_id(url)
        peloton = self._download_json(f'https://api.onepeloton.com/api/peloton/{workout_id}', workout_id)

        if peloton.get('ride_id'):
            if not peloton.get('is_live') or peloton.get('is_encore') or peloton.get('status') != 'PRE_START':
                return self.url_result('https://members.onepeloton.com/classes/player/%s' % peloton['ride_id'])
            else:
                raise ExtractorError('Ride has not started', expected=True)
        else:
            raise ExtractorError('Missing video ID')
