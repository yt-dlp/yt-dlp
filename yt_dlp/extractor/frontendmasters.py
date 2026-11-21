import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    parse_duration,
    url_or_none,
    urlencode_postdata,
)


class FrontendMastersBaseIE(InfoExtractor):
    _API_BASE = 'https://api.frontendmasters.com/v1/kabuki'
    _LOGIN_URL = 'https://frontendmasters.com/login/'

    _NETRC_MACHINE = 'frontendmasters'

    def _get_subtitles(self, lesson_data, course_data):
        captions_base = "https://captions.frontendmasters.com/assets/courses/"
        lesson_slug = lesson_data.get('slug')
        lesson_index = lesson_data.get('index')
        date_published = course_data.get('datePublished')
        course_slug = course_data.get('slug')

        subtitles_url = f'{captions_base}{date_published}-{course_slug}/{lesson_index}-{lesson_slug}.vtt'

        return {
            'en': [{
                'url': subtitles_url
            }]
        }

    def _perform_login(self, username, password):
        login_page = self._download_webpage(
            self._LOGIN_URL, None, 'Downloading login page')

        login_form = self._hidden_inputs(login_page)

        login_form.update({
            'username': username,
            'password': password,
        })

        post_url = self._search_regex(
            r'<form[^>]+action=(["\'])(?P<url>.+?)\1', login_page,
            'post_url', default=self._LOGIN_URL, group='url')

        if not post_url.startswith('http'):
            post_url = urllib.parse.urljoin(self._LOGIN_URL, post_url)

        response = self._download_webpage(
            post_url, None, 'Logging in', data=urlencode_postdata(login_form),
            headers={'Content-Type': 'application/x-www-form-urlencoded'})

        # Successful login
        if any(p in response for p in (
                'wp-login.php?action=logout', '>Logout')):
            return

        error = self._html_search_regex(
            r'class=(["\'])(?:(?!\1).)*\bMessageAlert\b(?:(?!\1).)*\1[^>]*>(?P<error>[^<]+)<',
            response, 'error message', default=None, group='error')
        if error:
            raise ExtractorError(f'Unable to login: {error}', expected=True)
        raise ExtractorError('Unable to log in')


class FrontendMastersPageBaseIE(FrontendMastersBaseIE):
    def _download_course(self, course_name, url):
        return self._download_json(
            f'{self._API_BASE}/courses/{course_name}', course_name,
            'Downloading course JSON', headers={'Referer': url})

    @staticmethod
    def _extract_chapters(course):
        chapters = []
        lesson_elements = course.get('lessonElements')
        if isinstance(lesson_elements, list):
            chapters = [url_or_none(e) for e in lesson_elements if url_or_none(e)]
        return chapters

    @staticmethod
    def _extract_lesson(chapters, lesson_id, lesson, subtitles):
        title = lesson.get('title') or lesson_id
        display_id = lesson.get('slug')
        description = lesson.get('description')
        thumbnail = lesson.get('thumbnail')

        chapter_number = None
        index = lesson.get('index')
        element_index = lesson.get('elementIndex')
        if (isinstance(index, int) and isinstance(element_index, int)
                and index < element_index):
            chapter_number = element_index - index
        chapter = (chapters[chapter_number - 1]
                   if chapter_number - 1 < len(chapters) else None)

        duration = None
        timestamp = lesson.get('timestamp')
        if isinstance(timestamp, str):
            mobj = re.search(
                r'(?P<start>\d{1,2}:\d{1,2}:\d{1,2})\s*-(?P<end>\s*\d{1,2}:\d{1,2}:\d{1,2})',
                timestamp)
            if mobj:
                duration = parse_duration(mobj.group('end')) - parse_duration(
                    mobj.group('start'))

        return {
            '_type': 'url_transparent',
            'url': f'frontendmasters:{lesson_id}',
            'ie_key': FrontendMastersIE.ie_key(),
            'id': lesson_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'chapter': chapter,
            'chapter_number': chapter_number,
            'subtitles': subtitles
        }


