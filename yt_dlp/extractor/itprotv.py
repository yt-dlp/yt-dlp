# coding: utf-8

import re

from .common import InfoExtractor

from ..utils import (
    qualities,
    traverse_obj
)


class ITProTVIE(InfoExtractor):
    _VALID_URL = r'https://app.itpro.tv/course/([0-9a-z-]+)/(?P<id>[0-9a-z-]+)'
    _TESTS = [{
        'url': 'https://app.itpro.tv/course/guided-tour/introductionitprotv',
        'md5': 'bca4a28c2667fd1a63052e71a94bb88c',
        'info_dict': {
            'id': 'introductionitprotv',
            'ext': 'mp4',
            'title': 'An Introduction to ITProTV 101',
            'thumbnail': 'https://itprotv-image-bucket.s3.amazonaws.com/getting-started/itprotv-101-introduction-PGM.11_39_56_02.Still001.png',
            'description': 'Welcome to ITProTV! The guided tour you are about to participate in has been assembled to introduce you to ITProTV and show you many of the features available as part of ITProTV.',
            'duration': 269,
            'series': 'ITProTV 101',
            'series_id': 'guided-tour',
            'availability': 'needs_auth',
            'chapter': 'ITProTV 101',
            'chapter_number': 1,
            'chapter_id': '5dbb3de426b46c0010b5d1b6'
        },
        'params': {
            'skip_download': True,
        },
    }
    ]

    def _get_course_api_json(self, webpage, course_name):
        jwt = self._fetch_jwt(webpage)

        if jwt:
            headers = {'Authorization': 'Bearer ' + jwt}
            course_api = self._download_json(
                f'https://api.itpro.tv/api/urza/v3/consumer-web/course?url={course_name}&brand=00002560-0000-3fa9-0000-1d61000035f3',
                course_name, headers=headers, note='Fetching data from course API')

        return course_api

    def _fetch_jwt(self, webpage):
        return self._search_regex(r'{"passedToken":"([A-Za-z0-9-_]*\.[A-Za-z0-9-_]*\.[A-Za-z0-9-_]+)",', webpage, 'jwt')

    def _real_extract(self, url):
        QUALITIES = qualities(['low', 'medium', 'high', 'veryhigh'])

        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        course_name = re.match(r'https?://.*/course/(?P<course_name>[0-9a-z-]+)/.*', url).group(1)
        course_api = self._get_course_api_json(webpage, course_name)

        course = course_api['course']
        episode = course_api['currentEpisode']

        for i in range(len(course.get('topics'))):
            if traverse_obj(course, ('topics', i, 'id'), expected_type=str) == episode.get('topic'):
                chapter_name = traverse_obj(course, ('topics', i, 'title'), expected_type=str)
                chapter_id = traverse_obj(course, ('topics', i, 'id'), expected_type=str)
                chapter_number = i + 1

        return {
            'id': video_id,
            'title': episode['title'],
            'description': episode.get('description'),
            'thumbnail': episode.get('thumbnail'),
            'formats': [
                {'url': episode.get('jwVideo320Embed'), 'height': 320, 'quality': QUALITIES('low')},
                {'url': episode.get('jwVideo480Embed'), 'height': 480, 'quality': QUALITIES('medium')},
                {'url': episode.get('jwVideo720Embed'), 'height': 720, 'quality': QUALITIES('high')},
                {'url': episode.get('jwVideo1080Embed'), 'height': 1080, 'quality': QUALITIES('veryhigh')}
            ],
            'duration': episode.get('length'),
            'series': course.get('name'),
            'series_id': course.get('url'),
            'availability': self._availability(
                needs_premium=False, needs_subscription=False, needs_auth=True,
                is_private=False, is_unlisted=False),
            'chapter': chapter_name,
            'chapter_number': chapter_number,
            'chapter_id': chapter_id
        }


class ITProTVCourseIE(ITProTVIE):
    _VALID_URL = r'https?://app.itpro.tv/course/(?P<id>[0-9a-z-]+)/?'
    _TESTS = [
        {
            'url': 'https://app.itpro.tv/course/guided-tour',
            'info_dict': {
                'id': 'guided-tour',
                'ext': 'mp4',
            },
            'params': {
                'skip_download': True,
            },
        }
    ]

    def _real_extract(self, url):
        course_id = self._match_id(url)
        webpage = self._download_webpage(url, course_id)
        course_api = self._get_course_api_json(webpage, course_id)

        course = course_api['course']

        entries = []
        for episode in course['episodes']:
            entry = {
                '_type': 'url_transparent',
                'ie_key': 'ITProTV',
                'url': url + '/' + episode['url'],
                'title': episode.get('title')
            }
            entries.append(entry)

        return self.playlist_result(
            entries, playlist_id=course_id, playlist_title=course.get('name'), playlist_description=course.get('description'))
