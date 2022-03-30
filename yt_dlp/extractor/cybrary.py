# coding: utf-8
from .common import InfoExtractor
from .vimeo import VimeoIE

from ..compat import (
    compat_urllib_parse_urlencode
)

from ..utils import (
    int_or_none,
    smuggle_url,
    traverse_obj,
    urlencode_postdata
)


class CybraryBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'cybrary'

    _API_KEY = 'AIzaSyCX9ru6j70PX2My1Eq6Q1zoMAhuTdXlzSw'
    _ENDPOINTS = {
        'login': 'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={}',
        'launch': 'https://app.cybrary.it/courses/api/catalog/{}/launch',
        'vimeo_oembed': 'https://vimeo.com/api/oembed.json?url=https://vimeo.com/{}',
        'enrollment': 'https://app.cybrary.it/courses/api/enrollment/{}'
    }
    _TOKEN = None

    def _perform_login(self, username, password):
        # self._request_webpage('https://app.cybrary.it/login/', None)
        response = self._download_json(
            self._ENDPOINTS['login'].format(self._API_KEY), None, note='Logging in',
            data=urlencode_postdata({'email': username, 'password': password, 'returnSecureToken': True}))

        if response:
            self._TOKEN = response['idToken']

    def _call_api(self, endpoint, item_id):
        return self._download_json(
            self._ENDPOINTS[endpoint].format(item_id), item_id,
            headers={'Authorization': f'Bearer {self._TOKEN}'})


class CybraryIE(CybraryBaseIE):
    _VALID_URL = r'https?://app.cybrary.it/immersive/(?P<enrollment>[0-9]+)/activity/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://app.cybrary.it/immersive/12487950/activity/63102',
        'md5': 'TODO: md5 sum of the first 10241 bytes of the video file (use --test)',
        'info_dict': {
            'id': '646609770',
            'ext': 'mp4',
            'title': 'Getting Started',
            # 'thumbnail': r're:^https?://.*\.jpg$',
            # TODO more properties, either as:
            # * A value
            # * MD5 checksum; start the string with md5:
            # * A regular expression; start the string with re:
            # * Any Python type (for example int or float)
        }
    }]

    def _real_extract(self, url):
        activity_id, enrollment_id = self._match_valid_url(url).group('id', 'enrollment')
        enrollment = self._call_api('enrollment', enrollment_id)

        course = enrollment['content']
        course_info = course.get('content_description')
        activity = course['learning_modules'][0]['activities'][0]

        vimeo_id = self._call_api('launch', activity_id)['vendor_data']['content'][0]['videoId']

        return {
            '_type': 'url_transparent',
            'series': course_info.get('title'),
            'series_id': int_or_none(course_info.get('id')),
            'id': vimeo_id,
            'title': activity.get('title'),
            'url': smuggle_url('https://player.vimeo.com/video/{}'.format(vimeo_id), {'http_headers': {'Referer': 'https://api.cybrary.it'}})
        }
