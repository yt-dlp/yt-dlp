# coding: utf-8
from .common import InfoExtractor
from .vimeo import VimeoIE

from ..compat import (
    compat_urllib_parse_urlencode
)

from ..utils import (
    smuggle_url,
    urlencode_postdata
)


class CybraryBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'cybrary'

    _API_KEY = 'AIzaSyCX9ru6j70PX2My1Eq6Q1zoMAhuTdXlzSw'
    _ENDPOINTS = {
        'login': 'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={}',
        'launch': 'https://app.cybrary.it/courses/api/catalog/{}/launch',
        'vimeo_oembed': 'https://vimeo.com/api/oembed.json?url=https://vimeo.com/{}'
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
    _VALID_URL = r'https?://app\.cybrary\.it.*/activity/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://app.cybrary.it/immersive/12487950/activity/63102',
        'md5': 'TODO: md5 sum of the first 10241 bytes of the video file (use --test)',
        'info_dict': {
            'id': '63102',
            'ext': 'mp4',
            'title': 'Browse, Career Paths & My Learning',
            # 'thumbnail': r're:^https?://.*\.jpg$',
            # TODO more properties, either as:
            # * A value
            # * MD5 checksum; start the string with md5:
            # * A regular expression; start the string with re:
            # * Any Python type (for example int or float)
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        # vimeo_id = self._call_api('launch', video_id)['vendor_data'][0]['videoId']
        vimeo_id = self._download_json(
            'https://app.cybrary.it/courses/api/catalog/{}/launch'.format(video_id), video_id,
            headers={'Authorization': f'Bearer {self._TOKEN}'})['vendor_data']['content'][0]['videoId']

        # print(vimeo_id)
        # print(compat_urllib_parse_urlencode(self._ENDPOINTS['vimeo_oembed'].format(vimeo_id)))

        # return self.url_result(
        #     smuggle_url('https://player.vimeo.com/video/{}'.format(vimeo_id), {'http_headers': {'Referer': 'https://api.cybrary.it/'}}),
        #     ie='Vimeo',
        #     video_id=vimeo_id)

        return self.url_result(
            smuggle_url('https://player.vimeo.com/video/{}'.format(vimeo_id), {'http_headers': {'Referer': 'https://api.cybrary.it/'}}),
            video_id=video_id,
            url_transparent=True
        )

        # TODO more code goes here, for example ...
        # title = self._html_search_regex(r'<h1>(.+?)</h1>', webpage, 'title')

        # return {
        #     'id': video_id,
        #     'title': title,
        #     'description': self._og_search_description(webpage),
        #     'uploader': self._search_regex(r'<div[^>]+id="uploader"[^>]*>([^<]+)<', webpage, 'uploader', fatal=False),
        #     # TODO more properties (see yt_dlp/extractor/common.py)
        # }