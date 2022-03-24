# coding: utf-8

import re

from .common import InfoExtractor

from ..utils import (
    qualities
)


class ITProTVIE(InfoExtractor):
    _VALID_URL = r'https://app.itpro.tv/course/([0-9a-z-]+)/(?P<id>[0-9a-z-]+)'
    _TESTS = [
    {
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

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        course_name = re.match(r'https?://.*/course/(?P<course_name>[0-9a-z-]+)/.*', url).group(1)
        jwt = self._search_regex(r'{"passedToken":"([A-Za-z0-9-_]*\.[A-Za-z0-9-_]*\.[A-Za-z0-9-_]+)",', webpage, 'jwt')

        if jwt:
            headers = {'Authorization': 'Bearer ' + jwt}
            course_api = self._download_json(f'https://api.itpro.tv/api/urza/v3/consumer-web/course?url={course_name}&brand=00002560-0000-3fa9-0000-1d61000035f3', course_name, headers=headers, note='Fetching data from course API')

        course = course_api['course']

        episode = course_api['currentEpisode']

        title = episode['title']
        description = episode['description']
        video_url = episode['jwVideo1080Embed']
        thumbnail = episode['thumbnail']
        chapter = episode['topic']

        for i in range(len(course['topics'])):
            if course['topics'][i]['id'] == chapter:
                chapter_name = course['topics'][i]['title']
                chapter_id = course['topics'][i]['id']
                chapter_number = i + 1

        QUALITIES = qualities(['low', 'medium', 'high', 'veryhigh'])

        info_dict = {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'formats': [
                {'url': episode['jwVideo320Embed'], 'height': 320, 'quality': QUALITIES('low')},
                {'url': episode['jwVideo480Embed'], 'height': 480, 'quality': QUALITIES('medium')},
                {'url': episode['jwVideo720Embed'], 'height': 720, 'quality': QUALITIES('high')},
                {'url': episode['jwVideo1080Embed'], 'height': 1080, 'quality': QUALITIES('verhigh')}
            ],
            'duration': episode['length'],

            'series': course['name'],
            'series_id': course['url'],
            'availability': self._availability(
                needs_premium=False, needs_subscription=False, needs_auth=True,
                is_private=False, is_unlisted=False),
            'chapter': chapter_name,
            'chapter_number': chapter_number,
            'chapter_id': chapter_id
        }

        if episode['enCaptionData']:
            info_dict['subtitles'] = {
                    'en':
                        [
                            {
                                'data': episode['enCaptionData'],
                                'ext': 'vtt'
                            }
                        ]
                    }

        return info_dict

class ITProTVCourseIE(InfoExtractor):
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

        jwt = self._search_regex(r'{"passedToken":"([A-Za-z0-9-_]*\.[A-Za-z0-9-_]*\.[A-Za-z0-9-_]+)",', webpage, 'jwt')

        if jwt:
            headers = {'Authorization': 'Bearer ' + jwt}
            course_api = self._download_json(f'https://api.itpro.tv/api/urza/v3/consumer-web/course?url={course_id}&brand=00002560-0000-3fa9-0000-1d61000035f3', course_id, headers=headers, note='Fetching data from course API')

        course = course_api['course']

        entries = []

        for episode in course['episodes']:
            entry = {
                '_type': 'url_transparent',
                'ie_key': 'ITProTV',
                'url': url + '/' + episode['url'],
                'title': episode['title']
            }
            entries.append(entry)

        return self.playlist_result(entries, playlist_id=course_id, playlist_title=course['name'], playlist_description=course['description'])