class FrontendMastersIE(FrontendMastersBaseIE):
    _VALID_URL = r'(?:frontendmasters:|https?://api\.frontendmasters\.com/v\d+/kabuki/video/)(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://api.frontendmasters.com/v1/kabuki/video/a2qogef6ba',
        'md5': '7f161159710d6b7016a4f4af6fcb05e2',
        'info_dict': {
            'id': 'a2qogef6ba',
            'ext': 'mp4',
            'title': 'a2qogef6ba',
        },
        'skip': 'Requires FrontendMasters account credentials',
    }, {
        'url': 'frontendmasters:a2qogef6ba',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        lesson_id = self._match_id(url)

        source_url = f'{self._API_BASE}/video/{lesson_id}/source'
        headers = {
            'Referer': 'https://frontendmasters.com/',
        }
        cookies = self._get_cookies("https://frontendmasters.com/")
        fem_auth_mod = cookies.get('fem_auth_mod')
        if fem_auth_mod:
            headers['Cookie'] = f'fem_auth_mod={fem_auth_mod.value}'

        json_response = self._download_json(
            source_url,
            'Downloading source JSON', query={
                'f': 'm3u8'
            }, headers=headers)

        m3u8_url = json_response.get('url')

        formats = self._extract_m3u8_formats(m3u8_url, lesson_id)

        return {
            'id': lesson_id,
            'title': lesson_id,
            'formats': formats,
        }


class FrontendMastersLessonIE(FrontendMastersPageBaseIE):
    _VALID_URL = r'https?://(?:www\.)?frontendmasters\.com/courses/(?P<course_name>[^/]+)/(?P<lesson_name>[^/]+)'
    _TEST = {
        'url': 'https://frontendmasters.com/courses/web-development/tools',
        'info_dict': {
            'id': 'a2qogef6ba',
            'display_id': 'tools',
            'ext': 'mp4',
            'title': 'Tools',
            'description': 'md5:82c1ea6472e88ed5acd1829fe992e4f7',
            'thumbnail': r're:^https?://.*\.jpg$',
            'chapter': 'Introduction',
            'chapter_number': 1,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Requires FrontendMasters account credentials',
    }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        course_name, lesson_name = mobj.group('course_name', 'lesson_name')

        course = self._download_course(course_name, url)

        lesson_id, lesson = next(
            (video_id, data)
            for video_id, data in course['lessonData'].items()
            if data.get('slug') == lesson_name)

        subtitles = self.extract_subtitles(lesson, course)
        chapters = self._extract_chapters(course)
        return self._extract_lesson(chapters, lesson_id, lesson, subtitles)


class FrontendMastersCourseIE(FrontendMastersPageBaseIE):
    _VALID_URL = r'https?://(?:www\.)?frontendmasters\.com/courses/(?P<id>[^/]+)'
    _TEST = {
        'url': 'https://frontendmasters.com/courses/web-development/',
        'info_dict': {
            'id': 'web-development',
            'title': 'Introduction to Web Development',
            'description': 'md5:9317e6e842098bf725d62360e52d49a6',
        },
        'playlist_count': 81,
        'skip': 'Requires FrontendMasters account credentials',
    }

    @classmethod
    def suitable(cls, url):
        return False if FrontendMastersLessonIE.suitable(url) else super(
            FrontendMastersBaseIE, cls).suitable(url)

    def _real_extract(self, url):
        course_name = self._match_id(url)

        course = self._download_course(course_name, url)

        chapters = self._extract_chapters(course)

        lessons = sorted(
            course['lessonData'].values(), key=lambda data: data['index'])

        entries = []
        for lesson in lessons:
            lesson_name = lesson.get('slug')
            lesson_id = lesson.get('hash') or lesson.get('statsId')
            subtitles = self.extract_subtitles(lesson, course)
            if not lesson_id or not lesson_name:
                continue
            entries.append(self._extract_lesson(chapters, lesson_id, lesson, subtitles))

        title = course.get('title')
        description = course.get('description')

        return self.playlist_result(entries, course_name, title, description)
