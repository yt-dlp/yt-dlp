import re
import time

from datetime import datetime
from .common import InfoExtractor
from ..cookies import LenientSimpleCookie
from ..utils import urlencode_postdata, ExtractorError


class AcademyMelIE(InfoExtractor):
    _TEST_EMAIL = 'meriat@jaga.email'  # use this as username in the test/local_parameters.json if running the test
    _TEST_PASSWORD = 'bBY-ccbp$8'  # use this as password in the test/local_parameters.json if running the test

    _CACHE_KEY = 'academymel'
    _CACHE_SUBKEY = 'login-cookie-header'

    _NETRC_MACHINE = 'academymel'
    _LOGIN_URL = 'https://academymel.online/cms/system/login'
    _VALID_URL = r'^https?:\/\/academymel\.online\/(?P<url>.*)$'

    _TESTS = [{
        'url': 'http://academymel.online/3video_1',
        'info_dict': {
            'id': 'master.m3u8?user-cdn=cdnvideo&acc-id=714517&user-id=359525183&loc-mode=ru&version=10:2:1:0:2:cdnvideo&consumer=vod&jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyLWlkIjozNTk1MjUxODN9',
            'title': 'master',
            'ext': 'mp4',
            'duration': 1693
        }
    }, {
        'url': 'http://academymel.online/3video_2',
        'info_dict': {
            'id': 'master.m3u8?user-cdn=cdnvideo&acc-id=714517&user-id=359525183&loc-mode=ru&version=10:2:1:0:2:cdnvideo&consumer=vod&jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyLWlkIjozNTk1MjUxODN9',
            'title': 'master',
            'ext': 'mp4',
            'duration': 1871
        }
    }]

    def _perform_login(self, username, password):
        login_body = urlencode_postdata({
            'action': 'processXdget',
            'xdgetId': 'r6335_1_1',
            'params[action]': 'login',
            'params[url]': 'http://academymel.online/cms/system/login?required=true',
            'params[object_type]': 'cms_page',
            'params[object_id]': -1,
            'params[email]': username,
            'params[password]': password,
            'requestTime': int(time.time())
        })

        try:
            webpage = self._request_webpage(self._LOGIN_URL,
                                            None,
                                            data=login_body,
                                            note='Logging into the academymel.online',
                                            errnote='Failed to log in into academymel.online',
                                            fatal=True)
        except ExtractorError:
            raise ExtractorError('Could not log in into academymel.online (login URL: "%s")' % self._LOGIN_URL,
                                 expected=True)

        # The response itself is a JSON, but it is not needed - only the Set-Cookie value(s) are
        cookie_header = webpage.get_header('Set-Cookie')
        set_cookie_header = LenientSimpleCookie(cookie_header)
        set_cookie_header.load(cookie_header)
        self.cache.store(self._CACHE_KEY, self._CACHE_SUBKEY, set_cookie_header)

    def playlist_from_entries(self, entries, valid_url):
        current_timestamp = int(time.time())
        current_datetime = datetime.fromtimestamp(current_timestamp)
        formatted_datetime = current_datetime.strftime("%d.%m.%Y, %H:%M")

        return self.playlist_result(entries,
                                    'academymel-playlist-%d' % current_timestamp,
                                    'AcademyMel playlist (%s)' % formatted_datetime,
                                    'AcademyMel playlist for %s (at %s)' % (valid_url, formatted_datetime))

    def _real_extract(self, url):
        valid_url = self._match_valid_url(url)

        if not valid_url:
            raise ExtractorError('Invalid URL found', expected=True)

        set_cookie_header = self.cache.load(self._CACHE_KEY, self._CACHE_SUBKEY)

        if not set_cookie_header:
            raise ExtractorError('The set-cookie has not been loaded', expected=True)

        try:
            webpage = self._download_webpage(url,
                                             None,
                                             headers=set_cookie_header,
                                             fatal=True,
                                             note='Downloading video website',
                                             errnote='Failed to download video website')
        except ExtractorError:
            raise ExtractorError('Could not download the video website at "%s"' % url, expected=True)

        entries = []
        for video_url in re.findall(
            r'<iframe[^>]+src=\"(?P<url>https?://[^/]+\.getcourse\.ru/sign-player/\?.*)\"',
                webpage):
            self.to_screen('AcademyMel video URL found: %s' % video_url)
            entries.append(self.url_result(video_url, 'GetCourseRu'))

        return self.playlist_from_entries(entries, valid_url)
