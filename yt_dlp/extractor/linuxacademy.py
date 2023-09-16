import json
import random

from .common import InfoExtractor
from ..compat import compat_b64decode, compat_str
from ..networking.exceptions import HTTPError
from ..utils import (
    clean_html,
    ExtractorError,
    js_to_json,
    parse_duration,
    try_get,
    unified_timestamp,
    urlencode_postdata,
    urljoin,
)


class LinuxAcademyIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.)?linuxacademy\.com/cp/
                        (?:
                            courses/lesson/course/(?P<chapter_id>\d+)/lesson/(?P<lesson_id>\d+)|
                            modules/view/id/(?P<course_id>\d+)
                        )
                    '''
    _TESTS = [{
        'url': 'https://linuxacademy.com/cp/courses/lesson/course/7971/lesson/2/module/675',
        'info_dict': {
            'id': '7971-2',
            'ext': 'mp4',
            'title': 'What Is Data Science',
            'description': 'md5:c574a3c20607144fb36cb65bdde76c99',
            'timestamp': int,  # The timestamp and upload date changes
            'upload_date': r're:\d+',
            'duration': 304,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Requires Linux Academy account credentials',
    }, {
        'url': 'https://linuxacademy.com/cp/courses/lesson/course/1498/lesson/2',
        'only_matching': True,
    }, {
        'url': 'https://linuxacademy.com/cp/modules/view/id/154',
        'info_dict': {
            'id': '154',
            'title': 'AWS Certified Cloud Practitioner',
            'description': 'md5:a68a299ca9bb98d41cca5abc4d4ce22c',
            'duration': 28835,
        },
        'playlist_count': 41,
        'skip': 'Requires Linux Academy account credentials',
    }, {
        'url': 'https://linuxacademy.com/cp/modules/view/id/39',
        'info_dict': {
            'id': '39',
            'title': 'Red Hat Certified Systems Administrator - RHCSA (EX200) Exam Prep  (legacy)',
            'description': 'md5:0f1d3369e90c3fb14a79813b863c902f',
            'duration': 89280,
        },
        'playlist_count': 73,
        'skip': 'Requires Linux Academy account credentials',
    }]

    _AUTHORIZE_URL = 'https://login.linuxacademy.com/authorize'
    _ORIGIN_URL = 'https://linuxacademy.com'
    _CLIENT_ID = 'KaWxNn1C2Gc7n83W9OFeXltd8Utb5vvx'
    _NETRC_MACHINE = 'linuxacademy'

    def _perform_login(self, username, password):
        def random_string():
            return ''.join(random.choices(
                '0123456789ABCDEFGHIJKLMNOPQRSTUVXYZabcdefghijklmnopqrstuvwxyz-._~', k=32))

        webpage, urlh = self._download_webpage_handle(
            self._AUTHORIZE_URL, None, 'Downloading authorize page', query={
                'client_id': self._CLIENT_ID,
                'response_type': 'token id_token',
                'response_mode': 'web_message',
                'redirect_uri': self._ORIGIN_URL,
                'scope': 'openid email user_impersonation profile',
                'audience': self._ORIGIN_URL,
                'state': random_string(),
                'nonce': random_string(),
            })

        login_data = self._parse_json(
            self._search_regex(
                r'atob\(\s*(["\'])(?P<value>(?:(?!\1).)+)\1', webpage,
                'login info', group='value'), None,
            transform_source=lambda x: compat_b64decode(x).decode('utf-8')
        )['extraParams']

        login_data.update({
            'client_id': self._CLIENT_ID,
            'redirect_uri': self._ORIGIN_URL,
            'tenant': 'lacausers',
            'connection': 'Username-Password-ACG-Proxy',
            'username': username,
            'password': password,
            'sso': 'true',
        })

        login_state_url = urlh.url

        try:
            login_page = self._download_webpage(
                'https://login.linuxacademy.com/usernamepassword/login', None,
                'Downloading login page', data=json.dumps(login_data).encode(),
                headers={
                    'Content-Type': 'application/json',
                    'Origin': 'https://login.linuxacademy.com',
                    'Referer': login_state_url,
                })
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 401:
                error = self._parse_json(e.cause.response.read(), None)
                message = error.get('description') or error['code']
                raise ExtractorError(
                    '%s said: %s' % (self.IE_NAME, message), expected=True)
            raise

        callback_page, urlh = self._download_webpage_handle(
            'https://login.linuxacademy.com/login/callback', None,
            'Downloading callback page',
            data=urlencode_postdata(self._hidden_inputs(login_page)),
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://login.linuxacademy.com',
                'Referer': login_state_url,
            })

        access_token = self._search_regex(
            r'access_token=([^=&]+)', urlh.url,
            'access token', default=None)
        if not access_token:
            access_token = self._parse_json(
                self._search_regex(
                    r'authorizationResponse\s*=\s*({.+?})\s*;', callback_page,
                    'authorization response'), None,
                transform_source=js_to_json)['response']['access_token']

        self._download_webpage(
            'https://linuxacademy.com/cp/login/tokenValidateLogin/token/%s'
            % access_token, None, 'Downloading token validation page')

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        chapter_id, lecture_id, course_id = mobj.group('chapter_id', 'lesson_id', 'course_id')
        item_id = course_id if course_id else '%s-%s' % (chapter_id, lecture_id)

        webpage = self._download_webpage(url, item_id)

        # course path
        if course_id:
            module = self._parse_json(
                self._search_regex(
                    r'window\.module\s*=\s*({(?:(?!};)[^"]|"([^"]|\\")*")+})\s*;', webpage, 'module'),
                item_id)
            entries = []
            chapter_number = None
            chapter = None
            chapter_id = None
            for item in module['items']:
                if not isinstance(item, dict):
                    continue

                def type_field(key):
                    return (try_get(item, lambda x: x['type'][key], compat_str) or '').lower()
                type_fields = (type_field('name'), type_field('slug'))
                # Move to next module section
                if 'section' in type_fields:
                    chapter = item.get('course_name')
                    chapter_id = item.get('course_module')
                    chapter_number = 1 if not chapter_number else chapter_number + 1
                    continue
                # Skip non-lessons
                if 'lesson' not in type_fields:
                    continue
                lesson_url = urljoin(url, item.get('url'))
                if not lesson_url:
                    continue
                title = item.get('title') or item.get('lesson_name')
                description = item.get('md_desc') or clean_html(item.get('description')) or clean_html(item.get('text'))
                entries.append({
                    '_type': 'url_transparent',
                    'url': lesson_url,
                    'ie_key': LinuxAcademyIE.ie_key(),
                    'title': title,
                    'description': description,
                    'timestamp': unified_timestamp(item.get('date')) or unified_timestamp(item.get('created_on')),
                    'duration': parse_duration(item.get('duration')),
                    'chapter': chapter,
                    'chapter_id': chapter_id,
                    'chapter_number': chapter_number,
                })
            return {
                '_type': 'playlist',
                'entries': entries,
                'id': course_id,
                'title': module.get('title'),
                'description': module.get('md_desc') or clean_html(module.get('desc')),
                'duration': parse_duration(module.get('duration')),
            }

        # single video path
        m3u8_url = self._parse_json(
            self._search_regex(
                r'player\.playlist\s*=\s*(\[.+?\])\s*;', webpage, 'playlist'),
            item_id)[0]['file']
        formats = self._extract_m3u8_formats(
            m3u8_url, item_id, 'mp4', entry_protocol='m3u8_native',
            m3u8_id='hls')
        info = {
            'id': item_id,
            'formats': formats,
        }
        lesson = self._parse_json(
            self._search_regex(
                (r'window\.lesson\s*=\s*({.+?})\s*;',
                 r'player\.lesson\s*=\s*({.+?})\s*;'),
                webpage, 'lesson', default='{}'), item_id, fatal=False)
        if lesson:
            info.update({
                'title': lesson.get('lesson_name'),
                'description': lesson.get('md_desc') or clean_html(lesson.get('desc')),
                'timestamp': unified_timestamp(lesson.get('date')) or unified_timestamp(lesson.get('created_on')),
                'duration': parse_duration(lesson.get('duration')),
            })
        if not info.get('title'):
            info['title'] = self._search_regex(
                (r'>Lecture\s*:\s*(?P<value>[^<]+)',
                 r'lessonName\s*=\s*(["\'])(?P<value>(?:(?!\1).)+)\1'), webpage,
                'title', group='value')
        return info
