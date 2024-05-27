# filemoon.py
# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    decode_packed_codes,
    js_to_json,
)

class FileMoonIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?filemoon\.sx/./(?P<id>\w+)'
    _TEST = {
        'url': 'https://filemoon.sx/e/dw40rxrzruqz',
        'md5': '5a713742f57ac4aef29b74733e8dda01',
        'info_dict': {
            'id': 'dw40rxrzruqz',
            'title': 'dw40rxrzruqz',
            'ext': 'mp4'
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)
        matches = re.findall(r'(?s)(eval.*?)</script>', webpage)
        packed = matches[-1]
        unpacked = decode_packed_codes(packed)
        jwplayer_sources = self._parse_json(
            self._search_regex(
                r'(?s)player\s*\.\s*setup\s*\(\s*\{\s*sources\s*:\s*(.*?])', unpacked, 'jwplayer sources'),
            video_id, transform_source=js_to_json)

        formats = self._parse_jwplayer_formats(jwplayer_sources, video_id)

        return {
            'id': video_id,
            'title': self._generic_title(url) or video_id,
            'formats': formats
    }
