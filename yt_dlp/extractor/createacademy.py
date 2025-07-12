import json
import re

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    get_element_html_by_id,
    traverse_obj,
)


class CreateAcademyIE(InfoExtractor):
    _VALID_URL = r'https://www.createacademy.com/(?:[^/]+/)*lessons/(?P<id>[^/?#]+)'

    _TESTS = [
        {
            'url': 'https://www.createacademy.com/courses/dan-pearson/lessons/meet-dan',
            'info_dict': {
                'id': '265',
                'ext': 'mp4',
                'file_prefix': 'Create Academy - s10e01',
                'title': 'Meet Dan',
                'description': 'md5:48c8af37219020571a84d5f406e75d86',
                'display_id': 'meet-dan',
                'chapter': 'Introduction',
                'chapter_id': '34',
                'course_id': '10',
                'chapter_number': 1,
                'thumbnail': 'https://cf-images.eu-west-1.prod.boltdns.net/v1/static/6222962662001/22f75006-c49f-4d95-8673-1b60df4223d2/45d953e0-fa58-4cb6-9217-1c7b3c80c932/1280x720/match/image.jpg',
            },
        },
    ]

    def _get_lesson_metadata(self, data, lesson_id):
        course = traverse_obj(data, ('props', 'course'))
        prefix = 'Create Academy - s' + str(course.get('id')).zfill(2) + 'e'

        sections = traverse_obj(course, ('curriculum', 'sections'))

        for section in sections:
            for lesson in section.get('lessons'):
                if lesson.get('id') == lesson_id:
                    return {
                        'section': section,
                        'file_prefix': prefix + str(lesson.get('number')).zfill(2),
                        'title': lesson.get('title').strip(),
                    }

        return {
            'section': {
                'id': 0,
                'number': 0,
                'title': '',
            },
            'file_prefix': 'Create Academy',
            'title': traverse_obj(data, ('props', 'lesson', 'title')).strip(),
        }

    def _get_policy_key(self, data, video_id):
        bc = traverse_obj(data, ('props', 'brightcove'))
        accountId = bc.get('accountId')
        playerId = bc.get('playerId')

        playerData = self._download_webpage(f'https://players.brightcove.net/{accountId}/{playerId}_default/index.min.js', video_id, 'Retrieving policy key')
        obj = re.search(r'{policyKey:"(.*?)"}', playerData)
        key = re.search(r'"(.*?)"', obj.group())

        return key.group().replace('"', '')

    def _get_manifest_url(self, data, video_id):
        host_video_id = traverse_obj(data, ('props', 'lesson', 'video', 'host_video_id'))
        accountId = traverse_obj(data, ('props', 'brightcove', 'accountId'))
        policyKey = self._get_policy_key(data, video_id)

        manifest_data = self._download_json(f'https://edge.api.brightcove.com/playback/v1/accounts/{accountId}/videos/{host_video_id}', video_id, 'Retrieving manifest URL', headers={'accept': f'application/json;pk={policyKey}'})

        for source in manifest_data.get('sources'):
            if 'master.m3u8' in source.get('src'):
                return source.get('src')

    def _get_page_data(self, url, video_id):
        webpage = self._download_webpage(url, video_id)

        page_elem = get_element_html_by_id('app', webpage)
        attributes = extract_attributes(page_elem)

        return json.loads(attributes.get('data-page'))

    def _real_extract(self, url):
        video_id = url.split('/')[-1]
        data = self._get_page_data(url, video_id)

        lesson = traverse_obj(data, ('props', 'lesson'))
        createacademy_id = lesson.get('id')

        # get media from manifest
        manifestUrl = self._get_manifest_url(data, video_id)

        formats, subtitles = [], {}
        fmts, subs = self._extract_m3u8_formats_and_subtitles(manifestUrl, str(createacademy_id), 'mp4')

        formats.extend(fmts)
        self._merge_subtitles(subs, target=subtitles)

        lesson_metadata = self._get_lesson_metadata(data, createacademy_id)
        section = lesson_metadata.get('section')

        return {
            'id': str(createacademy_id),
            'file_prefix': lesson_metadata.get('file_prefix'),
            'title': lesson_metadata.get('title'),
            'display_id': video_id,
            'description': lesson.get('description'),
            'thumbnail': lesson.get('thumbnail'),
            'formats': formats,
            'subtitles': subtitles,
            'chapter': section.get('title').strip(),
            'chapter_number': section.get('number'),
            'chapter_id': str(section.get('id')),
            'course_id': str(traverse_obj(data, ('props', 'course', 'id'))).zfill(2),
        }


class CreateAcademyCourseIE(CreateAcademyIE):
    _VALID_URL = r'https://www.createacademy.com/courses/(?!.*\/lessons\/)(?P<id>[^/?#]+)'

    _TESTS = [
        {
            'url': 'https://www.createacademy.com/courses/dan-pearson',
            'info_dict': {
                'id': '265',
                'ext': 'mp4',
                'chapter_id': '34',
                'description': 'md5:48c8af37219020571a84d5f406e75d86',
                'chapter_number': 1,
                'thumbnail': 'https://cf-images.eu-west-1.prod.boltdns.net/v1/static/6222962662001/22f75006-c49f-4d95-8673-1b60df4223d2/45d953e0-fa58-4cb6-9217-1c7b3c80c932/1280x720/match/image.jpg',
                'file_prefix': 'Create Academy - s10e01',
                'title': 'Meet Dan',
                'display_id': 'meet-dan',
                'course_id': '10',
                'chapter': 'Introduction',
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._get_page_data(url, video_id)

        # iterate lessons
        entries = []
        sections = traverse_obj(data, ('props', 'curriculum', 'sections'))

        for section in sections:
            for lesson in section.get('lessons'):
                entries.append(super()._real_extract('https://www.createacademy.com' + lesson.get('lessonPath')))

        return {
            '_type': 'playlist',
            'title': traverse_obj(data, ('props', 'course', 'name')),
            'entries': entries,
        }
