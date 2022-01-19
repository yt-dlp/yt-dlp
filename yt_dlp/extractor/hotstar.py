# coding: utf-8
from __future__ import unicode_literals

import hashlib
import hmac
import re
import time
import uuid
import json

from .common import InfoExtractor
from ..compat import (
    compat_HTTPError,
    compat_str
)
from ..utils import (
    determine_ext,
    ExtractorError,
    int_or_none,
    str_or_none,
    try_get,
    url_or_none,
)


class HotStarBaseIE(InfoExtractor):
    _AKAMAI_ENCRYPTION_KEY = b'\x05\xfc\x1a\x01\xca\xc9\x4b\xc4\x12\xfc\x53\x12\x07\x75\xf9\xee'

    def _call_api_impl(self, path, video_id, query, st=None, cookies=None):
        st = int_or_none(st) or int(time.time())
        exp = st + 6000
        auth = 'st=%d~exp=%d~acl=/*' % (st, exp)
        auth += '~hmac=' + hmac.new(self._AKAMAI_ENCRYPTION_KEY, auth.encode(), hashlib.sha256).hexdigest()

        if cookies and cookies.get('userUP'):
            token = cookies.get('userUP').value
        else:
            token = self._download_json(
                'https://api.hotstar.com/um/v3/users',
                video_id, note='Downloading token',
                data=json.dumps({"device_ids": [{"id": compat_str(uuid.uuid4()), "type": "device_id"}]}).encode('utf-8'),
                headers={
                    'hotstarauth': auth,
                    'x-hs-platform': 'PCTV',  # or 'web'
                    'Content-Type': 'application/json',
                })['user_identity']

        response = self._download_json(
            'https://api.hotstar.com/' + path, video_id, headers={
                'hotstarauth': auth,
                'x-hs-appversion': '6.72.2',
                'x-hs-platform': 'web',
                'x-hs-usertoken': token,
            }, query=query)

        if response['message'] != "Playback URL's fetched successfully":
            raise ExtractorError(
                response['message'], expected=True)
        return response['data']

    def _call_api(self, path, video_id, query_name='contentId'):
        return self._download_json('https://api.hotstar.com/' + path, video_id=video_id, query={
            query_name: video_id,
            'tas': 10000,
        }, headers={
            'x-country-code': 'IN',
            'x-platform-code': 'PCTV',
        })

    def _call_api_v2(self, path, video_id, st=None, cookies=None):
        return self._call_api_impl(
            '%s/content/%s' % (path, video_id), video_id, st=st, cookies=cookies, query={
                'desired-config': 'audio_channel:stereo|container:fmp4|dynamic_range:hdr|encryption:plain|ladder:tv|package:dash|resolution:fhd|subs-tag:HotstarVIP|video_codec:h265',
                'device-id': cookies.get('device_id').value if cookies.get('device_id') else compat_str(uuid.uuid4()),
                'os-name': 'Windows',
                'os-version': '10',
            })


