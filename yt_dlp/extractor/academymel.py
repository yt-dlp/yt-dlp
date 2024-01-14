import re
import time

from .common import InfoExtractor
from .getcourseru import GetCourseRuIE
from ..utils import update_url_query, urlencode_postdata


class AcademyMelIE(InfoExtractor):
    _NETRC_MACHINE = 'academymel'
    _VALID_URL = r'https?://academymel\.online/(?P<id>[^/?#]+)'
    _LOGIN_URL = 'https://academymel.online/cms/system/login'
    _TESTS = [{
        'url': 'http://academymel.online/3video_1',
        'info_dict': {
            'id': '4885302',
            'title': 'Промоуроки Академии МЕЛ',
            'ext': 'mp4',
            'duration': 1693
        }
    }]

    def _perform_login(self, username, password):
        self._request_webpage(
            self._LOGIN_URL, None, 'Logging in', 'Failed to log in',
            data=urlencode_postdata({
                'action': 'processXdget',
                'xdgetId': 'r6335_1_1',
                'params[action]': 'login',
                'params[url]': update_url_query(self._LOGIN_URL, {'required': 'true'}),
                'params[object_type]': 'cms_page',
                'params[object_id]': -1,
                'params[email]': username,
                'params[password]': password,
                'requestTime': int(time.time())
            }))

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        if not self._get_cookies(self._LOGIN_URL).get('PHPSESSID5'):
            self.raise_login_required()
        webpage = self._download_webpage(url, playlist_id)
        title = self._html_extract_title(webpage)

        return self.playlist_from_matches(
            re.findall(r'data-iframe-src="(https?://[^."]+\.getcourse\.ru/sign-player/[^"]+)', webpage),
            playlist_id, title, ie=GetCourseRuIE, video_kwargs={
                'url_transparent': True,
                'title': title,
            })
