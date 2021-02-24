# coding: utf-8
from __future__ import unicode_literals

import json
import uuid

from .adobepass import AdobePassIE
from ..compat import (
    compat_HTTPError,
    compat_str,
    compat_urllib_parse_unquote,
)
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_age_limit,
    parse_duration,
    try_get,
    unified_timestamp,
)


class FOXIE(AdobePassIE):
    _VALID_URL = r'https?://(?:www\.)?fox\.com/watch/(?P<id>[\da-fA-F]+)'
    _TESTS = [{
        # clip
        'url': 'https://www.fox.com/watch/4b765a60490325103ea69888fb2bd4e8/',
        'md5': 'ebd296fcc41dd4b19f8115d8461a3165',
        'info_dict': {
            'id': '4b765a60490325103ea69888fb2bd4e8',
            'ext': 'mp4',
            'title': 'Aftermath: Bruce Wayne Develops Into The Dark Knight',
            'description': 'md5:549cd9c70d413adb32ce2a779b53b486',
            'duration': 102,
            'timestamp': 1504291893,
            'upload_date': '20170901',
            'creator': 'FOX',
            'series': 'Gotham',
            'age_limit': 14,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # episode, geo-restricted
        'url': 'https://www.fox.com/watch/087036ca7f33c8eb79b08152b4dd75c1/',
        'only_matching': True,
    }, {
        # episode, geo-restricted, tv provided required
        'url': 'https://www.fox.com/watch/30056b295fb57f7452aeeb4920bc3024/',
        'only_matching': True,
    }]
    _GEO_BYPASS = False
    _HOME_PAGE_URL = 'https://www.fox.com/'
    _API_KEY = 'abdcbed02c124d393b39e818a4312055'
    _access_token = None

    def _call_api(self, path, video_id, data=None):
        headers = {
            'X-Api-Key': self._API_KEY,
        }
        if self._access_token:
            headers['Authorization'] = 'Bearer ' + self._access_token
        try:
            return self._download_json(
                'https://api2.fox.com/v2.0/' + path,
                video_id, data=data, headers=headers)
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 403:
                entitlement_issues = self._parse_json(
                    e.cause.read().decode(), video_id)['entitlementIssues']
                for e in entitlement_issues:
                    if e.get('errorCode') == 1005:
                        raise ExtractorError(
                            'This video is only available via cable service provider '
                            'subscription. You may want to use --cookies.', expected=True)
                messages = ', '.join([e['message'] for e in entitlement_issues])
                raise ExtractorError(messages, expected=True)
            raise

    def _real_initialize(self):
        if not self._access_token:
            mvpd_auth = self._get_cookies(self._HOME_PAGE_URL).get('mvpd-auth')
            if mvpd_auth:
                self._access_token = (self._parse_json(compat_urllib_parse_unquote(
                    mvpd_auth.value), None, fatal=False) or {}).get('accessToken')
            if not self._access_token:
                self._access_token = self._call_api(
                    'login', None, json.dumps({
                        'deviceId': compat_str(uuid.uuid4()),
                    }).encode())['accessToken']

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video = self._call_api('vodplayer/' + video_id, video_id)

        title = video['name']
        release_url = video['url']
        try:
            m3u8_url = self._download_json(release_url, video_id)['playURL']
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 403:
                error = self._parse_json(e.cause.read().decode(), video_id)
                if error.get('exception') == 'GeoLocationBlocked':
                    self.raise_geo_restricted(countries=['US'])
                raise ExtractorError(error['description'], expected=True)
            raise
        formats = self._extract_m3u8_formats(
            m3u8_url, video_id, 'mp4',
            entry_protocol='m3u8_native', m3u8_id='hls')
        self._sort_formats(formats)

        data = try_get(
            video, lambda x: x['trackingData']['properties'], dict) or {}

        duration = int_or_none(video.get('durationInSeconds')) or int_or_none(
            video.get('duration')) or parse_duration(video.get('duration'))
        timestamp = unified_timestamp(video.get('datePublished'))
        creator = data.get('brand') or data.get('network') or video.get('network')
        series = video.get('seriesName') or data.get(
            'seriesName') or data.get('show')

        subtitles = {}
        for doc_rel in video.get('documentReleases', []):
            rel_url = doc_rel.get('url')
            if not url or doc_rel.get('format') != 'SCC':
                continue
            subtitles['en'] = [{
                'url': rel_url,
                'ext': 'scc',
            }]
            break

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'description': video.get('description'),
            'duration': duration,
            'timestamp': timestamp,
            'age_limit': parse_age_limit(video.get('contentRating')),
            'creator': creator,
            'series': series,
            'season_number': int_or_none(video.get('seasonNumber')),
            'episode': video.get('name'),
            'episode_number': int_or_none(video.get('episodeNumber')),
            'release_year': int_or_none(video.get('releaseYear')),
            'subtitles': subtitles,
        }
