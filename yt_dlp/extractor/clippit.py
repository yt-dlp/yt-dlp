# coding: utf-8

from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    parse_iso8601,
    qualities,
)

import re


class ClippitIE(InfoExtractor):

    _VALID_URL = r'https?://(?:www\.)?clippituser\.tv/c/(?P<id>[a-z]+)'
    _TEST = {
        'url': 'https://www.clippituser.tv/c/evmgm',
        'md5': '963ae7a59a2ec4572ab8bf2f2d2c5f09',
        'info_dict': {
            'id': 'evmgm',
            'ext': 'mp4',
            'title': 'Bye bye Brutus. #BattleBots  - Clippit',
            'uploader': 'lizllove',
            'uploader_url': 'https://www.clippituser.tv/p/lizllove',
            'timestamp': 1472183818,
            'upload_date': '20160826',
            'description': 'BattleBots | ABC',
            'thumbnail': r're:^https?://.*\.jpg$',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._html_search_regex(r'<title.*>(.+?)</title>', webpage, 'title')

        FORMATS = ('sd', 'hd')
        quality = qualities(FORMATS)
        formats = []
        for format_id in FORMATS:
            url = self._html_search_regex(r'data-%s-file="(.+?)"' % format_id,
                                          webpage, 'url', fatal=False)
            if not url:
                continue
            match = re.search(r'/(?P<height>\d+)\.mp4', url)
            formats.append({
                'url': url,
                'format_id': format_id,
                'quality': quality(format_id),
                'height': int(match.group('height')) if match else None,
            })

        uploader = self._html_search_regex(r'class="username".*>\s+(.+?)\n',
                                           webpage, 'uploader', fatal=False)
        uploader_url = ('https://www.clippituser.tv/p/' + uploader
                        if uploader else None)

        timestamp = self._html_search_regex(r'datetime="(.+?)"',
                                            webpage, 'date', fatal=False)
        thumbnail = self._html_search_regex(r'data-image="(.+?)"',
                                            webpage, 'thumbnail', fatal=False)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'uploader': uploader,
            'uploader_url': uploader_url,
            'timestamp': parse_iso8601(timestamp),
            'description': self._og_search_description(webpage),
            'thumbnail': thumbnail,
        }
