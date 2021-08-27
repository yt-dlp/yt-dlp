# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    get_element_by_class,
    int_or_none,
    remove_start,
    strip_or_none,
    unified_strdate,
)


class ScreencastOMaticIE(InfoExtractor):
    _VALID_URL = r'https?://screencast-o-matic\.com/(?:(?:watch|player)/|embed\?.*?\bsc=)(?P<id>[0-9a-zA-Z]+)'
    _TESTS = [{
        'url': 'http://screencast-o-matic.com/watch/c2lD3BeOPl',
        'md5': '483583cb80d92588f15ccbedd90f0c18',
        'info_dict': {
            'id': 'c2lD3BeOPl',
            'ext': 'mp4',
            'title': 'Welcome to 3-4 Philosophy @ DECV!',
            'thumbnail': r're:^https?://.*\.jpg$',
            'description': 'as the title says! also: some general info re 1) VCE philosophy and 2) distance learning.',
            'duration': 369,
            'upload_date': '20141216',
        }
    }, {
        'url': 'http://screencast-o-matic.com/player/c2lD3BeOPl',
        'only_matching': True,
    }, {
        'url': 'http://screencast-o-matic.com/embed?ff=true&sc=cbV2r4Q5TL&fromPH=true&a=1',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(
            'https://screencast-o-matic.com/player/' + video_id, video_id)
        info = self._parse_html5_media_entries(url, webpage, video_id)[0]
        info.update({
            'id': video_id,
            'title': get_element_by_class('overlayTitle', webpage),
            'description': strip_or_none(get_element_by_class('overlayDescription', webpage)) or None,
            'duration': int_or_none(self._search_regex(
                r'player\.duration\s*=\s*function\(\)\s*{\s*return\s+(\d+);\s*};',
                webpage, 'duration', default=None)),
            'upload_date': unified_strdate(remove_start(
                get_element_by_class('overlayPublished', webpage), 'Published: ')),
        })
        return info
