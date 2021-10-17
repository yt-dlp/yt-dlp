from __future__ import unicode_literals

import itertools
import re

from .common import SearchInfoExtractor


class GoogleSearchIE(SearchInfoExtractor):
    IE_DESC = 'Google Video search'
    _MAX_RESULTS = 1000
    IE_NAME = 'video.google:search'
    _SEARCH_KEY = 'gvsearch'
    _WORKING = False
    _TEST = {
        'url': 'gvsearch15:python language',
        'info_dict': {
            'id': 'python language',
            'title': 'python language',
        },
        'playlist_count': 15,
    }

    def _search_results(self, query):
        for pagenum in itertools.count():
            webpage = self._download_webpage(
                'http://www.google.com/search',
                'gvsearch:' + query,
                note='Downloading result page %s' % (pagenum + 1),
                query={
                    'tbm': 'vid',
                    'q': query,
                    'start': pagenum * 10,
                    'hl': 'en',
                })

            for hit_idx, mobj in enumerate(re.finditer(
                    r'<h3 class="r"><a href="([^"]+)"', webpage)):
                if re.search(f'id="vidthumb{hit_idx + 1}"', webpage):
                    yield self.url_result(mobj.group(1))

            if not re.search(r'id="pnnext"', webpage):
                return
