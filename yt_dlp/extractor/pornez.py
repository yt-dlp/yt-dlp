# coding: utf-8
from __future__ import unicode_literals
import re
from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    int_or_none,
    mimetype2ext
)


class PornezIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?pornez\.net/video(?P<id>[0-9]+)/'
    _TEST = {
        'url': 'https://pornez.net/video344819/mistresst-funny_penis_names-wmv/',
        'md5': '2e19a0a1cff3a5dbea0ef1b9e80bcbbc',
        'info_dict': {
            'id': '344819',
            'ext': 'mp4',
            'title': r'mistresst funny_penis_names wmv',
            'thumbnail': r're:^https?://.*\.jpg$',
            'age_limit': 18,
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        iframe_src = self._html_search_regex(r'<iframe src="([^"]+)"', webpage, 'iframe', fatal=True)
        title = self._html_search_meta(['name', 'twitter:title', 'og:title'], webpage, 'title', default=None) or self._search_regex(r'<h1>(.*?)</h1>', webpage, 'title')
        thumbnail = self._html_search_meta(['thumbnailUrl'], webpage, 'title', default=None)
        webpage = self._download_webpage(iframe_src, video_id)
        formats = []
        video_elements = self._search_regex(r'(?s)<video id="hls-video"[^>]*>(.*?)</video>', webpage, 'video elements', fatal=True)

        for source in re.findall(r'<source[^>]+>', video_elements):
            attributes = extract_attributes(source)
            format_url = attributes.get('src', None)
            format_type = attributes.get('type', None)
            format_title = attributes.get('title', None)
            height = int_or_none(self._search_regex(r'(\d+)', format_title, 'height', default=None))
            if format_url is None or format_type is None or format_title is None or height is None:
                continue
            format_ext = mimetype2ext(format_type)
            if format_ext == 'm3u8':
                format_ext = 'mp4'
            formats.append({
                'format_id': format_title,
                'url': format_url,
                'ext': format_ext,
                'height': int_or_none(height)
            })
        self._sort_formats(formats)
        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'formats': formats,
            'age_limit': 18
        }
