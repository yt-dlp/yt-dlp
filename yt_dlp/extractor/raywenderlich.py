from __future__ import unicode_literals

import re

from .common import InfoExtractor
from .vimeo import VimeoIE
from ..compat import compat_str
from ..utils import (
    ExtractorError,
    int_or_none,
    merge_dicts,
    try_get,
    unescapeHTML,
    unified_timestamp,
    urljoin,
)


class RayWenderlichIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            videos\.raywenderlich\.com/courses|
                            (?:www\.)?raywenderlich\.com
                        )/
                        (?P<course_id>[^/]+)/lessons/(?P<id>\d+)
                    '''

    _TESTS = [{
        'url': 'https://www.raywenderlich.com/3530-testing-in-ios/lessons/1',
        'info_dict': {
            'id': '248377018',
            'ext': 'mp4',
            'title': 'Introduction',
            'description': 'md5:804d031b3efa9fcb49777d512d74f722',
            'timestamp': 1513906277,
            'upload_date': '20171222',
            'duration': 133,
            'uploader': 'Ray Wenderlich',
            'uploader_id': 'user3304672',
        },
        'params': {
            'noplaylist': True,
            'skip_download': True,
        },
        'add_ie': [VimeoIE.ie_key()],
        'expected_warnings': ['HTTP Error 403: Forbidden'],
    }, {
        'url': 'https://videos.raywenderlich.com/courses/105-testing-in-ios/lessons/1',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_video_id(data, lesson_id):
        if not data:
            return
        groups = try_get(data, lambda x: x['groups'], list) or []
        if not groups:
            return
        for group in groups:
            if not isinstance(group, dict):
                continue
            contents = try_get(data, lambda x: x['contents'], list) or []
            for content in contents:
                if not isinstance(content, dict):
                    continue
                ordinal = int_or_none(content.get('ordinal'))
                if ordinal != lesson_id:
                    continue
                video_id = content.get('identifier')
                if video_id:
                    return compat_str(video_id)

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        course_id, lesson_id = mobj.group('course_id', 'id')
        display_id = '%s/%s' % (course_id, lesson_id)

        webpage = self._download_webpage(url, display_id)

        thumbnail = self._og_search_thumbnail(
            webpage, default=None) or self._html_search_meta(
            'twitter:image', webpage, 'thumbnail')

        if '>Subscribe to unlock' in webpage:
            raise ExtractorError(
                'This content is only available for subscribers',
                expected=True)

        info = {
            'thumbnail': thumbnail,
        }

        vimeo_id = self._search_regex(
            r'data-vimeo-id=["\'](\d+)', webpage, 'vimeo id', default=None)

        if not vimeo_id:
            data = self._parse_json(
                self._search_regex(
                    r'data-collection=(["\'])(?P<data>{.+?})\1', webpage,
                    'data collection', default='{}', group='data'),
                display_id, transform_source=unescapeHTML, fatal=False)
            video_id = self._extract_video_id(
                data, lesson_id) or self._search_regex(
                r'/videos/(\d+)/', thumbnail, 'video id')
            headers = {
                'Referer': url,
                'X-Requested-With': 'XMLHttpRequest',
            }
            csrf_token = self._html_search_meta(
                'csrf-token', webpage, 'csrf token', default=None)
            if csrf_token:
                headers['X-CSRF-Token'] = csrf_token
            video = self._download_json(
                'https://videos.raywenderlich.com/api/v1/videos/%s.json'
                % video_id, display_id, headers=headers)['video']
            vimeo_id = video['clips'][0]['provider_id']
            info.update({
                '_type': 'url_transparent',
                'title': video.get('name'),
                'description': video.get('description') or video.get(
                    'meta_description'),
                'duration': int_or_none(video.get('duration')),
                'timestamp': unified_timestamp(video.get('created_at')),
            })

        return merge_dicts(info, self.url_result(
            VimeoIE._smuggle_referrer(
                'https://player.vimeo.com/video/%s' % vimeo_id, url),
            ie=VimeoIE.ie_key(), video_id=vimeo_id))


class RayWenderlichCourseIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            videos\.raywenderlich\.com/courses|
                            (?:www\.)?raywenderlich\.com
                        )/
                        (?P<id>[^/]+)
                    '''

    _TEST = {
        'url': 'https://www.raywenderlich.com/3530-testing-in-ios',
        'info_dict': {
            'title': 'Testing in iOS',
            'id': '3530-testing-in-ios',
        },
        'params': {
            'noplaylist': False,
        },
        'playlist_count': 29,
    }

    @classmethod
    def suitable(cls, url):
        return False if RayWenderlichIE.suitable(url) else super(
            RayWenderlichCourseIE, cls).suitable(url)

    def _real_extract(self, url):
        course_id = self._match_id(url)

        webpage = self._download_webpage(url, course_id)

        entries = []
        lesson_urls = set()
        for lesson_url in re.findall(
                r'<a[^>]+\bhref=["\'](/%s/lessons/\d+)' % course_id, webpage):
            if lesson_url in lesson_urls:
                continue
            lesson_urls.add(lesson_url)
            entries.append(self.url_result(
                urljoin(url, lesson_url), ie=RayWenderlichIE.ie_key()))

        title = self._og_search_title(
            webpage, default=None) or self._html_search_meta(
            'twitter:title', webpage, 'title', default=None)

        return self.playlist_result(entries, course_id, title)
