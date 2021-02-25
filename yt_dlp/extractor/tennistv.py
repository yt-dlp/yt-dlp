# coding: utf-8
from __future__ import unicode_literals

import json

from .common import InfoExtractor

from ..utils import (
    ExtractorError,
    unified_timestamp,
)


class TennisTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tennistv\.com/videos/(?P<id>[-a-z0-9]+)'
    _TEST = {
        'url': 'https://www.tennistv.com/videos/indian-wells-2018-verdasco-fritz',
        'info_dict': {
            'id': 'indian-wells-2018-verdasco-fritz',
            'ext': 'mp4',
            'title': 'Fernando Verdasco v Taylor Fritz',
            'description': 're:^After his stunning victory.{174}$',
            'thumbnail': 'https://atp-prod.akamaized.net/api/images/v1/images/112831/landscape/1242/0',
            'timestamp': 1521017381,
            'upload_date': '20180314',
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Requires email and password of a subscribed account',
    }
    _NETRC_MACHINE = 'tennistv'

    def _login(self):
        username, password = self._get_login_info()
        if not username or not password:
            raise ExtractorError('No login info available, needed for using %s.' % self.IE_NAME, expected=True)

        login_form = {
            'Email': username,
            'Password': password,
        }
        login_json = json.dumps(login_form).encode('utf-8')
        headers = {
            'content-type': 'application/json',
            'Referer': 'https://www.tennistv.com/login',
            'Origin': 'https://www.tennistv.com',
        }

        login_result = self._download_json(
            'https://www.tennistv.com/api/users/v1/login', None,
            note='Logging in',
            errnote='Login failed (wrong password?)',
            headers=headers,
            data=login_json)

        if login_result['error']['errorCode']:
            raise ExtractorError('Login failed, %s said: %r' % (self.IE_NAME, login_result['error']['errorMessage']))

        if login_result['entitlement'] != 'SUBSCRIBED':
            self.report_warning('%s may not be subscribed to %s.' % (username, self.IE_NAME))

        self._session_token = login_result['sessionToken']

    def _real_initialize(self):
        self._login()

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        internal_id = self._search_regex(r'video=([\w-]+)', webpage, 'internal video id')

        headers = {
            'Origin': 'https://www.tennistv.com',
            'authorization': 'ATP %s' % self._session_token,
            'content-type': 'application/json',
            'Referer': url,
        }
        check_data = {
            'videoID': internal_id,
            'VideoUrlType': 'HLS',
        }
        check_json = json.dumps(check_data).encode('utf-8')
        check_result = self._download_json(
            'https://www.tennistv.com/api/users/v1/entitlementchecknondiva',
            video_id, note='Checking video authorization', headers=headers, data=check_json)
        formats = self._extract_m3u8_formats(check_result['contentUrl'], video_id, ext='mp4')
        self._sort_formats(formats)

        vdata = self._download_json(
            'https://www.tennistv.com/api/en/v2/none/common/video/%s' % video_id,
            video_id, headers=headers)

        timestamp = unified_timestamp(vdata['timestamp'])
        thumbnail = vdata['video']['thumbnailUrl']
        description = vdata['displayText']['description']
        title = vdata['video']['title']

        series = vdata['tour']
        venue = vdata['displayText']['venue']
        round_str = vdata['seo']['round']

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'formats': formats,
            'thumbnail': thumbnail,
            'timestamp': timestamp,
            'series': series,
            'season': venue,
            'episode': round_str,
        }
