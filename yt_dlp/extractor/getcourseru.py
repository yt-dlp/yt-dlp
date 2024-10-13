import re
import time
import urllib.parse

from .common import InfoExtractor
from ..utils import ExtractorError, int_or_none, url_or_none, urlencode_postdata
from ..utils.traversal import traverse_obj


class GetCourseRuPlayerIE(InfoExtractor):
    _VALID_URL = r'https?://player02\.getcourse\.ru/sign-player/?\?(?:[^#]+&)?json=[^#&]+'
    _EMBED_REGEX = [rf'<iframe[^>]+\bsrc=[\'"](?P<url>{_VALID_URL}[^\'"]*)']
    _TESTS = [{
        'url': 'http://player02.getcourse.ru/sign-player/?json=eyJ2aWRlb19oYXNoIjoiMTkwYmRmOTNmMWIyOTczNTMwOTg1M2E3YTE5ZTI0YjMiLCJ1c2VyX2lkIjozNTk1MjUxODMsInN1Yl9sb2dpbl91c2VyX2lkIjpudWxsLCJsZXNzb25faWQiOm51bGwsImlwIjoiNDYuMTQyLjE4Mi4yNDciLCJnY19ob3N0IjoiYWNhZGVteW1lbC5vbmxpbmUiLCJ0aW1lIjoxNzA1NDQ5NjQyLCJwYXlsb2FkIjoidV8zNTk1MjUxODMiLCJ1aV9sYW5ndWFnZSI6InJ1IiwiaXNfaGF2ZV9jdXN0b21fc3R5bGUiOnRydWV9&s=354ad2c993d95d5ac629e3133d6cefea&vh-static-feature=zigzag',
        'info_dict': {
            'id': '513573381',
            'title': '190bdf93f1b29735309853a7a19e24b3',
            'ext': 'mp4',
            'thumbnail': 'https://preview-htz.kinescopecdn.net/preview/190bdf93f1b29735309853a7a19e24b3/preview.jpg?version=1702370546&host=vh-80',
            'duration': 1693,
        },
        'skip': 'JWT expired',
    }]

    def _real_extract(self, url):
        webpage = self._download_webpage(url, None, 'Downloading player page')
        window_configs = self._search_json(
            r'window\.configs\s*=', webpage, 'config', None)
        video_id = str(window_configs['gcFileId'])
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
            'subtitles': subtitles,
        }


class GetCourseRuIE(InfoExtractor):
    _NETRC_MACHINE = 'getcourseru'
    _DOMAINS = [
        'academymel.online',
        'marafon.mani-beauty.com',
        'on.psbook.ru',
    ]
    _BASE_URL_RE = rf'https?://(?:(?!player02\.)[^.]+\.getcourse\.(?:ru|io)|{"|".join(map(re.escape, _DOMAINS))})'
    _VALID_URL = [
        rf'{_BASE_URL_RE}/(?!pl/|teach/)(?P<id>[^?#]+)',
        rf'{_BASE_URL_RE}/(?:pl/)?teach/control/lesson/view\?(?:[^#]+&)?id=(?P<id>\d+)',
    ]
    _TESTS = [{
        'url': 'http://academymel.online/3video_1',
        'info_dict': {
            'id': '3059742',
            'display_id': '3video_1',
            'title': 'Промоуроки Академии МЕЛ',
        },
        'playlist_count': 1,
        'playlist': [{
            'info_dict': {
                'id': '513573381',
                'ext': 'mp4',
                'title': 'Промоуроки Академии МЕЛ',
                'thumbnail': 'https://preview-htz.kinescopecdn.net/preview/190bdf93f1b29735309853a7a19e24b3/preview.jpg?version=1702370546&host=vh-80',
                'duration': 1693,
            },
        }],
    }, {
        'url': 'https://academymel.getcourse.ru/3video_1',
        'info_dict': {
            'id': '3059742',
            'display_id': '3video_1',
            'title': 'Промоуроки Академии МЕЛ',
        },
        'playlist_count': 1,
        'playlist': [{
            'info_dict': {
                'id': '513573381',
                'ext': 'mp4',
                'title': 'Промоуроки Академии МЕЛ',
                'thumbnail': 'https://preview-htz.kinescopecdn.net/preview/190bdf93f1b29735309853a7a19e24b3/preview.jpg?version=1702370546&host=vh-80',
                'duration': 1693,
            },
        }],
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
                'duration': 704,
            },
        }],
        'skip': 'paid lesson',
    }, {
        'url': 'https://manibeauty.getcourse.ru/pl/teach/control/lesson/view?id=272499894',
        'info_dict': {
            'id': '272499894',
            'title': 'Мотивация к тренировкам',
        },
        'playlist_count': 1,
        'playlist': [{
            'info_dict': {
                'id': '447479687',
                'ext': 'mp4',
                'title': 'Мотивация к тренировкам',
                'thumbnail': 'https://preview-htz.vhcdn.com/preview/70ed5b9f489dd03b4aff55bfdff71a26/preview.jpg?version=1685115787&host=vh-71',
                'duration': 30,
            },
        }],
        'skip': 'paid lesson',
    }, {
        'url': 'https://gaismasmandalas.getcourse.io/ATLAUTSEVBUT',
        'only_matching': True,
    }]

    _LOGIN_URL_PATH = '/cms/system/login'

    def _login(self, hostname, username, password):
        if self._get_cookies(f'https://{hostname}').get('PHPSESSID5'):
            return
        login_url = f'https://{hostname}{self._LOGIN_URL_PATH}'
        webpage = self._download_webpage(login_url, None)

        self._request_webpage(
            login_url, None, 'Logging in', 'Failed to log in',
            data=urlencode_postdata({
                'action': 'processXdget',
                'xdgetId': self._html_search_regex(
                    r'<form[^>]+\bclass="[^"]*\bstate-login[^"]*"[^>]+\bdata-xdget-id="([^"]+)"',
                    webpage, 'xdgetId'),
                'params[action]': 'login',
                'params[url]': login_url,
                'params[object_type]': 'cms_page',
                'params[object_id]': -1,
                'params[email]': username,
                'params[password]': password,
                'requestTime': int(time.time()),
                'requestSimpleSign': self._html_search_regex(
                    r'window.requestSimpleSign\s*=\s*"([\da-f]+)"', webpage, 'simple sign'),
            }))

    def _real_extract(self, url):
        hostname = urllib.parse.urlparse(url).hostname
        username, password = self._get_login_info(netrc_machine=hostname)
        if username:
            self._login(hostname, username, password)

        display_id = self._match_id(url)
        webpage, urlh = self._download_webpage_handle(url, display_id)
        if self._LOGIN_URL_PATH in urlh.url:
            raise ExtractorError(
                f'This video is only available for registered users. {self._login_hint("any", netrc=hostname)}',
                expected=True)

        playlist_id = self._search_regex(
            r'window\.(?:lessonId|gcsObjectId)\s*=\s*(\d+)', webpage, 'playlist id', default=display_id)
        title = self._og_search_title(webpage) or self._html_extract_title(webpage)

        return self.playlist_from_matches(
            re.findall(GetCourseRuPlayerIE._EMBED_REGEX[0], webpage),
            playlist_id, title, display_id=display_id, ie=GetCourseRuPlayerIE, video_kwargs={
                'url_transparent': True,
                'title': title,
            })
