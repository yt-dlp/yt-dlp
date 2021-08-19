# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    urlencode_postdata,
    urljoin,
)


class LinkedInLearningBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'linkedin'
    _LOGIN_URL = 'https://www.linkedin.com/uas/login?trk=learning'

    def _call_api(self, course_slug, fields, video_slug=None, resolution=None):
        query = {
            'courseSlug': course_slug,
            'fields': fields,
            'q': 'slugs',
        }
        sub = ''
        if video_slug:
            query.update({
                'videoSlug': video_slug,
                'resolution': '_%s' % resolution,
            })
            sub = ' %dp' % resolution
        api_url = 'https://www.linkedin.com/learning-api/detailedCourses'
        return self._download_json(
            api_url, video_slug, 'Downloading%s JSON metadata' % sub, headers={
                'Csrf-Token': self._get_cookies(api_url)['JSESSIONID'].value,
            }, query=query)['elements'][0]

    def _get_urn_id(self, video_data):
        urn = video_data.get('urn')
        if urn:
            mobj = re.search(r'urn:li:lyndaCourse:\d+,(\d+)', urn)
            if mobj:
                return mobj.group(1)

    def _get_video_id(self, video_data, course_slug, video_slug):
        return self._get_urn_id(video_data) or '%s/%s' % (course_slug, video_slug)

    def _real_initialize(self):
        email, password = self._get_login_info()
        if email is None:
            return

        login_page = self._download_webpage(
            self._LOGIN_URL, None, 'Downloading login page')
        action_url = urljoin(self._LOGIN_URL, self._search_regex(
            r'<form[^>]+action=(["\'])(?P<url>.+?)\1', login_page, 'post url',
            default='https://www.linkedin.com/uas/login-submit', group='url'))
        data = self._hidden_inputs(login_page)
        data.update({
            'session_key': email,
            'session_password': password,
        })
        login_submit_page = self._download_webpage(
            action_url, None, 'Logging in',
            data=urlencode_postdata(data))
        error = self._search_regex(
            r'<span[^>]+class="error"[^>]*>\s*(.+?)\s*</span>',
            login_submit_page, 'error', default=None)
        if error:
            raise ExtractorError(error, expected=True)


class LinkedInLearningIE(LinkedInLearningBaseIE):
    IE_NAME = 'linkedin:learning'
    _VALID_URL = r'https?://(?:www\.)?linkedin\.com/learning/(?P<course_slug>[^/]+)/(?P<id>[^/?#]+)'
    _TEST = {
        'url': 'https://www.linkedin.com/learning/programming-foundations-fundamentals/welcome?autoplay=true',
        'md5': 'a1d74422ff0d5e66a792deb996693167',
        'info_dict': {
            'id': '90426',
            'ext': 'mp4',
            'title': 'Welcome',
            'timestamp': 1430396150.82,
            'upload_date': '20150430',
        },
    }

    def _real_extract(self, url):
        course_slug, video_slug = re.match(self._VALID_URL, url).groups()

        video_data = None
        formats = []
        for width, height in ((640, 360), (960, 540), (1280, 720)):
            video_data = self._call_api(
                course_slug, 'selectedVideo', video_slug, height)['selectedVideo']

            video_url_data = video_data.get('url') or {}
            progressive_url = video_url_data.get('progressiveUrl')
            if progressive_url:
                formats.append({
                    'format_id': 'progressive-%dp' % height,
                    'url': progressive_url,
                    'height': height,
                    'width': width,
                    'source_preference': 1,
                })

        title = video_data['title']

        audio_url = video_data.get('audio', {}).get('progressiveUrl')
        if audio_url:
            formats.append({
                'abr': 64,
                'ext': 'm4a',
                'format_id': 'audio',
                'url': audio_url,
                'vcodec': 'none',
            })

        streaming_url = video_url_data.get('streamingUrl')
        if streaming_url:
            formats.extend(self._extract_m3u8_formats(
                streaming_url, video_slug, 'mp4',
                'm3u8_native', m3u8_id='hls', fatal=False))

        # It seems like this would be correctly handled by default
        # However, unless someone can confirm this, the old
        # behaviour is being kept as-is
        self._sort_formats(formats, ('res', 'source_preference'))

        return {
            'id': self._get_video_id(video_data, course_slug, video_slug),
            'title': title,
            'formats': formats,
            'thumbnail': video_data.get('defaultThumbnail'),
            'timestamp': float_or_none(video_data.get('publishedOn'), 1000),
            'duration': int_or_none(video_data.get('durationInSeconds')),
        }


class LinkedInLearningCourseIE(LinkedInLearningBaseIE):
    IE_NAME = 'linkedin:learning:course'
    _VALID_URL = r'https?://(?:www\.)?linkedin\.com/learning/(?P<id>[^/?#]+)'
    _TEST = {
        'url': 'https://www.linkedin.com/learning/programming-foundations-fundamentals',
        'info_dict': {
            'id': 'programming-foundations-fundamentals',
            'title': 'Programming Foundations: Fundamentals',
            'description': 'md5:76e580b017694eb89dc8e8923fff5c86',
        },
        'playlist_mincount': 61,
    }

    @classmethod
    def suitable(cls, url):
        return False if LinkedInLearningIE.suitable(url) else super(LinkedInLearningCourseIE, cls).suitable(url)

    def _real_extract(self, url):
        course_slug = self._match_id(url)
        course_data = self._call_api(course_slug, 'chapters,description,title')

        entries = []
        for chapter_number, chapter in enumerate(course_data.get('chapters', []), 1):
            chapter_title = chapter.get('title')
            chapter_id = self._get_urn_id(chapter)
            for video in chapter.get('videos', []):
                video_slug = video.get('slug')
                if not video_slug:
                    continue
                entries.append({
                    '_type': 'url_transparent',
                    'id': self._get_video_id(video, course_slug, video_slug),
                    'title': video.get('title'),
                    'url': 'https://www.linkedin.com/learning/%s/%s' % (course_slug, video_slug),
                    'chapter': chapter_title,
                    'chapter_number': chapter_number,
                    'chapter_id': chapter_id,
                    'ie_key': LinkedInLearningIE.ie_key(),
                })

        return self.playlist_result(
            entries, course_slug,
            course_data.get('title'),
            course_data.get('description'))
