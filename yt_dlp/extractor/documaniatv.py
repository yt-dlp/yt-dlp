# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    int_or_none,
)


class DocumaniaTVIE(InfoExtractor):
    _VALID_URL = r'(?:https?://)(?:www\.)?documaniatv\.com/[^/]+/.+_(?P<id>.+)\.html'

    _TESTS = [{
        'url': 'https://www.documaniatv.com/ciencia-y-tecnologia/the-pirate-bay-video_22c12b753.html',
        'info_dict': {
            'id': '22c12b753',
            'ext': 'mp4',
            'title': 'The pirate bay',
        },
        'skip': 'Provide cookies and user-agent',
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        webpage = self._download_webpage(url, id, errnote='Provide cookies and user-agent')
        playback_url = self._html_search_regex(r'file\s?:\s?\"(.+\.mp4)\"', webpage, 'playback_url')
        formats = [{
            'url': playback_url,
            'width': int_or_none(self._og_search_property('video:width', webpage, 'width')),
            'height': int_or_none(self._og_search_property('video:height', webpage, 'height')),
            'ext': 'mp4',
        }]
        self._sort_formats(formats)
        return {
            'id': id,
            'title': self._og_search_title(webpage),
            'formats': formats,
        }
