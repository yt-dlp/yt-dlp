import hashlib

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    dict_get,
    traverse_obj,
    urlencode_postdata,
)


class BrilliantpalaIE(InfoExtractor):
    _NETRC_MACHINE = 'brilliantpala'
    _LOGIN_API = 'https://elearn.brilliantpala.org/login/'

    def _get_logged_in_username(self, webpage):
        if self._LOGIN_API == self._og_search_property('url', webpage):
            self.raise_login_required()
        return self._html_search_regex(
            r'"username":\s*"(?P<username>[^"]+)"', webpage, 'stream page info', 'username')

    def _perform_login(self, username, password):
        login_form = self._hidden_inputs(self._download_webpage(
            self._LOGIN_API, None, 'Downloading login page'))
        login_form.update({
            'username': username,
            'password': password,
        })
        self._set_cookie('elearn.brilliantpala.org', 'csrftoken', login_form['csrfmiddlewaretoken'])

        logged_page = self._download_webpage(
            self._LOGIN_API, None, note='Logging in', headers={'Referer': self._LOGIN_API},
            data=urlencode_postdata(login_form))

        if self._html_search_regex(
            r'(?P<warning>Your username / email and password)', logged_page,
                'authentication failure warning', group='warning', fatal=False, default=''):
            raise ExtractorError('wrong username or password', expected=True)

        if self._html_search_regex(
            r'(?P<button_text>Logout Other Devices)', logged_page, 'logout device button',
                group='button_text', fatal=False, default=''):
            logout_device_form = self._hidden_inputs(logged_page)
            self._download_webpage(
                'https://elearn.brilliantpala.org/logout_devices/?next=/', None,
                note='Logging out other devices', data=urlencode_postdata(logout_device_form),
                headers={'Referer': self._LOGIN_API})


class BrilliantpalaCourseContentPageIE(BrilliantpalaIE):
    IE_NAME = 'Brilliantpala:CourseContent'
    IE_DESC = 'VoD on elearn.brilliantpala.org'
    _VALID_URL = r'https?://elearn\.brilliantpala\.org/courses/(?P<course_id>\d+)/contents/(?P<content_id>\d+)/?'
    _TESTS = [{
        'url': 'https://elearn.brilliantpala.org/courses/42/contents/12345/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        course_id, content_id = self._match_valid_url(url).group('course_id', 'content_id')
        video_id = f'{course_id}-{content_id}'

        username = self._get_logged_in_username(self._download_webpage(url, video_id))

        content_json = self._download_json(
            f'https://elearn.brilliantpala.org/api/v2.4/contents/{content_id}/',
            video_id, note='Fetching content info', errnote='Unable to fetch content info')

        entries = []
        for stream in traverse_obj(content_json, ('video', 'streams')):
            formats = self._extract_m3u8_formats(
                m3u8_url=stream['url'], video_id=video_id)
            for format in formats:
                format['hls_aes'] = {
                    'uri': f'https://elearn.brilliantpala.org/api/v2.5/video_contents/{content_id}/key/'}
            entry = {
                'id': str(stream['id']),
                'title': dict_get(content_json, 'title', ''),
                'formats': formats,
                'http_headers': {'X-Key': hashlib.sha256(username.encode('ascii')).hexdigest()},
                'thumbnail': content_json.get('cover_image')
            }
            entries.append(entry)

        return self.playlist_result(
            entries, playlist_id=video_id, playlist_title=content_json.get('title'))
