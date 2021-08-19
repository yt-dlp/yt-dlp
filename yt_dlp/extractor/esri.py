# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_urlparse
from ..utils import (
    int_or_none,
    parse_filesize,
    unified_strdate,
)


class EsriVideoIE(InfoExtractor):
    _VALID_URL = r'https?://video\.esri\.com/watch/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'https://video.esri.com/watch/1124/arcgis-online-_dash_-developing-applications',
        'md5': 'd4aaf1408b221f1b38227a9bbaeb95bc',
        'info_dict': {
            'id': '1124',
            'ext': 'mp4',
            'title': 'ArcGIS Online - Developing Applications',
            'description': 'Jeremy Bartley demonstrates how to develop applications with ArcGIS Online.',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 185,
            'upload_date': '20120419',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        formats = []
        for width, height, content in re.findall(
                r'(?s)<li><strong>(\d+)x(\d+):</strong>(.+?)</li>', webpage):
            for video_url, ext, filesize in re.findall(
                    r'<a[^>]+href="([^"]+)">([^<]+)&nbsp;\(([^<]+)\)</a>', content):
                formats.append({
                    'url': compat_urlparse.urljoin(url, video_url),
                    'ext': ext.lower(),
                    'format_id': '%s-%s' % (ext.lower(), height),
                    'width': int(width),
                    'height': int(height),
                    'filesize_approx': parse_filesize(filesize),
                })
        self._sort_formats(formats)

        title = self._html_search_meta('title', webpage, 'title')
        description = self._html_search_meta(
            'description', webpage, 'description', fatal=False)

        thumbnail = self._html_search_meta('thumbnail', webpage, 'thumbnail', fatal=False)
        if thumbnail:
            thumbnail = re.sub(r'_[st]\.jpg$', '_x.jpg', thumbnail)

        duration = int_or_none(self._search_regex(
            [r'var\s+videoSeconds\s*=\s*(\d+)', r"'duration'\s*:\s*(\d+)"],
            webpage, 'duration', fatal=False))

        upload_date = unified_strdate(self._html_search_meta(
            'last-modified', webpage, 'upload date', fatal=False))

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'upload_date': upload_date,
            'formats': formats
        }
