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
    },
        {
        'url': 'https://app.itpro.tv/course/beyond-tech/job-interview-tips',
        'md5': '101a299b98c47ccf4c67f9f0951defa8',
        'info_dict': {
            'id': 'job-interview-tips',
            'ext': 'mp4',
            'title': 'Job Interview Tips',
            'thumbnail': 'https://s3.amazonaws.com:443/production-itprotv-thumbnails/2f370bf5-294d-4bbe-ab80-c0b5781630ea.png',
            'description': "Did you know that preparation is one of the most important aspects of a successful job interview? Just as the interviewer will do their research on you, it's equally as important for you to do your research on the company. In this episode Jo will share with you some key preparation tips and best practices that will hopefully help you nail your next job interview!",
            'duration': 267,
            'series': 'Beyond Tech',
            'series_id': 'beyond-tech',
            'availability': 'needs_auth',
            'chapter': 'Job Development',
            'chapter_number': 2,
            'chapter_id': '5f7c78d424330c000edf04d9'
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

    def _get_episode_api_json(self, webpage, episode_id):
        jwt = self._fetch_jwt(webpage)

        if jwt:
            headers = {'Authorization': 'Bearer ' + jwt}
            episode_api = self._download_json(
                f'https://api.itpro.tv/api/urza/v3/consumer-web/brand/00002560-0000-3fa9-0000-1d61000035f3/episode?url={episode_id}',
                episode_id, headers=headers, note='Fetching data from episode API')

        return episode_api

    def _fetch_jwt(self, webpage):
        return self._search_regex(r'{"passedToken":"([A-Za-z0-9-_]*\.[A-Za-z0-9-_]*\.[A-Za-z0-9-_]+)",', webpage, 'jwt')

    def _check_if_logged_in(self, webpage):
        if '{ member: null' in webpage:
            raise self.raise_login_required(method='cookies')

    def _real_extract(self, url):
        QUALITIES = qualities(['low', 'medium', 'high', 'veryhigh'])

        episode_id = self._match_id(url)
        webpage = self._download_webpage(url, episode_id)
        self._check_if_logged_in(webpage)

        course_name = re.match(r'https?://.*/course/(?P<course_name>[0-9a-z-]+)/.*', url).group(1)
        course_api = self._get_course_api_json(webpage, course_name)
        course = course_api['course']

        episode_api = self._get_episode_api_json(webpage, episode_id)
        episode = episode_api['episode']

        for i in range(len(course.get('topics'))):
            if traverse_obj(course, ('topics', i, 'id'), expected_type=str) == episode.get('topic'):
                chapter_name = traverse_obj(course, ('topics', i, 'title'), expected_type=str)
                chapter_id = traverse_obj(course, ('topics', i, 'id'), expected_type=str)
                chapter_number = i + 1

        return {
            'id': episode_id,
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
            'chapter_id': chapter_id,
            'subtitles': {'en': [{'ext': 'vtt', 'data': episode.get('enCaptionData')}]}
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
        },
        {
            'url': 'https://app.itpro.tv/course/beyond-tech',
            'info_dict': {
                'id': 'beyond-tech',
                'ext': 'mp4',
            },
            'params': {
                'skip_download': True,
            },
        },
    ]

    def _real_extract(self, url):
        course_id = self._match_id(url)
        webpage = self._download_webpage(url, course_id)
        self._check_if_logged_in(webpage)
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
