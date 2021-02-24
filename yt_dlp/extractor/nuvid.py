from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    parse_duration,
)


class NuvidIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www|m)\.nuvid\.com/video/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'http://m.nuvid.com/video/1310741/',
        'md5': 'eab207b7ac4fccfb4e23c86201f11277',
        'info_dict': {
            'id': '1310741',
            'ext': 'mp4',
            'title': 'Horny babes show their awesome bodeis and',
            'duration': 129,
            'age_limit': 18,
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        page_url = 'http://m.nuvid.com/video/%s' % video_id
        webpage = self._download_webpage(
            page_url, video_id, 'Downloading video page')
        # When dwnld_speed exists and has a value larger than the MP4 file's
        # bitrate, Nuvid returns the MP4 URL
        # It's unit is 100bytes/millisecond, see mobile-nuvid-min.js for the algorithm
        self._set_cookie('nuvid.com', 'dwnld_speed', '10.0')
        mp4_webpage = self._download_webpage(
            page_url, video_id, 'Downloading video page for MP4 format')

        html5_video_re = r'(?s)<(?:video|audio)[^<]*(?:>.*?<source[^>]*)?\s+src=["\'](.*?)["\']',
        video_url = self._html_search_regex(html5_video_re, webpage, video_id)
        mp4_video_url = self._html_search_regex(html5_video_re, mp4_webpage, video_id)
        formats = [{
            'url': video_url,
        }]
        if mp4_video_url != video_url:
            formats.append({
                'url': mp4_video_url,
            })

        title = self._html_search_regex(
            [r'<span title="([^"]+)">',
             r'<div class="thumb-holder video">\s*<h5[^>]*>([^<]+)</h5>',
             r'<span[^>]+class="title_thumb">([^<]+)</span>'], webpage, 'title').strip()
        thumbnails = [
            {
                'url': thumb_url,
            } for thumb_url in re.findall(r'<img src="([^"]+)" alt="" />', webpage)
        ]
        thumbnail = thumbnails[0]['url'] if thumbnails else None
        duration = parse_duration(self._html_search_regex(
            [r'<i class="fa fa-clock-o"></i>\s*(\d{2}:\d{2})',
             r'<span[^>]+class="view_time">([^<]+)</span>'], webpage, 'duration', fatal=False))

        return {
            'id': video_id,
            'title': title,
            'thumbnails': thumbnails,
            'thumbnail': thumbnail,
            'duration': duration,
            'age_limit': 18,
            'formats': formats,
        }