class HotStarIE(HotStarBaseIE):
    IE_NAME = 'hotstar'
    _VALID_URL = r'''(?x)
                        (?:
                            hotstar\:|
                            https?://(?:www\.)?hotstar\.com(?:/in)?/(?!in/)
                        )
                        (?:
                            (?P<type>movies|sports|episode|(?P<tv>tv))
                            (?:
                                \:|
                                /[^/?#]+/
                                (?(tv)
                                    (?:[^/?#]+/){2}|
                                    (?:[^/?#]+/)*
                                )
                            )|
                            [^/?#]+/
                        )?
                        (?P<id>\d{10})
                   '''
    _TESTS = [{
        'url': 'https://www.hotstar.com/can-you-not-spread-rumours/1000076273',
        'info_dict': {
            'id': '1000076273',
            'ext': 'mp4',
            'title': 'Can You Not Spread Rumours?',
            'description': 'md5:c957d8868e9bc793ccb813691cc4c434',
            'timestamp': 1447248600,
            'upload_date': '20151111',
            'duration': 381,
        },
    }, {
        'url': 'hotstar:1000076273',
        'only_matching': True,
    }, {
        'url': 'https://www.hotstar.com/movies/radha-gopalam/1000057157',
        'info_dict': {
            'id': '1000057157',
            'ext': 'mp4',
            'title': 'Radha Gopalam',
            'description': 'md5:be3bc342cc120bbc95b3b0960e2b0d22',
            'timestamp': 1140805800,
            'upload_date': '20060224',
            'duration': 9182,
        },
    }, {
        'url': 'hotstar:movies:1000057157',
        'only_matching': True,
    }, {
        'url': 'https://www.hotstar.com/in/sports/cricket/follow-the-blues-2021/recap-eng-fight-back-on-day-2/1260066104',
        'only_matching': True,
    }, {
        'url': 'https://www.hotstar.com/in/sports/football/most-costly-pl-transfers-ft-grealish/1260065956',
        'only_matching': True,
    }, {
        # contentData
        'url': 'hotstar:sports:1260065956',
        'only_matching': True,
    }, {
        # contentData
        'url': 'hotstar:sports:1260066104',
        'only_matching': True,
    }, {
        'url': 'https://www.hotstar.com/tv/ek-bhram-sarvagun-sampanna/s-2116/janhvi-targets-suman/1000234847',
        'info_dict': {
            'id': '1000234847',
            'ext': 'mp4',
            'title': 'Janhvi Targets Suman',
            'description': 'md5:78a85509348910bd1ca31be898c5796b',
            'timestamp': 1556670600,
            'upload_date': '20190501',
            'duration': 1219,
            'channel': 'StarPlus',
            'channel_id': 3,
            'series': 'Ek Bhram - Sarvagun Sampanna',
            'season': 'Chapter 1',
            'season_number': 1,
            'season_id': 6771,
            'episode': 'Janhvi Targets Suman',
            'episode_number': 8,
        },
    }, {
        'url': 'hotstar:episode:1000234847',
        'only_matching': True,
    }]
    _GEO_BYPASS = False
    _TYPE = {
        'movies': 'movie',
        'sports': 'match',
        'episode': 'episode',
        'tv': 'episode',
        None: 'content',
    }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        video_type = mobj.group('type')
        cookies = self._get_cookies(url)
        video_type = self._TYPE.get(video_type, video_type)
        video_data = self._call_api(f'o/v1/{video_type}/detail', video_id)['body']['results']['item']
        title = video_data['title']

        if not self.get_param('allow_unplayable_formats') and video_data.get('drmProtected'):
            self.report_drm(video_id)

        headers = {'Referer': 'https://www.hotstar.com/in'}
        formats = []
        subs = {}
        geo_restricted = False
        _, urlh = self._download_webpage_handle('https://www.hotstar.com/in', video_id)
        # Required to fix https://github.com/yt-dlp/yt-dlp/issues/396
        st = urlh.headers.get('x-origin-date')
        # change to v2 in the future
        playback_sets = self._call_api_v2('play/v1/playback', video_id, st=st, cookies=cookies)['playBackSets']
        for playback_set in playback_sets:
            if not isinstance(playback_set, dict):
                continue
            dr = re.search(r'dynamic_range:(?P<dr>[a-z]+)', playback_set.get('tagsCombination')).group('dr')
            format_url = url_or_none(playback_set.get('playbackUrl'))
            if not format_url:
                continue
            format_url = re.sub(
                r'(?<=//staragvod)(\d)', r'web\1', format_url)
            tags = str_or_none(playback_set.get('tagsCombination')) or ''
            ingored_res, ignored_vcodec, ignored_dr = self._configuration_arg('res'), self._configuration_arg('vcodec'), self._configuration_arg('dr')
            if any(f'resolution:{ig_res}' in tags for ig_res in ingored_res) or any(f'video_codec:{ig_vc}' in tags for ig_vc in ignored_vcodec) or any(f'dynamic_range:{ig_dr}' in tags for ig_dr in ignored_dr):
                continue
            ext = determine_ext(format_url)
            current_formats, current_subs = [], {}
            try:
                if 'package:hls' in tags or ext == 'm3u8':
                    current_formats, current_subs = self._extract_m3u8_formats_and_subtitles(
                        format_url, video_id, 'mp4',
                        entry_protocol='m3u8_native',
                        m3u8_id=f'{dr}-hls', headers=headers)
                elif 'package:dash' in tags or ext == 'mpd':
                    current_formats, current_subs = self._extract_mpd_formats_and_subtitles(
                        format_url, video_id, mpd_id=f'{dr}-dash', headers=headers)
                elif ext == 'f4m':
                    # produce broken files
                    pass
                else:
                    current_formats = [{
                        'url': format_url,
                        'width': int_or_none(playback_set.get('width')),
                        'height': int_or_none(playback_set.get('height')),
                    }]
            except ExtractorError as e:
                if isinstance(e.cause, compat_HTTPError) and e.cause.code == 403:
                    geo_restricted = True
                continue
            if tags and 'encryption:plain' not in tags:
                for f in current_formats:
                    f['has_drm'] = True
            if tags and 'language' in tags:
                lang = re.search(r'language:(?P<lang>[a-z]+)', tags).group('lang')
                for f in current_formats:
                    if not f.get('langauge'):
                        f['language'] = lang
            formats.extend(current_formats)
            subs = self._merge_subtitles(subs, current_subs)
        if not formats and geo_restricted:
            self.raise_geo_restricted(countries=['IN'], metadata_available=True)
        self._sort_formats(formats)

        for f in formats:
            f.setdefault('http_headers', {}).update(headers)

        return {
            'id': video_id,
            'title': title,
            'description': video_data.get('description'),
            'duration': int_or_none(video_data.get('duration')),
            'timestamp': int_or_none(video_data.get('broadcastDate') or video_data.get('startDate')),
            'formats': formats,
            'subtitles': subs,
            'channel': video_data.get('channelName'),
            'channel_id': video_data.get('channelId'),
            'series': video_data.get('showName'),
            'season': video_data.get('seasonName'),
            'season_number': int_or_none(video_data.get('seasonNo')),
            'season_id': video_data.get('seasonId'),
            'episode': title,
            'episode_number': int_or_none(video_data.get('episodeNo')),
            'http_headers': {
                'Referer': 'https://www.hotstar.com/in',
            }
        }


