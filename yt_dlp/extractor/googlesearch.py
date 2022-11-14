import itertools
import re

from .common import SearchInfoExtractor


class GoogleSearchIE(SearchInfoExtractor):
    IE_DESC = 'Google Video search'
    IE_NAME = 'video.google:search'
    _SEARCH_KEY = 'gvsearch'
    _TESTS = [{
        'url': 'gvsearch15:python language',
        'info_dict': {
            'id': 'python language',
            'title': 'python language',
        },
        'playlist_count': 15,
    }]
    _PAGE_SIZE = 100

    def _search_results(self, query):
        for pagenum in itertools.count():
            webpage = self._download_webpage(
                'http://www.google.com/search', f'gvsearch:{query}',
                note=f'Downloading result page {pagenum + 1}',
                query={
                    'tbm': 'vid',
                    'q': query,
                    'start': pagenum * self._PAGE_SIZE,
                    'num': self._PAGE_SIZE,
                    'hl': 'en',
                })

            for url in re.findall(r'<div[^>]* class="dXiKIc"[^>]*><a href="([^"]+)"', webpage):
                yield self.url_result(url)

            if not re.search(r'id="pnnext"', webpage):
                return
