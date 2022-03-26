# coding: utf-8

import re

from .common import InfoExtractor

from ..utils import (
    int_or_none,
    traverse_obj,
    urljoin
)


class ITProTVBaseIE(InfoExtractor):
    def _get_course_api_json(self, webpage, course_name):
        jwt = self._fetch_jwt(webpage)

        if jwt:
            headers = {'Authorization': f'Bearer {jwt}'}
            course_api = self._download_json(
                f'https://api.itpro.tv/api/urza/v3/consumer-web/course?url={course_name}&brand=00002560-0000-3fa9-0000-1d61000035f3',
                course_name, headers=headers, note='Fetching data from course API')

            return course_api

    def _get_episode_api_json(self, webpage, episode_id):
        jwt = self._fetch_jwt(webpage)

        if jwt:
            headers = {'Authorization': f'Bearer {jwt}'}
            episode_api = self._download_json(
                f'https://api.itpro.tv/api/urza/v3/consumer-web/brand/00002560-0000-3fa9-0000-1d61000035f3/episode?url={episode_id}',
                episode_id, headers=headers, note='Fetching data from episode API')

            return episode_api

    def _fetch_jwt(self, webpage):
        return self._search_regex(r'{"passedToken":"([\w-]+\.[\w-]+\.[\w-]+)",', webpage, 'jwt')

    def _check_if_logged_in(self, webpage):
        if re.match(r'{\s*member\s*:\s*null', webpage):
            raise self.raise_login_required()


class ITProTVIE(ITProTVBaseIE):
    _VALID_URL = r'https://app.itpro.tv/course/([\w-]+)/(?P<id>[\w-]+)'
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
        episode_id = self._match_id(url)
        webpage = self._download_webpage(url, episode_id)
        self._check_if_logged_in(webpage)

        course_name = self._search_regex(r'https?://.+/course/(?P<course_name>[\w-]+)/[\w-]+', url, 'course_name')
        course = self._get_course_api_json(webpage, course_name)['course']

        episode = self._get_episode_api_json(webpage, episode_id)['episode']

        for i in range(len(course.get('topics'))):
            if traverse_obj(course, ('topics', i, 'id'), expected_type=str) == episode.get('topic'):
                chapter_name = traverse_obj(course, ('topics', i, 'title'), expected_type=str)
                chapter_id = traverse_obj(course, ('topics', i, 'id'), expected_type=str)
                chapter_number = i + 1

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
            'availability': self._availability(
                needs_premium=False, needs_subscription=False, needs_auth=True,
                is_private=False, is_unlisted=False),
            'chapter': chapter_name,
            'chapter_number': chapter_number,
            'chapter_id': chapter_id,
            'subtitles': {
                'en': [{'ext': 'vtt', 'data': episode['enCaptionData']}]
            } if episode.get('enCaptionData') else None,
        }


class ITProTVCourseIE(ITProTVBaseIE):
    _VALID_URL = r'https?://app.itpro.tv/course/(?P<id>[\w-]+)/?(?:$|[#?])'
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
        course = self._get_course_api_json(webpage, course_id)['course']

        entries = [self.url_result(
            urljoin(url, f"{course_id}/{episode['url']}"), ie='ITProTV', video_id=episode['url'], title=episode.get('title'), url_transparent=True)
            for episode in course['episodes']]

        return self.playlist_result(
            entries, course_id, course.get('name'), course.get('description'))
