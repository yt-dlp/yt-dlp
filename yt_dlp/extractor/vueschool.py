from .common import InfoExtractor
from .vimeo import VimeoIE
from ..compat import compat_HTMLParseError
from ..utils import (
    extract_attributes,
    get_element_by_class,
    get_element_text_and_html_by_tag,
    int_or_none,
    traverse_obj,
    try_call,
)


class VueSchoolBaseIE(InfoExtractor):
    def _get_course_info_from_lesson_slug(self, lesson_slug, id):
        return self._download_json(
            f'https://vueschool.io/api/lessons/{lesson_slug}/widgetInfo', video_id=id)


class VueSchoolLessonIE(VueSchoolBaseIE):
    IE_DESC = 'VueSchool Lesson'
    _VALID_URL = r'https?://vueschool\.io/lessons/(?P<id>[a-z0-9\-]+)'
    _TESTS = [{
        'url': 'https://vueschool.io/lessons/getting-started-with-vue-js-and-the-composition-api',
        'info_dict': {
            'ext': 'mp4',
            'id': '665769592',
            'title': 'Getting Started with Vue.js and the Composition API',
            'series_id': 'vue-js-fundamentals-with-the-composition-api',
            'series': 'Vue.js 3 Fundamentals with the Composition API',
            'chapter_number': 1,
            'chapter': 'Getting Started with Vue.js and the Composition API',
            'episode_number': 1,
            'episode': 'Getting Started with Vue.js and the Composition API',
            'duration': 238,
            'thumbnail': 'startswith:https://i.vimeocdn.com/video/',
            'uploader_id': 'user62798049',
            'description': 'md5:b634d76886075d7006349365df6bfe9f',
            'uploader_url': 'https://vimeo.com/user62798049',
            'uploader': 'Alex Kyriakidis',
            'display_id': 'getting-started-with-vue-js-and-the-composition-api',
        },
    }]

    def _real_extract(self, url):
        lesson_slug = self._match_id(url)
        webpage = self._download_webpage(url, video_id=lesson_slug)

        try:
            _, player = get_element_text_and_html_by_tag('vimeo-player', webpage)
            vimeo_id = extract_attributes(player)[':id']
        except compat_HTMLParseError:
            return self.raise_login_required()

        course = self._get_course_info_from_lesson_slug(lesson_slug, lesson_slug)
        for chapter in traverse_obj(course, ('chapters', ...)):
            for lesson in traverse_obj(chapter, ('lessons', ...)):
                if lesson_slug == lesson.get('slug'):
                    break
            else:
                chapter, lesson = {}, {}

        return {
            '_type': 'url_transparent',
            'url': VimeoIE._smuggle_referrer(f'https://player.vimeo.com/video/{vimeo_id}', url),
            'ie_key': VimeoIE.ie_key(),
            'display_id': lesson_slug,
            'series_id': course.get('slug'),
            'series': course.get('title'),
            'chapter_number': try_call(lambda: chapter['course_order'] + 1),
            'chapter': chapter.get('title'),
            'episode_number': int_or_none(lesson.get('course_order')),
            'episode': lesson.get('title'),
            'title': lesson.get('title'),
            'description': get_element_by_class('text xl:text-lg', webpage).strip(),
        }


class VueSchoolCourseIE(VueSchoolBaseIE):
    IE_DESC = 'VueSchool Course'
    _VALID_URL = r'https?://vueschool\.io/courses/(?P<id>[a-z0-9\-]+)'
    _TESTS = [{
        'url': 'https://vueschool.io/courses/vue-js-fundamentals-with-the-composition-api',
        'playlist_count': 14,
        'info_dict': {
            'id': 'vue-js-fundamentals-with-the-composition-api',
            'title': 'Vue.js 3 Fundamentals with the Composition API',
        },
    }]

    def _real_extract(self, url):
        course_slug = self._match_id(url)
        webpage = self._download_webpage(url, course_slug)

        lesson_slugs = self._html_search_regex(
            r'https?://vueschool\.io/lessons/(?P<lesson_slug>[\w\-]+)', webpage, 'lesson slug')
        course = self._get_course_info_from_lesson_slug(lesson_slugs, course_slug)

        return {
            '_type': 'playlist',
            'id': course.get('slug'),
            'title': course.get('title'),
            'entries': [self.url_result(f'https://vueschool.io/lessons/{lesson["slug"]}', VueSchoolLessonIE)
                        for lesson in traverse_obj(course, ('chapters', ..., 'lessons', ...))]
        }
