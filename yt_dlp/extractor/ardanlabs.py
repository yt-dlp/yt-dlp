import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    urlencode_postdata,
)


class ArdanLabsIE(InfoExtractor):
    _VALID_URL = r'https?://courses\.ardanlabs\.com/courses/take/(?P<id>[^/?]+)'
    _NETRC_MACHINE = 'ardanlabs'

    _TESTS = [{
        'url': 'https://courses.ardanlabs.com/courses/take/ultimate-docker-free-preview/lessons/63875769-day-01-part-1',
        'info_dict': {
            'id': '63875769',
            'ext': 'mp4',
            'title': str,
        },
        'skip': 'Requires authentication',
    }]

    def _perform_login(self, username, password):
        """Perform login to ArdanLabs/Thinkific"""
        self.report_login()

        login_url = 'https://courses.ardanlabs.com/users/sign_in'

        # Get the login page first to extract any CSRF tokens if needed
        login_page = self._download_webpage(
            login_url, None, note='Downloading login page',
            data=urlencode_postdata({
                'user[email]': username,
                'user[password]': password,
            }))

        # Check if login was successful by looking for login page indicators
        if 'user_sessions' in login_page or 'Sign In' in login_page:
            raise ExtractorError('Invalid email or password', expected=True)

    def _real_extract(self, url):
        course_slug = self._match_id(url)

        # Request the course API endpoint to get all content
        course_api_url = f'https://courses.ardanlabs.com/api/course_player/v2/courses/{course_slug}'
        try:
            course_response = self._download_json(course_api_url, course_slug, fatal=False)
        except Exception as e:
            raise ExtractorError(f'Failed to fetch course API: {e}', expected=True)

        # Extract course information
        course = course_response.get('course', {})
        course_name = course.get('name', course_slug)

        # Get all contents from the course
        contents = course_response.get('contents', [])

        # Filter for only Lesson type content (videos)
        lessons = [c for c in contents if c.get('contentable_type') == 'Lesson']

        self.to_screen(f'[DEBUG] Found {len(lessons)} lessons in course: {course_name}')

        # Create a playlist with all lessons
        entries = []
        for lesson in lessons:
            lesson_id = lesson.get('id')
            lesson_title = lesson.get('name')

            self.to_screen(f'[DEBUG] Processing lesson: {lesson_title} (ID: {lesson_id})')

            # Request the lessons API endpoint to get video details
            lessons_api_url = f'https://courses.ardanlabs.com/api/course_player/v2/lessons/{lesson.get("contentable_id")}'
            try:
                lessons_response = self._download_json(lessons_api_url, lesson_id, fatal=False)
            except Exception as e:
                self.to_screen(f'[WARNING] Failed to fetch lesson API for {lesson_title}: {e}')
                continue

            # Extract video_url from lessons response
            lesson_data = lessons_response.get('lesson', {})
            video_play_url = lesson_data.get('video_url')

            # Request the video play endpoint to get the Wistia embed HTML
            try:
                video_page = self._download_webpage(video_play_url, lesson_id)
            except Exception as e:
                self.to_screen(f'[WARNING] Failed to download video page for {lesson_title}: {e}')
                continue

            # Extract Wistia media ID from script tag
            wistia_match = re.search(r'https://fast\.wistia\.com/embed/medias/([a-z0-9]{10,12})', video_page)

            if not wistia_match:
                self.to_screen(f'[WARNING] Could not find Wistia media ID for {lesson_title}')
                continue

            wistia_id = wistia_match.group(1)
            wistia_url = f'https://fast.wistia.com/embed/medias/{wistia_id}'

            duration = lesson.get('meta_data', {}).get('duration_in_seconds')

            # Add entry for this lesson
            entry = {
                '_type': 'url_transparent',
                'url': wistia_url,
                'ie_key': 'Wistia',
                'id': str(lesson_id),
                'title': lesson_title,
                'duration': duration,
            }
            entries.append(entry)

        # Return playlist
        return {
            '_type': 'playlist',
            'id': course_slug,
            'title': course_name,
            'entries': entries,
        }
