# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    int_or_none,
)


class ZoomUSIE(InfoExtractor):
    IE_NAME = 'zoom.us'
    _VALID_URL = r'https://(.*).?zoom.us/rec(ording)?/play/(?P<id>.*)'

    _TEST = {
        'url': 'https://zoom.us/recording/play/SILVuCL4bFtRwWTtOCFQQxAsBQsJljFtm9e4Z_bvo-A8B-nzUSYZRNuPl3qW5IGK',
        'info_dict': {
            'md5': '031a5b379f1547a8b29c5c4c837dccf2',
            'title': "GAZ Transformational Tuesdays W/ Landon & Stapes",
            'id': "SILVuCL4bFtRwWTtOCFQQxAsBQsJljFtm9e4Z_bvo-A8B-nzUSYZRNuPl3qW5IGK",
            'ext': "mp4",
        }
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        video_url = self._search_regex(r"viewMp4Url: \'(.*)\'", webpage, 'video url')
        topic = self._search_regex(r"topic: \"(.*)\",", webpage, 'video url')
        viewResolvtionsWidth = self._search_regex(r"viewResolvtionsWidth: (.*),", webpage, 'res width')
        viewResolvtionsHeight = self._search_regex(r"viewResolvtionsHeight: (.*),", webpage, 'res width')

        formats = []
        formats.append({
            'url': video_url,
            'width': int_or_none(viewResolvtionsWidth),
            'height': int_or_none(viewResolvtionsHeight),
            'http_headers': {'Accept': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5',
                             'Referer': 'https://zoom.us/'}
        })
        self._sort_formats(formats)

        return {
            'id': display_id,
            'title': topic,
            'formats': formats
        }
