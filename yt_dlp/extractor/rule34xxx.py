# coding: utf-8
from __future__ import unicode_literals

from ..utils import str_to_int
from .common import InfoExtractor


class Rule34XXXIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rule34\.xxx/(?:index.php)?\?(?=.*page=post)(?=.*s=view)(?=.*id=(?P<id>\d+))'
    _TESTS = [
        {
            'url': 'https://rule34.xxx/index.php?page=post&s=view&id=4328926',
            'md5': '5b21e7ba114d023b6f455919ddeafbe9',
            'info_dict': {
                'id': '4328926',
                'ext': 'mp4',
                'title': 'rule34xxx',
                'url': r're:^https://.*\.rule34\.xxx/.*\.mp4',
                'width': 1920,
                'height': 1080,
                'thumbnail': r're:https://.*\.rule34\.xxx/thumbnails/.*\.jpg',
                'age_limit': 18
            },
        }
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        video_url = self._og_search_property('image', webpage)
        width = str_to_int(self._html_search_regex(r'\'width\':\s*(\d+)', webpage, 'width', default=None))
        height = str_to_int(self._html_search_regex(r'\'height\':\s*(\d+)', webpage, 'height', default=None))
        thumbnail = self._html_search_regex(r'(https://.*\.rule34\.xxx/thumbnails/[^\?"\']+)', webpage, 'thumbnail', default=None)

        return {
            'id': video_id,
            'url': video_url,
            # This site does not provide meaningful title
            'title': 'rule34xxx',
            'width': width,
            'height': height,
            'thumbnail': thumbnail,
            'age_limit': 18
        }
