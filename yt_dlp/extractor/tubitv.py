# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    sanitized_Request,
    urlencode_postdata,
)


class TubiTvIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tubitv\.com/(?:video|movies|tv-shows)/(?P<id>[0-9]+)'
    _LOGIN_URL = 'http://tubitv.com/login'
    _NETRC_MACHINE = 'tubitv'
    _GEO_COUNTRIES = ['US']
    _TESTS = [{
        'url': 'http://tubitv.com/video/283829/the_comedian_at_the_friday',
        'md5': '43ac06be9326f41912dc64ccf7a80320',
        'info_dict': {
            'id': '283829',
            'ext': 'mp4',
            'title': 'The Comedian at The Friday',
            'description': 'A stand up comedian is forced to look at the decisions in his life while on a one week trip to the west coast.',
            'uploader_id': 'bc168bee0d18dd1cb3b86c68706ab434',
        },
    }, {
        'url': 'http://tubitv.com/tv-shows/321886/s01_e01_on_nom_stories',
        'only_matching': True,
    }, {
        'url': 'http://tubitv.com/movies/383676/tracker',
        'only_matching': True,
    }, {
        'url': 'https://tubitv.com/movies/560057/penitentiary?start=true',
        'info_dict': {
            'id': '560057',
            'ext': 'mp4',
            'title': 'Penitentiary',
            'description': 'md5:8d2fc793a93cc1575ff426fdcb8dd3f9',
            'uploader_id': 'd8fed30d4f24fcb22ec294421b9defc2',
            'release_year': 1979,
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _login(self):
        username, password = self._get_login_info()
        if username is None:
            return
        self.report_login()
        form_data = {
            'username': username,
            'password': password,
        }
        payload = urlencode_postdata(form_data)
        request = sanitized_Request(self._LOGIN_URL, payload)
        request.add_header('Content-Type', 'application/x-www-form-urlencoded')
        login_page = self._download_webpage(
            request, None, False, 'Wrong login info')
        if not re.search(r'id="tubi-logout"', login_page):
            raise ExtractorError(
                'Login failed (invalid username/password)', expected=True)

    def _real_initialize(self):
        self._login()

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_data = self._download_json(
            'http://tubitv.com/oz/videos/%s/content' % video_id, video_id)
        title = video_data['title']

        formats = self._extract_m3u8_formats(
            self._proto_relative_url(video_data['url']),
            video_id, 'mp4', 'm3u8_native')
        self._sort_formats(formats)

        thumbnails = []
        for thumbnail_url in video_data.get('thumbnails', []):
            if not thumbnail_url:
                continue
            thumbnails.append({
                'url': self._proto_relative_url(thumbnail_url),
            })

        subtitles = {}
        for sub in video_data.get('subtitles', []):
            sub_url = sub.get('url')
            if not sub_url:
                continue
            subtitles.setdefault(sub.get('lang', 'English'), []).append({
                'url': self._proto_relative_url(sub_url),
            })

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': thumbnails,
            'description': video_data.get('description'),
            'duration': int_or_none(video_data.get('duration')),
            'uploader_id': video_data.get('publisher_id'),
            'release_year': int_or_none(video_data.get('year')),
        }
