# coding: utf-8

from .common import InfoExtractor

class LaCTVIE(InfoExtractor):

    _VALID_URL = r'https?://(www\.)?lactv\.it/(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<id>[^/?#]+)'

    _TESTS = [

    ]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        embed_url = self._search_regex(r'<iframe[^>]+src=\"(https?://[^/\"]+/embed/[^\"]+)"', webpage, 'embed URL')
        embed = self._download_webpage(embed_url, display_id, 'Downloading player embed')
        pass

