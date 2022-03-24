# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor

from ..utils import (
    sanitized_Request,
    urlencode_postdata,
    qualities
)


class ITProTVIE(InfoExtractor):
    _VALID_URL = r'https://app.itpro.tv/course/([0-9a-z-]+)/(?P<id>[0-9a-z-]+)'
    _TESTS = [
        {
        'url': 'https://app.itpro.tv/course/accelerated-cissp-2021/securityrisk-keycissp',
        'md5': '0d8f96562ff3b180ba1dabda7093d822',
        'info_dict': {
            'id': 'securityrisk-keycissp',
            'ext': 'mp4',
            'title': 'Security and Risk Management Key Points',
            'thumbnail': r're:^https?://.*\.png$',
            'description': 'In this episode, we will be reviewing the Domain 1, Security and Risk Management key points that you need to focus on for the CISSP exam. After watching this episode you will be able to understand and identify the key points and items from Domain 1 that need to be mastered as part of your preparation to take and pass the CISSP exam.',
            'duration': 1100,
            'series': 'Certified Information Systems Security Professional - CISSP 2021',
            'series_id': 'accelerated-cissp-2021',
            'availability': 'needs_auth',
            'chapter': 'Security and Risk Management',
            'chapter_number': 1,
            'chapter_id': '5ffe09ef8a8eba000ee1947e'
        },
        'params': {
                'skip_download': True,
            },
    },
    {
        'url': 'https://app.itpro.tv/course/guided-tour/introductionitprotv',
        'md5': 'bca4a28c2667fd1a63052e71a94bb88c',
        'info_dict': {
            'id': 'introductionitprotv',
            'ext': 'mp4',
            'title': 'An Introduction to ITProTV 101',
            'thumbnail': r're:^https?://.*\.png$',
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

        return {
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
            'subtitles': {
                'en':
                    [
                        {
                            'data': episode['enCaptionData'],
                            'ext': 'vtt'
                        }
                    ]
                },
            'series': course['name'],
            'series_id': course['url'],
            'availability': self._availability(
                needs_premium=False, needs_subscription=False, needs_auth=True,
                is_private=False, is_unlisted=False),
            'chapter': chapter_name,
            'chapter_number': chapter_number,
            'chapter_id': chapter_id
        }