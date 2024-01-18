from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    determine_ext,
    int_or_none,
    try_get,
    unified_timestamp,
    url_or_none,
)


class EggheadBaseIE(InfoExtractor):
    def _call_api(self, path, video_id, resource, fatal=True):
        return self._download_json(
            'https://app.egghead.io/api/v1/' + path,
            video_id, 'Downloading %s JSON' % resource, fatal=fatal)


class EggheadCourseIE(EggheadBaseIE):
    IE_DESC = 'egghead.io course'
    IE_NAME = 'egghead:course'
    _VALID_URL = r'https://(?:app\.)?egghead\.io/(?:course|playlist)s/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://egghead.io/courses/professor-frisby-introduces-composable-functional-javascript',
        'playlist_count': 29,
        'info_dict': {
            'id': '432655',
            'title': 'Professor Frisby Introduces Composable Functional JavaScript',
            'description': 're:(?s)^This course teaches the ubiquitous.*You\'ll start composing functionality before you know it.$',
        },
    }, {
        'url': 'https://app.egghead.io/playlists/professor-frisby-introduces-composable-functional-javascript',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        series_path = 'series/' + playlist_id
        lessons = self._call_api(
            series_path + '/lessons', playlist_id, 'course lessons')

        entries = []
        for lesson in lessons:
            lesson_url = url_or_none(lesson.get('http_url'))
            if not lesson_url:
                continue
            lesson_id = lesson.get('id')
            if lesson_id:
                lesson_id = compat_str(lesson_id)
            entries.append(self.url_result(
                lesson_url, ie=EggheadLessonIE.ie_key(), video_id=lesson_id))

        course = self._call_api(
            series_path, playlist_id, 'course', False) or {}

        playlist_id = course.get('id')
        if playlist_id:
            playlist_id = compat_str(playlist_id)

        return self.playlist_result(
            entries, playlist_id, course.get('title'),
            course.get('description'))


class EggheadLessonIE(EggheadBaseIE):
    IE_DESC = 'egghead.io lesson'
    IE_NAME = 'egghead:lesson'
    _VALID_URL = r'https://(?:app\.)?egghead\.io/(?:api/v1/)?lessons/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://egghead.io/lessons/javascript-linear-data-flow-with-container-style-types-box',
        'info_dict': {
            'id': '1196',
            'display_id': 'javascript-linear-data-flow-with-container-style-types-box',
            'ext': 'mp4',
            'title': 'Create linear data flow with container style types (Box)',
            'description': 'md5:9aa2cdb6f9878ed4c39ec09e85a8150e',
            'thumbnail': r're:^https?:.*\.jpg$',
            'timestamp': 1481296768,
            'upload_date': '20161209',
            'duration': 304,
            'view_count': 0,
            'tags': 'count:2',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://egghead.io/api/v1/lessons/react-add-redux-to-a-react-application',
        'only_matching': True,
    }, {
        'url': 'https://app.egghead.io/lessons/javascript-linear-data-flow-with-container-style-types-box',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        lesson = self._call_api(
            'lessons/' + display_id, display_id, 'lesson')

        lesson_id = compat_str(lesson['id'])
        title = lesson['title']

        formats = []
        for _, format_url in lesson['media_urls'].items():
            format_url = url_or_none(format_url)
            if not format_url:
                continue
            ext = determine_ext(format_url)
            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    format_url, lesson_id, 'mp4', m3u8_id='hls', fatal=False))
            elif ext == 'mpd':
                formats.extend(self._extract_mpd_formats(
                    format_url, lesson_id, mpd_id='dash', fatal=False))
            else:
                formats.append({
                    'url': format_url,
                })

        return {
            'id': lesson_id,
            'display_id': display_id,
            'title': title,
            'description': lesson.get('summary'),
            'thumbnail': lesson.get('thumb_nail'),
            'timestamp': unified_timestamp(lesson.get('published_at')),
            'duration': int_or_none(lesson.get('duration')),
            'view_count': int_or_none(lesson.get('plays_count')),
            'tags': try_get(lesson, lambda x: x['tag_list'], list),
            'series': try_get(
                lesson, lambda x: x['series']['title'], compat_str),
            'formats': formats,
        }
