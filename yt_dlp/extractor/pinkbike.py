# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    remove_end,
    remove_start,
    str_to_int,
    unified_strdate,
)


class PinkbikeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:www\.)?pinkbike\.com/video/|es\.pinkbike\.org/i/kvid/kvid-y5\.swf\?id=)(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'http://www.pinkbike.com/video/402811/',
        'md5': '4814b8ca7651034cd87e3361d5c2155a',
        'info_dict': {
            'id': '402811',
            'ext': 'mp4',
            'title': 'Brandon Semenuk - RAW 100',
            'description': 'Official release: www.redbull.ca/rupertwalker',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 100,
            'upload_date': '20150406',
            'uploader': 'revelco',
            'location': 'Victoria, British Columbia, Canada',
            'view_count': int,
            'comment_count': int,
        }
    }, {
        'url': 'http://es.pinkbike.org/i/kvid/kvid-y5.swf?id=406629',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(
            'http://www.pinkbike.com/video/%s' % video_id, video_id)

        formats = []
        for _, format_id, src in re.findall(
                r'data-quality=((?:\\)?["\'])(.+?)\1[^>]+src=\1(.+?)\1', webpage):
            height = int_or_none(self._search_regex(
                r'^(\d+)[pP]$', format_id, 'height', default=None))
            formats.append({
                'url': src,
                'format_id': format_id,
                'height': height,
            })
        self._sort_formats(formats)

        title = remove_end(self._og_search_title(webpage), ' Video - Pinkbike')
        description = self._html_search_regex(
            r'(?s)id="media-description"[^>]*>(.+?)<',
            webpage, 'description', default=None) or remove_start(
            self._og_search_description(webpage), title + '. ')
        thumbnail = self._og_search_thumbnail(webpage)
        duration = int_or_none(self._html_search_meta(
            'video:duration', webpage, 'duration'))

        uploader = self._search_regex(
            r'<a[^>]+\brel=["\']author[^>]+>([^<]+)', webpage,
            'uploader', fatal=False)
        upload_date = unified_strdate(self._search_regex(
            r'class="fullTime"[^>]+title="([^"]+)"',
            webpage, 'upload date', fatal=False))

        location = self._html_search_regex(
            r'(?s)<dt>Location</dt>\s*<dd>(.+?)<',
            webpage, 'location', fatal=False)

        def extract_count(webpage, label):
            return str_to_int(self._search_regex(
                r'<span[^>]+class="stat-num"[^>]*>([\d,.]+)</span>\s*<span[^>]+class="stat-label"[^>]*>%s' % label,
                webpage, label, fatal=False))

        view_count = extract_count(webpage, 'Views')
        comment_count = extract_count(webpage, 'Comments')

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'upload_date': upload_date,
            'uploader': uploader,
            'location': location,
            'view_count': view_count,
            'comment_count': comment_count,
            'formats': formats
        }
