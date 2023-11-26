from .common import InfoExtractor
from ..utils import js_to_json
from urllib.parse import urlencode

class C13ClIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?13\.cl/en-vivo'

    def _real_extract(self, url):
        display_id = 'C13'
        webpage = self._download_webpage(url, display_id)

        stream_url = self._search_regex(r'<div\s+.*id=(?:"|\')player(?:"|\')[^>]+><iframe\s+.*src=(?:"|\')([^?]+)', webpage, 'stream_url')

        return self.url_result(stream_url,
            display_id=display_id, url_transparent=True)
