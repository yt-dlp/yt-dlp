# coding: utf-8
from __future__ import unicode_literals

from yt_dlp.utils import (
    str_to_int,
    parse_duration
)

from .common import InfoExtractor

import re


class Rule34VideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rule34video\.com/videos/(?P<id>\d+)'
    _TESTS = [
        {
            'url': 'https://rule34video.com/videos/3065157/shot-it-mmd-hmv/',
            'info_dict': {
                'id': '3065157',
                'ext': 'mp4',
                'title': 'Shot It-(mmd hmv)',
                'thumbnail': 'https://rule34video.com/contents/videos_screenshots/3065000/3065157/preview.jpg',
                'duration': 347.0,
                'formats': [
                    {'url': r're:^https://rule34video\.com/get_file/.*360p?\.mp4/\?download=true',
                        'quality': '360'},
                    {'url': r're:^https://rule34video\.com/get_file/.*480p?\.mp4/\?download=true',
                        'quality': '480'},
                    {'url': r're:^https://rule34video\.com/get_file/.*720p?\.mp4/\?download=true',
                        'quality': '720'},
                    {'url': r're:^https://rule34video\.com/get_file/.*1080p?\.mp4/\?download=true',
                        'quality': '1080'},
                ]
            }
        },
        {
            'url': 'https://rule34video.com/videos/3065296/lara-in-trouble-ep-7-wildeerstudio/',
            'info_dict': {
                'id': '3065296',
                'ext': 'mp4',
                'title': 'Lara in Trouble Ep. 7 [WildeerStudio]',
                #'thumbnail': 'https://rule34video.com/contents/videos_screenshots/3065000/3065296/preview.jpg',
                'formats': [
                    {'url': r're:^https://rule34video\.com/get_file/.*360p?\.mp4/\?download=true',
                        'quality': '360'},
                    {'url': r're:^https://rule34video\.com/get_file/.*480p?\.mp4/\?download=true',
                        'quality': '480'},
                    {'url': r're:^https://rule34video\.com/get_file/.*720p?\.mp4/\?download=true',
                        'quality': '720'},
                    {'url': r're:^https://rule34video\.com/get_file/.*1080p?\.mp4/\?download=true',
                        'quality': '1080'},
                ]
            }
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        formats = []

        for mobj in re.finditer(r'<a[^>]+href="([^"]+download=true[^"]+)".*>([^\s]+) ([^<]+)p</a>', webpage):
            url, ext, quality = mobj.groups()
            formats.append({
                'url': url,
                'ext': ext.lower(),
                'quality': quality,
            })

        title = self._html_search_regex(r'<title>([^<]+)</title>', webpage, 'title')
        thumbnail = self._html_search_regex(r'preview_url:\s+\'([^\']+)\'', webpage, 'thumbnail', default=None)
        duration = self._html_search_regex(r'"icon-clock"></i>\s+<span>((?:\d+:?)+)', webpage, 'duration', default=None)

        self._sort_formats(formats)

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'thumbnail': thumbnail,
            'duration': parse_duration(duration),
            #'ext': 'mp4'
        }
