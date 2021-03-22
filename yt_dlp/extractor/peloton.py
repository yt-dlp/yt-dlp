# coding: utf-8
from __future__ import unicode_literals

import datetime
import json
import re

from .common import InfoExtractor
from ..compat import (
    compat_HTTPError,
    compat_integer_types,
    compat_str,
    compat_urllib_parse
)
from ..utils import (
    ExtractorError,
    parse_m3u8_attributes,
    try_get
)


class PelotonBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'peloton'

    _SESSION_URL = 'https://api.onepeloton.com/api/started_client_session'
    _LOGIN_URL = 'https://api.onepeloton.com/auth/login'
    _RIDE_URL_TEMPLATE = 'https://api.onepeloton.com/api/ride/%s/details?stream_source=multichannel'
    _SUBSCRIPTION_URL = 'https://api.onepeloton.com/api/subscription/stream'
    _MANIFEST_URL_TEMPLATE = '%s?hdnea=%s'
    _PROXY_TEMPLATE = 'https://members.onepeloton.com/.netlify/functions/m3u8-proxy?displayLanguage=en&acceptedSubtitles=%s&url=%s'

    def _start_session(self, video_id):
        self._download_webpage(self._SESSION_URL, video_id,
                               note='Starting session')

    def _login(self, video_id):
        username, password = self._get_login_info()
        if username and password:
            try:
                self._download_json(self._LOGIN_URL, video_id,
                                    note='Logging in',
                                    data=json.dumps({
                                        'username_or_email': username,
                                        'password': password,
                                        'with_pubsub': False
                                    }).encode(),
                                    headers={
                                        'Content-Type': 'application/json'
                                    })
            except ExtractorError as e:
                if isinstance(e.cause, compat_HTTPError) and e.cause.code == 401:
                    json_string = self._webpage_read_content(e.cause, None, video_id)
                    res = self._parse_json(json_string, video_id)
                    if res['message'] == 'Login failed':
                        raise ExtractorError(res['message'], expected=True)
                    else:
                        raise ExtractorError(res['message'])
                else:
                    raise
        else:
            self.raise_login_required()

    def _get_ride(self, video_id):
        return self._download_json(self._RIDE_URL_TEMPLATE % video_id, video_id)

    def _get_token(self, video_id):
        try:
            subscription = self._download_json(self._SUBSCRIPTION_URL, video_id,
                                               note='Downloading token',
                                               data=json.dumps({}).encode(),
                                               headers={
                                                   'Content-Type': 'application/json'
                                               })
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 403:
                json_string = self._webpage_read_content(e.cause, None, video_id)
                res = self._parse_json(json_string, video_id)
                if res['message'] == 'Stream limit reached':
                    raise ExtractorError(res['message'], expected=True)
                else:
                    raise ExtractorError(res['message'])
            else:
                raise
        return subscription['token']

    def _extract(self, video_id):
        try:
            self._start_session(video_id)
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 401:
                self._login(video_id)
                self._start_session(video_id)
            else:
                raise

        metadata = self._get_ride(video_id)
        if not metadata.get('ride'):
            raise ExtractorError('Missing stream metadata')

        token = self._get_token(video_id)

        is_live = False
        subtitles = {}
        content_format = try_get(metadata, lambda x: x['ride']['content_format'], compat_str) or 'video'
        if content_format == 'audio':
            url = self._MANIFEST_URL_TEMPLATE % (metadata['ride'].get('vod_stream_url'), compat_urllib_parse.quote(token))
            formats = [{
                'url': url,
                'ext': 'm4a',
                'format_id': 'audio',
                'resolution': 'audio only'
            }]
            ext = 'm4a'
        else:
            if metadata['ride'].get('vod_stream_url'):
                url = self._PROXY_TEMPLATE % (
                    ','.join([re.sub('^([a-z]+)-([A-Z]+)$', r'\1', caption) for caption in metadata['ride']['captions']]),
                    self._MANIFEST_URL_TEMPLATE % (
                        metadata['ride']['vod_stream_url'],
                        compat_urllib_parse.quote(compat_urllib_parse.quote(token))))
            elif metadata['ride'].get('live_stream_url'):
                url = self._MANIFEST_URL_TEMPLATE % (metadata['ride'].get('live_stream_url'), compat_urllib_parse.quote(token))
                is_live = True
            else:
                raise ExtractorError('Missing video URL')
            formats = self._extract_m3u8_formats(url, video_id, 'mp4')
            if formats:
                for i, f in enumerate(formats, start=2):
                    if f.get('vcodec') == 'none':
                        f['source_preference'] = -i
                    else:
                        break
                self._sort_formats(formats)
            ext = 'mp4'
            m3u8_doc = self._download_webpage(url, video_id, note='Downloading m3u8', fatal=False)
            if m3u8_doc:
                for line in m3u8_doc.splitlines():
                    if line.startswith('#EXT-X-MEDIA:'):
                        media = parse_m3u8_attributes(line)
                        if media.get('TYPE') == 'SUBTITLES':
                            subtitles.setdefault(media.get('LANGUAGE'), []).append({
                                'url': media.get('URI'),
                                'ext': 'vtt'
                            })

        if metadata.get('instructor_cues'):
            subtitles['cues'] = [{
                'data': json.dumps(metadata.get('instructor_cues')),
                'ext': 'json'
            }]

        release_date = None
        if metadata['ride'].get('original_air_time'):
            release_datetime = datetime.datetime.utcfromtimestamp(metadata['ride'].get('original_air_time'))
            if release_datetime:
                release_date = release_datetime.strftime('%Y%m%d')
        creator = None
        if metadata['ride'].get('instructor') and metadata['ride'].get('instructor').get('name'):
            creator = metadata['ride'].get('instructor').get('name')
        categories = None
        if metadata['ride'].get('fitness_discipline_display_name'):
            categories = [metadata['ride'].get('fitness_discipline_display_name')]
        tags = None
        if metadata['ride'].get('equipment_tags'):
            tags = []
            for equipment in metadata['ride'].get('equipment_tags'):
                if equipment.get('name'):
                    tags.append(equipment.get('name'))
        chapters = None
        if metadata.get('segments') and metadata.get('segments').get('segment_list'):
            chapters = []
            for segment in metadata.get('segments').get('segment_list'):
                if segment.get('start_time_offset') is not None and segment.get('length') and segment.get('name'):
                    chapters.append({
                        'start_time': segment.get('start_time_offset'),
                        'end_time': segment.get('start_time_offset') + segment.get('length'),
                        'title': segment.get('name')
                    })

        return {
            'id': video_id,
            'title': metadata['ride'].get('title'),
            'formats': formats,
            'url': url,
            'manifest_url': url,
            'ext': ext,
            'thumbnail': try_get(metadata, lambda x: x['ride']['image_url'], compat_str),
            'description': try_get(metadata, lambda x: x['ride']['description'], compat_str),
            'creator': creator,
            'release_date': release_date,
            'timestamp': try_get(metadata, lambda x: x['ride']['original_air_time'], compat_integer_types),
            'subtitles': subtitles,
            'duration': try_get(metadata, lambda x: x['ride']['length'], compat_integer_types),
            'categories': categories,
            'tags': tags,
            'is_live': is_live,
            'chapters': chapters
        }


