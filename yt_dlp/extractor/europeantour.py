# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor


class EuropeanTourIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?europeantour\.com/dpworld-tour/news/video/(?P<id>[^/&?#$]+)'

    _TESTS = [{
        'url': 'https://www.europeantour.com/dpworld-tour/news/video/the-best-shots-of-the-2021-seasons/',
        'info_dict': {
            'id': '6287788195001',
            'ext': 'mp4',
            'title': 'The best shots of the 2021 seasons',
            'duration': 2416.512,
            'timestamp': 1640010141,
            'uploader_id': '5136026580001',
            'tags': ['prod-imported'],
            'thumbnail': 'md5:fdac52bc826548860edf8145ee74e71a',
            'upload_date': '20211220'
        },
        'params': {'skip_download': True}
    }]

    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/default_default/index.html?videoId=%s'

    def _real_extract(self, url):
        id = self._match_id(url)
        webpage = self._download_webpage(url, id)
        vid, aid = re.search(r'(?s)brightcove-player\s?video-id="([^"]+)".*"ACCOUNT_ID":"([^"]+)"', webpage).groups()
        if not aid:
            aid = '5136026580001'
        return self.url_result(
            self.BRIGHTCOVE_URL_TEMPLATE % (aid, vid), 'BrightcoveNew')
