from __future__ import unicode_literals

import itertools

from .common import InfoExtractor
from ..utils import (
    get_element_by_id,
    int_or_none,
    remove_end,
)


class FoxgayIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?foxgay\.com/videos/(?:\S+-)?(?P<id>\d+)\.shtml'
    _TEST = {
        'url': 'http://foxgay.com/videos/fuck-turkish-style-2582.shtml',
        'md5': '344558ccfea74d33b7adbce22e577f54',
        'info_dict': {
            'id': '2582',
            'ext': 'mp4',
            'title': 'Fuck Turkish-style',
            'description': 'md5:6ae2d9486921891efe89231ace13ffdf',
            'age_limit': 18,
            'thumbnail': r're:https?://.*\.jpg$',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = remove_end(self._html_search_regex(
            r'<title>([^<]+)</title>', webpage, 'title'), ' - Foxgay.com')
        description = get_element_by_id('inf_tit', webpage)

        # The default user-agent with foxgay cookies leads to pages without videos
        self._downloader.cookiejar.clear('.foxgay.com')
        # Find the URL for the iFrame which contains the actual video.
        iframe_url = self._html_search_regex(
            r'<iframe[^>]+src=([\'"])(?P<url>[^\'"]+)\1', webpage,
            'video frame', group='url')
        iframe = self._download_webpage(
            iframe_url, video_id, headers={'User-Agent': 'curl/7.50.1'},
            note='Downloading video frame')
        video_data = self._parse_json(self._search_regex(
            r'video_data\s*=\s*([^;]+);', iframe, 'video data'), video_id)

        formats = [{
            'url': source,
            'height': int_or_none(resolution),
        } for source, resolution in zip(
            video_data['sources'], video_data.get('resolutions', itertools.repeat(None)))]

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'description': description,
            'thumbnail': video_data.get('act_vid', {}).get('thumb'),
            'age_limit': 18,
        }
