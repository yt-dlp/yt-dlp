from .common import InfoExtractor
from .vimeo import VimeoIE
from ..utils import (
    int_or_none,
    get_element_by_class,
    get_element_text_and_html_by_tag,
    extract_attributes,
    compat_HTMLParseError
)


class VueSchoolBaseIE(InfoExtractor):
    def _get_course_info_from_lesson_slug(self, lesson_slug, id):
        return self._download_json(f'https://vueschool.io/api/lessons/{lesson_slug}/widgetInfo', video_id=id)


class VueSchoolLessonIE(VueSchoolBaseIE):
    IE_DESC = 'VueSchool Lesson'
    _VALID_URL = r'https?://vueschool\.io/lessons/(?P<id>[a-z0-9\-]+)'
    _TESTS = [{
        'url': 'https://vueschool.io/lessons/getting-started-with-vue-js-and-the-composition-api',
        'info_dict': {
            'id': '665769592',
            'title': 'Getting Started with Vue.js and the Composition API',
            'series_id': 'vue-js-fundamentals-with-the-composition-api',
            'series': 'Vue.js 3 Fundamentals with the Composition API',
            'chapter_number': 1,
            'chapter': 'Getting Started with Vue.js and the Composition API',
            'episode_number': 1,
            'episode': 'Getting Started with Vue.js and the Composition API',
            'duration': 238,
            'uploader_id': str,
            'uploader': str,
            'uploader_url': str,
            'description': str,
            'thumbnail': str
        },
        'params': {
            'skip_download': True,
            'ignore_no_formats_error': True,
        },
    }]

    def _real_extract(self, url):
        lesson_slug = self._match_id(url)
        webpage = self._download_webpage(url, video_id=lesson_slug)

        """
         Attempt to access content behind paywall
        """
        try:
            (_, vimeo_wrapper_element) = get_element_text_and_html_by_tag('vimeo-player', webpage)
            vimeo_player_wrapper_dict = extract_attributes(vimeo_wrapper_element)
            vimeo_id = vimeo_player_wrapper_dict.get(':id')
        except compat_HTMLParseError:
            return self.raise_login_required(msg='This video is only available for paid users.', method='cookies')

        description = get_element_by_class('text xl:text-lg', webpage).strip()

        course_dict = self._get_course_info_from_lesson_slug(lesson_slug, id=lesson_slug)
        course_title = course_dict.get('title')
        course_slug = course_dict.get('slug')

        chapter_number = None
        chapter = None
        lesson_number = None
        lesson_title = None
        duration = None

        for chapter_dict in course_dict.get('chapters'):
            for lesson_dict in chapter_dict.get('lessons'):
                if lesson_slug == lesson_dict.get('slug'):
                    chapter_number = int_or_none(chapter_dict.get('course_order') + 1)
                    chapter = chapter_dict.get('title')
                    lesson_number = int_or_none(lesson_dict.get('course_order'))
                    lesson_title = lesson_dict.get('title')
                    duration = duration
                    break

        vimeo_url = VimeoIE._smuggle_referrer(f'https://player.vimeo.com/video/{vimeo_id}', url)

        return self.url_result(
            vimeo_url, VimeoIE, url_transparent=True,
            video_id=lesson_slug, video_title=lesson_title,
            id=lesson_slug,
            series_id=course_slug, series=course_title,
            chapter_number=chapter_number, chapter=chapter,
            episode_number=lesson_number, episode=lesson_title,
            title=lesson_title,
            description=description,
            duration=duration
        )


class VueSchoolCourseIE(VueSchoolBaseIE):
    IE_DESC = 'VueSchool Course'
    _VALID_URL = r'https?://vueschool\.io/courses/(?P<id>[a-z0-9\-]+)'
    _TESTS = [{
        'url': 'https://vueschool.io/courses/vue-js-fundamentals-with-the-composition-api',
        'info_dict': {
            'id': 'vue-js-fundamentals-with-the-composition-api',
            '_type': 'playlist',
            'title': 'Vue.js 3 Fundamentals with the Composition API',
        },
        'params': {
            'skip_download': True,
        }
    }]

    def _real_extract(self, url):
        course_slug = self._match_id(url)
        webpage = self._download_webpage(url, video_id=course_slug)

        lesson_slugs = self._html_search_regex(r'https?://vueschool\.io/lessons/(?P<lesson_slug>[0-9a-z\-]+)', webpage, name='lesson_slug')

        course_dict = self._get_course_info_from_lesson_slug(lesson_slugs, id=course_slug)
        course_title = course_dict.get('title')
        course_slug = course_dict.get('slug')
        lessons = [lesson for chapter in course_dict.get('chapters') for lesson in chapter.get('lessons')]

        return {
            '_type': 'playlist',
            'title': course_title,
            'id': course_slug,
            'entries': [self.url_result('https://vueschool.io/lessons/%s' % lesson.get('slug'), VueSchoolLessonIE) for lesson in lessons]
        }
