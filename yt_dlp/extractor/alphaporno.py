from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    parse_iso8601,
    parse_duration,
    parse_filesize,
    int_or_none,
)


class AlphaPornoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?alphaporno\.com/videos/(?P<id>[^/]+)'
    _TEST = {
        'url': 'http://www.alphaporno.com/videos/sensual-striptease-porn-with-samantha-alexandra/',
        'md5': 'feb6d3bba8848cd54467a87ad34bd38e',
        'info_dict': {
            'id': '258807',
            'display_id': 'sensual-striptease-porn-with-samantha-alexandra',
            'ext': 'mp4',
            'title': 'Sensual striptease porn with Samantha Alexandra',
            'thumbnail': r're:https?://.*\.jpg$',
            'timestamp': 1418694611,
            'upload_date': '20141216',
            'duration': 387,
            'filesize_approx': 54120000,
            'tbr': 1145,
            'categories': list,
            'age_limit': 18,
        }
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        video_id = self._search_regex(
            r"video_id\s*:\s*'([^']+)'", webpage, 'video id', default=None)

        video_url = self._search_regex(
            r"video_url\s*:\s*'([^']+)'", webpage, 'video url')
        ext = self._html_search_meta(
            'encodingFormat', webpage, 'ext', default='.mp4')[1:]

        title = self._search_regex(
            [r'<meta content="([^"]+)" itemprop="description">',
             r'class="title" itemprop="name">([^<]+)<'],
            webpage, 'title')
        thumbnail = self._html_search_meta('thumbnail', webpage, 'thumbnail')
        timestamp = parse_iso8601(self._html_search_meta(
            'uploadDate', webpage, 'upload date'))
        duration = parse_duration(self._html_search_meta(
            'duration', webpage, 'duration'))
        filesize_approx = parse_filesize(self._html_search_meta(
            'contentSize', webpage, 'file size'))
        bitrate = int_or_none(self._html_search_meta(
            'bitrate', webpage, 'bitrate'))
        categories = self._html_search_meta(
            'keywords', webpage, 'categories', default='').split(',')

        age_limit = self._rta_search(webpage)

        return {
            'id': video_id,
            'display_id': display_id,
            'url': video_url,
            'ext': ext,
            'title': title,
            'thumbnail': thumbnail,
            'timestamp': timestamp,
            'duration': duration,
            'filesize_approx': filesize_approx,
            'tbr': bitrate,
            'categories': categories,
            'age_limit': age_limit,
        }
