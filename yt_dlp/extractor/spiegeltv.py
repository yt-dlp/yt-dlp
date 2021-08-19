from __future__ import unicode_literals

from .common import InfoExtractor
from .nexx import NexxIE


class SpiegeltvIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?spiegel\.tv/videos/(?P<id>\d+)'
    _TEST = {
        'url': 'http://www.spiegel.tv/videos/161681-flug-mh370/',
        'only_matching': True,
    }

    def _real_extract(self, url):
        return self.url_result(
            'https://api.nexx.cloud/v3/748/videos/byid/%s'
            % self._match_id(url), ie=NexxIE.ie_key())
