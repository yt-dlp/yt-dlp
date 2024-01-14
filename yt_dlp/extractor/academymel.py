import re
import time

from datetime import datetime
from .common import InfoExtractor
from ..utils import urlencode_postdata, ExtractorError


class AcademyMelIE(InfoExtractor):
    _TEST_EMAIL = 'meriat@jaga.email'  # use this as username in the test/local_parameters.json if running the test
    _TEST_PASSWORD = 'bBY-ccbp$8'  # use this as password in the test/local_parameters.json if running the test

    _NETRC_MACHINE = 'academymel'
    _LOGIN_URL = 'https://academymel.online/cms/system/login'
    _VALID_URL = r'^https?:\/\/academymel\.online\/(?P<url>.*)$'

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

        self._request_webpage(self._LOGIN_URL,
                              None,
                              data=login_body,
                              note='Logging into the academymel.online',
                              errnote='Failed to log in into academymel.online',
                              fatal=True)

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

        webpage = self._download_webpage(url,
                                         None,
                                         fatal=True,
                                         note='Downloading video website',
                                         errnote='Failed to download video website')

        title = self._search_regex(r'<title>(?P<title>.*)</title>', webpage, 'title')

        entries = []
        processed_urls = set()  # Set to keep track of processed URLs

        for video_url in re.findall(
            r'data-iframe-src=\"(?P<url>https?://[^/]+\.getcourse\.ru/sign-player/\?.*?)\"',
            webpage,
                re.DOTALL + re.VERBOSE):
            # Check if the URL has not been processed before
            if video_url not in processed_urls:
                entries.append(self.url_result(video_url, 'GetCourseRu', url_transparent=True, title=title))
                processed_urls.add(video_url)  # Add the URL to the set of processed URLs

        return self.playlist_from_entries(entries, valid_url)