class HotStarPlaylistIE(HotStarBaseIE):
    IE_NAME = 'hotstar:playlist'
    _VALID_URL = r'https?://(?:www\.)?hotstar\.com/tv/[^/]+/s-\w+/list/[^/]+/t-(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://www.hotstar.com/tv/savdhaan-india/s-26/list/popular-clips/t-3_2_26',
        'info_dict': {
            'id': '3_2_26',
        },
        'playlist_mincount': 20,
    }, {
        'url': 'https://www.hotstar.com/tv/savdhaan-india/s-26/list/extras/t-2480',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        collection = self._call_api('o/v1/tray/find', playlist_id, 'uqId')['body']['results']
        entries = [
            self.url_result(
                'https://www.hotstar.com/%s' % video['contentId'],
                ie=HotStarIE.ie_key(), video_id=video['contentId'])
            for video in collection['assets']['items']
            if video.get('contentId')]

        return self.playlist_result(entries, playlist_id)


class HotStarSeriesIE(HotStarBaseIE):
    IE_NAME = 'hotstar:series'
    _VALID_URL = r'(?P<url>https?://(?:www\.)?hotstar\.com(?:/in)?/tv/[^/]+/(?P<id>\d+))'
    _TESTS = [{
        'url': 'https://www.hotstar.com/in/tv/radhakrishn/1260000646',
        'info_dict': {
            'id': '1260000646',
        },
        'playlist_mincount': 690,
    }, {
        'url': 'https://www.hotstar.com/tv/dancee-/1260050431',
        'info_dict': {
            'id': '1260050431',
        },
        'playlist_mincount': 43,
    }, {
        'url': 'https://www.hotstar.com/in/tv/mahabharat/435/',
        'info_dict': {
            'id': '435',
        },
        'playlist_mincount': 269,
    }]

    def _real_extract(self, url):
        url, series_id = self._match_valid_url(url).groups()
        headers = {
            'x-country-code': 'IN',
            'x-platform-code': 'PCTV',
        }
        detail_json = self._download_json('https://api.hotstar.com/o/v1/show/detail?contentId=' + series_id,
                                          video_id=series_id, headers=headers)
        id = compat_str(try_get(detail_json, lambda x: x['body']['results']['item']['id'], int))
        item_json = self._download_json('https://api.hotstar.com/o/v1/tray/g/1/items?etid=0&tao=0&tas=10000&eid=' + id,
                                        video_id=series_id, headers=headers)
        entries = [
            self.url_result(
                '%s/ignoreme/%d' % (url, video['contentId']),
                ie=HotStarIE.ie_key(), video_id=video['contentId'])
            for video in item_json['body']['results']['items']
            if video.get('contentId')]

        return self.playlist_result(entries, series_id)
