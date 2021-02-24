# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class ThisOldHouseIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?thisoldhouse\.com/(?:watch|how-to|tv-episode|(?:[^/]+/)?\d+)/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.thisoldhouse.com/how-to/how-to-build-storage-bench',
        'info_dict': {
            'id': '5dcdddf673c3f956ef5db202',
            'ext': 'mp4',
            'title': 'How to Build a Storage Bench',
            'description': 'In the workshop, Tom Silva and Kevin O\'Connor build a storage bench for an entryway.',
            'timestamp': 1442548800,
            'upload_date': '20150918',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.thisoldhouse.com/watch/arlington-arts-crafts-arts-and-crafts-class-begins',
        'only_matching': True,
    }, {
        'url': 'https://www.thisoldhouse.com/tv-episode/ask-toh-shelf-rough-electric',
        'only_matching': True,
    }, {
        'url': 'https://www.thisoldhouse.com/furniture/21017078/how-to-build-a-storage-bench',
        'only_matching': True,
    }, {
        'url': 'https://www.thisoldhouse.com/21113884/s41-e13-paradise-lost',
        'only_matching': True,
    }, {
        # iframe www.thisoldhouse.com
        'url': 'https://www.thisoldhouse.com/21083431/seaside-transformation-the-westerly-project',
        'only_matching': True,
    }]
    _ZYPE_TMPL = 'https://player.zype.com/embed/%s.html?api_key=hsOk_yMSPYNrT22e9pu8hihLXjaZf0JW5jsOWv4ZqyHJFvkJn6rtToHl09tbbsbe'

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        video_id = self._search_regex(
            r'<iframe[^>]+src=[\'"](?:https?:)?//(?:www\.)?thisoldhouse\.(?:chorus\.build|com)/videos/zype/([0-9a-f]{24})',
            webpage, 'video id')
        return self.url_result(self._ZYPE_TMPL % video_id, 'Zype', video_id)