class PelotonIE(PelotonBaseIE):
    IE_NAME = 'peloton'
    IE_DESC = 'Peloton'
    _VALID_URL = r'https?://members\.onepeloton\.com/classes/player/(?P<id>[a-f0-9]+)'
    _TESTS = [{
        'url': 'https://members.onepeloton.com/classes/player/0e9653eb53544eeb881298c8d7a87b86',
        'md5': 'ac6f19feaa852ef78ed999c69e514dc5',
        'info_dict': {
            'id': '0e9653eb53544eeb881298c8d7a87b86',
            'title': '20 min Chest & Back Strength',
            'url': r're:^https?://secure-vh.akamaihd.net/i/vod/btr/04-2019/04242019-chase-530pm-chestback-bbt/04242019-chase-530pm-chestback-bbt_,2,4,6,8,13,20,30,60,00k.mp4.csmil/index_7_av.m3u8',
            'manifest_url': r're:^https?://members.onepeloton.com/.netlify/functions/m3u8-proxy\?displayLanguage=en&acceptedSubtitles=en&url=https?://secure-vh.akamaihd.net/i/vod/btr/04-2019/04242019-chase-530pm-chestback-bbt/04242019-chase-530pm-chestback-bbt_,2,4,6,8,13,20,30,60,00k.mp4.csmil/master.m3u8',
            'ext': 'mp4',
            'thumbnail': 'https://s3.amazonaws.com/peloton-ride-images/9f58244259c46da45e7e0a3491ef0c65005cad97/img_1556145193871.jpg',
            'description': 'Grab your weights and join us for 20 minutes of chest and back work to tone and strengthen your upper body.',
            'creator': 'Chase Tucker',
            'release_date': '20190424',
            'timestamp': 1556141400,
            'upload_date': '20190424',
            'subtitles': {'en': [{
                'url': r're:^https?://secure-vh.akamaihd.net/i/vod/btr/04-2019/04242019-chase-530pm-chestback-bbt/04242019-chase-530pm-chestback-bbt_,2,4,6,8,13,20,30,60,00k.mp4.csmil/index_en_sbtl.m3u8',
                'ext': 'vtt'
            }]},
            'duration': 1389,
            'categories': ['Strength'],
            'tags': ['Workout Mat', 'Light Weights', 'Medium Weights'],
            'is_live': False,
            'chapters': [{
                'start_time': 0,
                'end_time': 1200,
                'title': 'Upper Body'
            }]
        },
        'skip': 'Account needed'
    }, {
        'url': 'https://members.onepeloton.com/classes/player/26603d53d6bb4de1b340514864a6a6a8',
        'md5': 'f0e9ec297fb5a201eeda2186d15f9745',
        'info_dict': {
            'id': '26603d53d6bb4de1b340514864a6a6a8',
            'title': '30 min Earth Day Fun Run',
            'url': r're:^https?://audio-only.mdc.akamaized.net/audio/04-2020/03042020-selena-45m-earthdayfunrun/03042020-selena-45m-earthdayfunrun-192.m4a',
            'manifest_url': r're:^https?://audio-only.mdc.akamaized.net/audio/04-2020/03042020-selena-45m-earthdayfunrun/03042020-selena-45m-earthdayfunrun-192.m4a',
            'ext': 'm4a',
            'thumbnail': 'https://s3.amazonaws.com/peloton-ride-images/04d2dbc888816dff28544c0b4c897d2a1439392e/img_1587061387_cc37b8341fff4c47bbfc23b2f3eb0f8e.jpg',
            'description': 'Celebrate our planet in this 30 min Earth Day Fun Run with Selena! Warm up for 10.5 min before 18.5 min of running and a 1 min cool down.',
            'creator': 'Selena Samuela',
            'release_date': '20200422',
            'timestamp': 1587567600,
            'upload_date': '20200422',
            'subtitles': {},
            'duration': 1802,
            'categories': ['Running'],
            'tags': None,
            'is_live': False,
            'chapters': [{
                'start_time': 0,
                'end_time': 626,
                'title': 'Warmup'
            }, {
                'start_time': 626,
                'end_time': 1740,
                'title': 'Running'
            }, {
                'start_time': 1740,
                'end_time': 1800,
                'title': 'Cool Down'
            }]
        },
        'skip': 'Account needed'
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self._extract(video_id)


class PelotonLiveIE(PelotonBaseIE):
    IE_NAME = 'peloton:live'
    IE_DESC = 'Peloton Live'
    _VALID_URL = r'https?://members\.onepeloton\.com/player/live/(?P<id>[a-f0-9]+)'
    _TEST = {
        'url': 'https://members.onepeloton.com/player/live/eedee2d19f804a9788f53aa8bd38eb1b',
        'md5': '79a501daa93c0d90b5715ffea745831d',
        'info_dict': {
            'id': '32edc92d28044be5bf6c7b6f1f8d1cbc',
            'title': '30 min HIIT Ride: Live from Home',
            'url': r're:^https?://amd-vod.akamaized.net/vod/bike/04-2020/04242020-alex_toussaint-1000am-drastic-2-32edc92d28044be5bf6c7b6f1f8d1cbc/HLS/',
            'manifest_url': r're:^https?://members.onepeloton.com/.netlify/functions/m3u8-proxy\?displayLanguage=en&acceptedSubtitles=&url=https?://amd-vod.akamaized.net/vod/bike/04-2020/04242020-alex_toussaint-1000am-drastic-2-32edc92d28044be5bf6c7b6f1f8d1cbc/HLS/master.m3u8',
            'ext': 'mp4',
            'thumbnail': 'https://s3.amazonaws.com/peloton-ride-images/65fb6f77f5973ca064e9618c43e5f16d56ea56bb/img_1587757866_2f10a87666fd4519ba0c4dbd69730539.png',
            'description': 'Efficient and effective, this intervals-driven class boosts metabolism and gives you a heart-healthy workout leaving you full of energy and confidence.',
            'creator': 'Alex Toussaint',
            'release_date': '20200424',
            'timestamp': 1587736620,
            'upload_date': '20200424',
            'subtitles': {},
            'duration': 2014,
            'categories': ['Cycling'],
            'tags': None,
            'is_live': False,
            'chapters': [{
                'start_time': 0,
                'end_time': 212,
                'title': 'Warmup'
            }, {
                'start_time': 212,
                'end_time': 1738,
                'title': 'Cycling'
            }, {
                'start_time': 1738,
                'end_time': 1800,
                'title': 'Cool Down'
            }]
        },
        'params': {
            'format': 'bestvideo'
        },
        'skip': 'Account needed'
    }

    _PELOTON_URL_TEMPLATE = 'https://api.onepeloton.com/api/peloton/%s'

    def _get_peloton(self, workout_id):
        return self._download_json(self._PELOTON_URL_TEMPLATE % workout_id, None)

    def _real_extract(self, url):
        workout_id = self._match_id(url)
        peloton = self._get_peloton(workout_id)

        if peloton.get('ride_id'):
            if not peloton.get('is_live') or peloton.get('is_encore') or peloton.get('status') != 'PRE_START':
                return self._extract(peloton.get('ride_id'))
            else:
                raise ExtractorError('Ride has not started', expected=True)
        else:
            raise ExtractorError('Missing video ID')
