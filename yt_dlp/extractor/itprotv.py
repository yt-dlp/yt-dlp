import re

from .common import InfoExtractor

from ..utils import (
    int_or_none,
    str_or_none,
    traverse_obj,
    urljoin
)


class ITProTVBaseIE(InfoExtractor):
    _ENDPOINTS = {
        'course': 'course?url={}&brand=00002560-0000-3fa9-0000-1d61000035f3',
        'episode': 'brand/00002560-0000-3fa9-0000-1d61000035f3/episode?url={}'
    }

    def _call_api(self, ep, item_id, webpage):
        return self._download_json(
            f'https://api.itpro.tv/api/urza/v3/consumer-web/{self._ENDPOINTS[ep].format(item_id)}',
            item_id, note=f'Fetching {ep} data API',
            headers={'Authorization': f'Bearer {self._fetch_jwt(webpage)}'})[ep]

    def _fetch_jwt(self, webpage):
        return self._search_regex(r'{"passedToken":"([\w-]+\.[\w-]+\.[\w-]+)",', webpage, 'jwt')

    def _check_if_logged_in(self, webpage):
        if re.match(r'{\s*member\s*:\s*null', webpage):
            self.raise_login_required()


class ITProTVIE(ITProTVBaseIE):
    _VALID_URL = r'https://app\.itpro\.tv/course/(?P<course>[\w-]+)/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://app.itpro.tv/course/guided-tour/introductionitprotv',
        'md5': 'bca4a28c2667fd1a63052e71a94bb88c',
        'info_dict': {
            'id': 'introductionitprotv',
            'ext': 'mp4',
            'title': 'An Introduction to ITProTV 101',
            'thumbnail': 'https://itprotv-image-bucket.s3.amazonaws.com/getting-started/itprotv-101-introduction-PGM.11_39_56_02.Still001.png',
            'description': 'md5:b175c2c3061ce35a4dd33865b2c1da4e',
            'duration': 269,
            'series': 'ITProTV 101',
            'series_id': 'guided-tour',
            'availability': 'needs_auth',
            'chapter': 'ITProTV 101',
            'chapter_number': 1,
            'chapter_id': '5dbb3de426b46c0010b5d1b6'
        },
    },
        {
        'url': 'https://app.itpro.tv/course/beyond-tech/job-interview-tips',
        'md5': '101a299b98c47ccf4c67f9f0951defa8',
        'info_dict': {
            'id': 'job-interview-tips',
            'ext': 'mp4',
            'title': 'Job Interview Tips',
            'thumbnail': 'https://s3.amazonaws.com:443/production-itprotv-thumbnails/2f370bf5-294d-4bbe-ab80-c0b5781630ea.png',
            'description': 'md5:30d8ba483febdf89ec85623aad3c3cb6',
            'duration': 267,
            'series': 'Beyond Tech',
            'series_id': 'beyond-tech',
            'availability': 'needs_auth',
            'chapter': 'Job Development',
            'chapter_number': 2,
            'chapter_id': '5f7c78d424330c000edf04d9'
        },
    }]

    def _real_extract(self, url):
        episode_id, course_name = self._match_valid_url(url).group('id', 'course')
        webpage = self._download_webpage(url, episode_id)
        self._check_if_logged_in(webpage)
        course = self._call_api('course', course_name, webpage)
        episode = self._call_api('episode', episode_id, webpage)

        chapter_number, chapter = next((
            (i, topic) for i, topic in enumerate(course.get('topics') or [], 1)
            if traverse_obj(topic, 'id') == episode.get('topic')), {})

        return {
            'id': episode_id,
            'title': episode.get('title'),
            'description': episode.get('description'),
            'thumbnail': episode.get('thumbnail'),
            'formats': [
                {'url': episode[f'jwVideo{h}Embed'], 'height': h}
                for h in (320, 480, 720, 1080) if episode.get(f'jwVideo{h}Embed')
            ],
            'duration': int_or_none(episode.get('length')),
            'series': course.get('name'),
            'series_id': course.get('url'),
            'chapter': str_or_none(chapter.get('title')),
            'chapter_number': chapter_number,
            'chapter_id': str_or_none(chapter.get('id')),
            'subtitles': {
                'en': [{'ext': 'vtt', 'data': episode['enCaptionData']}]
            } if episode.get('enCaptionData') else None,
        }


class ITProTVCourseIE(ITProTVBaseIE):
    _VALID_URL = r'https?://app\.itpro\.tv/course/(?P<id>[\w-]+)/?(?:$|[#?])'
    _TESTS = [
        {
            'url': 'https://app.itpro.tv/course/guided-tour',
            'info_dict': {
                'id': 'guided-tour',
                'description': 'md5:b175c2c3061ce35a4dd33865b2c1da4e',
                'title': 'ITProTV 101',
            },
            'playlist_count': 6
        },
        {
            'url': 'https://app.itpro.tv/course/beyond-tech',
            'info_dict': {
                'id': 'beyond-tech',
                'description': 'md5:44cd99855e7f81a15ce1269bd0621fed',
                'title': 'Beyond Tech'
            },
            'playlist_count': 15
        },
    ]

    def _real_extract(self, url):
        course_id = self._match_id(url)
        webpage = self._download_webpage(url, course_id)
        self._check_if_logged_in(webpage)
        course = self._call_api('course', course_id, webpage)

        entries = [self.url_result(
            urljoin(url, f'{course_id}/{episode["url"]}'), ITProTVIE,
            episode['url'], episode.get('title'), url_transparent=True)
            for episode in course['episodes']]

        return self.playlist_result(
            entries, course_id, course.get('name'), course.get('description'))
