import pprint
from time import time
from re import escape, findall
from urllib.parse import urlparse

from .common import InfoExtractor
from ..utils import int_or_none, traverse_obj, update_url_query, url_or_none, urlencode_postdata


class GetCourseRuPlayerIE(InfoExtractor):
    _VALID_URL = r'https?://player\d{2,}\.getcourse\.ru/sign-player/?\?(?:[^#]+&)?json=(?P<id>[^#&]+)'
    _TESTS = [{
        'url': 'http://player02.getcourse.ru/sign-player/?json=eyJ2aWRlb19oYXNoIjoiMTkwYmRmOTNmMWIyOTczNTMwOTg1M2E3YTE5ZTI0YjMiLCJ1c2VyX2lkIjozNTk1MjUxODMsInN1Yl9sb2dpbl91c2VyX2lkIjpudWxsLCJsZXNzb25faWQiOm51bGwsImlwIjoiNDYuMTQyLjE4Mi4yNDciLCJnY19ob3N0IjoiYWNhZGVteW1lbC5vbmxpbmUiLCJ0aW1lIjoxNzA1NDQ5NjQyLCJwYXlsb2FkIjoidV8zNTk1MjUxODMiLCJ1aV9sYW5ndWFnZSI6InJ1IiwiaXNfaGF2ZV9jdXN0b21fc3R5bGUiOnRydWV9&s=354ad2c993d95d5ac629e3133d6cefea&vh-static-feature=zigzag',
        'info_dict': {
            'id': '4885302',
            'title': '190bdf93f1b29735309853a7a19e24b3',
            'ext': 'mp4',
            'thumbnail': 'https://preview-htz.kinescopecdn.net/preview/190bdf93f1b29735309853a7a19e24b3/preview.jpg?version=1702370546&host=vh-80',
            'duration': 1693
        },
        'skip': 'JWT expired',
    }]

    def _real_extract(self, url):
        webpage = self._download_webpage(url, None, 'Downloading player page')
        window_configs = self._search_json(
            r'window\.configs\s*=', webpage, 'config', None)
        video_id = str(window_configs['videoId'])
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            window_configs['masterPlaylistUrl'], video_id)

        return {
            **traverse_obj(window_configs, {
                'title': ('videoHash', {str}),
                'thumbnail': ('previewUrl', {url_or_none}),
                'duration': ('videoDuration', {int_or_none}),
            }),
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles
        }


class GetCourseRuIE(InfoExtractor):
    _NETRC_MACHINE = 'getcourseru'
    _LOGIN_URL_SUFFIX = 'cms/system/login'
    _TESTS = [{
        'url': 'http://academymel.online/3video_1',
        'info_dict': {
            'id': '3video_1',
            'title': 'Промоуроки Академии МЕЛ',
        },
        'playlist_count': 1,
        'playlist': [{
            'info_dict': {
                'id': '4885302',
                'ext': 'mp4',
                'title': 'Промоуроки Академии МЕЛ',
                'thumbnail': 'https://preview-htz.kinescopecdn.net/preview/190bdf93f1b29735309853a7a19e24b3/preview.jpg?version=1702370546&host=vh-80',
                'duration': 1693
            },
        }]
    }, {
        'url': 'https://academymel.getcourse.ru/3video_1',
        'info_dict': {
            'id': '3video_1',
            'title': 'Промоуроки Академии МЕЛ',
        },
        'playlist_count': 1,
        'playlist': [{
            'info_dict': {
                'id': '4885302',
                'ext': 'mp4',
                'title': 'Промоуроки Академии МЕЛ',
                'thumbnail': 'https://preview-htz.kinescopecdn.net/preview/190bdf93f1b29735309853a7a19e24b3/preview.jpg?version=1702370546&host=vh-80',
                'duration': 1693
            },
        }]
    }, {
        'url': 'https://academymel.getcourse.ru/pl/teach/control/lesson/view?id=319141781&editMode=0',
        'info_dict': {
            'id': '319141781',
            'title': '1. Разминка у стены',
        },
        'playlist_count': 1,
        'playlist': [{
            'info_dict': {
                'id': '4919601',
                'ext': 'mp4',
                'title': '1. Разминка у стены',
                'thumbnail': 'https://preview-htz.vhcdn.com/preview/5a521788e7dc25b4f70c3dff6512d90e/preview.jpg?version=1703223532&host=vh-81',
                'duration': 704
            },
        }],
        'skip': 'paid lesson'
    }]
    _DOMAINS = [
        'academymel.online'
    ]
    _BASE_URL_RE = rf'https?://(?:(?!player\d+)[^.]+\.getcourse\.ru|{"|".join(map(escape, _DOMAINS))})'
    _VALID_URL = [
        rf'{_BASE_URL_RE}/(?P<id>[^/?#]+)/?(?:[?#]|$)',
        rf'{_BASE_URL_RE}/[^?#]+/view/?\?(?:[^#]+&)?id=(?P<id>\d+)',
    ]

    def _login(self, url, username, password):
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"

        self._request_webpage(
            base_url + self._LOGIN_URL_SUFFIX, None, 'Logging in', 'Failed to log in',
            data=urlencode_postdata({
                'action': 'processXdget',
                'xdgetId': 'r6335_1_1',
                #'xdgetId': '99945',
                'params[action]': 'login',
                'params[url]': update_url_query(base_url + self._LOGIN_URL_SUFFIX, {'required': 'true'}),
                'params[object_type]': 'cms_page',
                'params[object_id]': -1,
                'params[email]': username,
                'params[password]': password,
                'requestTime': int(time())
            }))

    def _real_extract(self, url):
        username, password = self._get_login_info()
        self._login(url, username, password)

        if not self._get_cookies(url).get('PHPSESSID5'):
            self.raise_login_required()

        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        playlist_id = self._search_regex(
            r'window\.lessonId\s*=\s*(\d+)', webpage, 'playlist id', default=display_id)

        title = self._html_extract_title(webpage)

        return self.playlist_from_matches(
            findall(r'data-iframe-src="(https?://player\d{2,}\.getcourse\.ru/sign-player/?\?(?:[^#]+&)?json=[^"]+)',
                    webpage),
            playlist_id, title, ie=GetCourseRuPlayerIE, video_kwargs={
                'url_transparent': True,
                'title': title,
            })
