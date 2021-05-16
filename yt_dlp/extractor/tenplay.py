# coding: utf-8
from __future__ import unicode_literals
from datetime import datetime
import base64
from .common import InfoExtractor
from ..utils import (
    HEADRequest,
    parse_age_limit,
    urlencode_postdata,
)


class TenPlayIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?10play\.com\.au/(?:[^/]+/)+(?P<id>tpv\d{6}[a-z]{5})'
    _NETRC_MACHINE = '10play'
    _TESTS = [{
        'url': 'https://10play.com.au/todd-sampsons-body-hack/episodes/season-4/episode-7/tpv200921kvngh',
        'info_dict': {
            'id': 'tpv200928zskgi',
            'ext': 'mp4',
            'title': "Todd Sampson's Body Hack - S4 Ep. 2",
            'description': 'md5:a73ea55671034c6367784405423ef5a0',
            'age_limit': 15,
            'timestamp': 1601379660,
            'upload_date': '20200909',
            'uploader_id': 'Channel 10',
        },
        'params': {
            'skip_download': True,
        }
    }, {
        'url': 'https://10play.com.au/how-to-stay-married/web-extras/season-1/terrys-talks-ep-1-embracing-change/tpv190915ylupc',
        'only_matching': True,
    }]
    _GEO_BYPASS = False

    def _get_bearer_token(self, video_id):
        _authdata = self._get_login_info()
        _time = datetime.now()
        _auth_header = base64.b64encode(f'{_time.year}{"{:02d}".format(_time.month)}{"{:02d}".format(_time.day)}000000'.encode('ascii')).decode('ascii')
        if(_authdata[0] is None or _authdata[1] is None):
            raise Exception('Your 10play account\'s details must be provided with --username and --password.')
        username, password = self._get_login_info()
        data = self._download_json('https://10play.com.au/api/user/auth', video_id, 'Getting bearer token', headers={
            'X-Network-Ten-Auth': _auth_header,
        }, data=urlencode_postdata({
            'email': username,
            'password': password,
        }))
        return f"Bearer {data['jwt']['accessToken']}"

    def _real_extract(self, url):
        content_id = self._match_id(url)
        _token = self._get_bearer_token(content_id)
        data = self._download_json(
            'https://10play.com.au/api/v1/videos/' + content_id, content_id)
        _video_url = self._download_json(data.get('playbackApiEndpoint'), content_id, 'Downloading video JSON', headers={'Authorization': _token}).get('source')
        m3u8_url = self._request_webpage(HEADRequest(
            _video_url), content_id).geturl()
        if '10play-not-in-oz' in m3u8_url:
            self.raise_geo_restricted(countries=['AU'])
        formats = self._extract_m3u8_formats(m3u8_url, content_id, 'mp4')
        self._sort_formats(formats)

        return {
            'formats': formats,
            'id': content_id,
            'title': data.get('title'),
            'description': data.get('description'),
            'age_limit': parse_age_limit(data.get('classification')),
            'series': data.get('showName'),
            'season': data.get('showContentSeason'),
            'timestamp': data.get('published'),
            'thumbnail': data.get('imageURL'),
            'uploader_id': 'Channel 10',
        }
