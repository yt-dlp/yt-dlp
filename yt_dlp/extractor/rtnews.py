# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class RTNewsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rt\.com/[^/]+/(?:[^/]+/)?(?P<id>\d+-[a-zA-Z0-9\-]+)'

    _TESTS = [{
        'url': 'https://www.rt.com/sport/546301-djokovic-arrives-belgrade-crowds/',
        'info_dict': {
            'id': '546301-djokovic-arrives-belgrade-crowds',
            'ext': 'mp4',
            'title': 'Crowds gather to greet deported Djokovic as he returns to Serbia (VIDEO)',
            'description': 'md5:1d5bfe1a988d81fd74227cfdf93d314d',
            'display_id': '546301',
            'thumbnail': 'https://cdni.rt.com/files/2022.01/article/61e587a085f540102c3386c1.png'
        },
        'params': {'skip_download': True}
    },
        {
            'url': 'https://www.rt.com/shows/in-question/535980-plot-to-assassinate-julian-assange/',
            'info_dict': {
                'id': '535980-plot-to-assassinate-julian-assange',
                'ext': 'mp4',
                'title': 'The plot to assassinate Julian Assange',
                'description': 'md5:55279ce5e4441dc1d16e2e4a730152cd',
                'display_id': '535980',
                'thumbnail': 'https://cdni.rt.com/files/2021.09/article/615226f42030274e8879b53d.png'
            },
            'params': {'skip_download': True}
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        display_id = id.split('-', maxsplit=1)[0]
        webpage = self._download_webpage(url, display_id)
        if 'og:video' not in webpage:
            self.raise_no_formats('No video/audio found at the provided url.', expected=True)

        return {
            'id': id,
            'display_id': display_id,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
            'url': self._og_search_video_url(webpage)
        }
