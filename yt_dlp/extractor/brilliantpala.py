import hashlib

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    traverse_obj,
    urlencode_postdata,
)


class BrilliantpalaBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'brilliantpala'
    _DOMAIN = '{subdomain}.brilliantpala.org'

    def _initialize_pre_login(self):
        self._HOMEPAGE = f'https://{self._DOMAIN}'
        self._LOGIN_API = f'{self._HOMEPAGE}/login/'
        self._LOGOUT_DEVICES_API = f'{self._HOMEPAGE}/logout_devices/?next=/'
        self._CONTENT_API = f'{self._HOMEPAGE}/api/v2.4/contents/{{content_id}}/'
        self._HLS_AES_URI = f'{self._HOMEPAGE}/api/v2.5/video_contents/{{content_id}}/key/'

    def _get_logged_in_username(self, url, video_id):
        webpage, urlh = self._download_webpage_handle(url, video_id)
        if urlh.url.startswith(self._LOGIN_API):
            self.raise_login_required()
        return self._html_search_regex(
            r'"username"\s*:\s*"(?P<username>[^"]+)"', webpage, 'logged-in username')

    def _perform_login(self, username, password):
        login_form = self._hidden_inputs(self._download_webpage(
            self._LOGIN_API, None, 'Downloading login page'))
        login_form.update({
            'username': username,
            'password': password,
        })
        self._set_cookie(self._DOMAIN, 'csrftoken', login_form['csrfmiddlewaretoken'])

        logged_page = self._download_webpage(
            self._LOGIN_API, None, note='Logging in', headers={'Referer': self._LOGIN_API},
            data=urlencode_postdata(login_form))

        if self._html_search_regex(
                r'(Your username / email and password)', logged_page, 'auth fail', default=None):
            raise ExtractorError('wrong username or password', expected=True)

        # the maximum number of logins is one
        if self._html_search_regex(
                r'(Logout Other Devices)', logged_page, 'logout devices button', default=None):
            logout_device_form = self._hidden_inputs(logged_page)
            self._download_webpage(
                self._LOGOUT_DEVICES_API, None, headers={'Referer': self._LOGIN_API},
                note='Logging out other devices', data=urlencode_postdata(logout_device_form))

    def _real_extract(self, url):
        course_id, content_id = self._match_valid_url(url).group('course_id', 'content_id')
        video_id = f'{course_id}-{content_id}'

        username = self._get_logged_in_username(url, video_id)

        content_json = self._download_json(
            self._CONTENT_API.format(content_id=content_id), video_id,
            note='Fetching content info', errnote='Unable to fetch content info')

        entries = []
        for stream in traverse_obj(content_json, ('video', 'streams', lambda _, v: v['id'] and v['url'])):
            formats = self._extract_m3u8_formats(stream['url'], video_id, fatal=False)
            if not formats:
                continue
            entries.append({
                'id': str(stream['id']),
                'title': content_json.get('title'),
                'formats': formats,
                'hls_aes': {'uri': self._HLS_AES_URI.format(content_id=content_id)},
                'http_headers': {'X-Key': hashlib.sha256(username.encode('ascii')).hexdigest()},
                'thumbnail': content_json.get('cover_image'),
            })

        return self.playlist_result(
            entries, playlist_id=video_id, playlist_title=content_json.get('title'))


class BrilliantpalaElearnIE(BrilliantpalaBaseIE):
    IE_NAME = 'Brilliantpala:Elearn'
    IE_DESC = 'VoD on elearn.brilliantpala.org'
    _VALID_URL = r'https?://elearn\.brilliantpala\.org/courses/(?P<course_id>\d+)/contents/(?P<content_id>\d+)/?'
    _TESTS = [{
        'url': 'https://elearn.brilliantpala.org/courses/42/contents/12345/',
        'only_matching': True,
    }, {
        'url': 'https://elearn.brilliantpala.org/courses/98/contents/36683/',
        'info_dict': {
            'id': '23577',
            'ext': 'mp4',
            'title': 'Physical World, Units and Measurements  - 1',
            'thumbnail': 'https://d1j3vi2u94ebt0.cloudfront.net/institute/brilliantpalalms/chapter_contents/26237/e657f81b90874be19795c7ea081f8d5c.png',
            'live_status': 'not_live',
        },
        'params': {
            'skip_download': True,
        },
    }]

    _DOMAIN = BrilliantpalaBaseIE._DOMAIN.format(subdomain='elearn')


class BrilliantpalaClassesIE(BrilliantpalaBaseIE):
    IE_NAME = 'Brilliantpala:Classes'
    IE_DESC = 'VoD on classes.brilliantpala.org'
    _VALID_URL = r'https?://classes\.brilliantpala\.org/courses/(?P<course_id>\d+)/contents/(?P<content_id>\d+)/?'
    _TESTS = [{
        'url': 'https://classes.brilliantpala.org/courses/42/contents/12345/',
        'only_matching': True,
    }, {
        'url': 'https://classes.brilliantpala.org/courses/416/contents/25445/',
        'info_dict': {
            'id': '9128',
            'ext': 'mp4',
            'title': 'Motion in a Straight Line - Class 1',
            'thumbnail': 'https://d3e4y8hquds3ek.cloudfront.net/institute/brilliantpalaelearn/chapter_contents/ff5ba838d0ec43419f67387fe1a01fa8.png',
            'live_status': 'not_live',
        },
        'params': {
            'skip_download': True,
        },
    }]

    _DOMAIN = BrilliantpalaBaseIE._DOMAIN.format(subdomain='classes')
