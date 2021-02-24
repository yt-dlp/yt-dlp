# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class LCIIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?lci\.fr/[^/]+/[\w-]+-(?P<id>\d+)\.html'
    _TEST = {
        'url': 'http://www.lci.fr/international/etats-unis-a-j-62-hillary-clinton-reste-sans-voix-2001679.html',
        'md5': '2fdb2538b884d4d695f9bd2bde137e6c',
        'info_dict': {
            'id': '13244802',
            'ext': 'mp4',
            'title': 'Hillary Clinton et sa quinte de toux, en plein meeting',
            'description': 'md5:a4363e3a960860132f8124b62f4a01c9',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        wat_id = self._search_regex(
            (r'data-watid=[\'"](\d+)', r'idwat["\']?\s*:\s*["\']?(\d+)'),
            webpage, 'wat id')
        return self.url_result('wat:' + wat_id, 'Wat', wat_id)
