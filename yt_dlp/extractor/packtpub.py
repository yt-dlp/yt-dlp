import json

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    clean_html,
    ExtractorError,
    # remove_end,
    str_or_none,
    strip_or_none,
    unified_timestamp,
    # urljoin,
)


class PacktPubBaseIE(InfoExtractor):
    # _PACKT_BASE = 'https://www.packtpub.com'
    _STATIC_PRODUCTS_BASE = 'https://static.packt-cdn.com/products/'


class PacktPubIE(PacktPubBaseIE):
    _VALID_URL = r'https?://(?:(?:www\.)?packtpub\.com/mapt|subscription\.packtpub\.com)/video/[^/]+/(?P<course_id>\d+)/(?P<chapter_id>[^/]+)/(?P<id>[^/]+)(?:/(?P<display_id>[^/?&#]+))?'

    _TESTS = [{
        'url': 'https://www.packtpub.com/mapt/video/web-development/9781787122215/20528/20530/Project+Intro',
        'md5': '1e74bd6cfd45d7d07666f4684ef58f70',
        'info_dict': {
            'id': '20530',
            'ext': 'mp4',
            'title': 'Project Intro',
            'thumbnail': r're:(?i)^https?://.*\.jpg',
            'timestamp': 1490918400,
            'upload_date': '20170331',
        },
    }, {
        'url': 'https://subscription.packtpub.com/video/web_development/9781787122215/20528/20530/project-intro',
        'only_matching': True,
    }, {
        'url': 'https://subscription.packtpub.com/video/programming/9781838988906/p1/video1_1/business-card-project',
        'only_matching': True,
    }]
    _NETRC_MACHINE = 'packtpub'
    _TOKEN = None

    def _perform_login(self, username, password):
        try:
            self._TOKEN = self._download_json(
                'https://services.packtpub.com/auth-v1/users/tokens', None,
                'Downloading Authorization Token', data=json.dumps({
                    'username': username,
                    'password': password,
                }).encode())['data']['access']
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status in (400, 401, 404):
                message = self._parse_json(e.cause.response.read().decode(), None)['message']
                raise ExtractorError(message, expected=True)
            raise

    def _real_extract(self, url):
        course_id, chapter_id, video_id, display_id = self._match_valid_url(url).groups()

        headers = {}
        if self._TOKEN:
            headers['Authorization'] = 'Bearer ' + self._TOKEN
        try:
            video_url = self._download_json(
                'https://services.packtpub.com/products-v1/products/%s/%s/%s' % (course_id, chapter_id, video_id), video_id,
                'Downloading JSON video', headers=headers)['data']
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 400:
                self.raise_login_required('This video is locked')
            raise

        # TODO: find a better way to avoid duplicating course requests
        # metadata = self._download_json(
        #     '%s/products/%s/chapters/%s/sections/%s/metadata'
        #     % (self._MAPT_REST, course_id, chapter_id, video_id),
        #     video_id)['data']

        # title = metadata['pageTitle']
        # course_title = metadata.get('title')
        # if course_title:
        #     title = remove_end(title, ' - %s' % course_title)
        # timestamp = unified_timestamp(metadata.get('publicationDate'))
        # thumbnail = urljoin(self._PACKT_BASE, metadata.get('filepath'))

        return {
            'id': video_id,
            'url': video_url,
            'title': display_id or video_id,  # title,
            # 'thumbnail': thumbnail,
            # 'timestamp': timestamp,
        }


class PacktPubCourseIE(PacktPubBaseIE):
    _VALID_URL = r'(?P<url>https?://(?:(?:www\.)?packtpub\.com/mapt|subscription\.packtpub\.com)/video/[^/]+/(?P<id>\d+))'
    _TESTS = [{
        'url': 'https://www.packtpub.com/mapt/video/web-development/9781787122215',
        'info_dict': {
            'id': '9781787122215',
            'title': 'Learn Nodejs by building 12 projects [Video]',
            'description': 'md5:489da8d953f416e51927b60a1c7db0aa',
        },
        'playlist_count': 90,
    }, {
        'url': 'https://subscription.packtpub.com/video/web_development/9781787122215',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if PacktPubIE.suitable(url) else super(
            PacktPubCourseIE, cls).suitable(url)

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        url, course_id = mobj.group('url', 'id')

        course = self._download_json(
            self._STATIC_PRODUCTS_BASE + '%s/toc' % course_id, course_id)
        metadata = self._download_json(
            self._STATIC_PRODUCTS_BASE + '%s/summary' % course_id,
            course_id, fatal=False) or {}

        entries = []
        for chapter_num, chapter in enumerate(course['chapters'], 1):
            chapter_id = str_or_none(chapter.get('id'))
            sections = chapter.get('sections')
            if not chapter_id or not isinstance(sections, list):
                continue
            chapter_info = {
                'chapter': chapter.get('title'),
                'chapter_number': chapter_num,
                'chapter_id': chapter_id,
            }
            for section in sections:
                section_id = str_or_none(section.get('id'))
                if not section_id or section.get('contentType') != 'video':
                    continue
                entry = {
                    '_type': 'url_transparent',
                    'url': '/'.join([url, chapter_id, section_id]),
                    'title': strip_or_none(section.get('title')),
                    'description': clean_html(section.get('summary')),
                    'thumbnail': metadata.get('coverImage'),
                    'timestamp': unified_timestamp(metadata.get('publicationDate')),
                    'ie_key': PacktPubIE.ie_key(),
                }
                entry.update(chapter_info)
                entries.append(entry)

        return self.playlist_result(
            entries, course_id, metadata.get('title'),
            clean_html(metadata.get('about')))
