import re

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
)


class NZZIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?nzz\.ch/(?:[^/]+/)*[^/?#]+-ld\.(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.nzz.ch/zuerich/gymizyte/gymizyte-schreiben-schueler-heute-noch-diktate-ld.9153',
        'info_dict': {
            'id': '9153',
        },
        'playlist_mincount': 6,
    }, {
        'url': 'https://www.nzz.ch/video/nzz-standpunkte/cvp-auf-der-suche-nach-dem-mass-der-mitte-ld.1368112',
        'info_dict': {
            'id': '1368112',
        },
        'playlist_count': 1,
    }]

    def _real_extract(self, url):
        page_id = self._match_id(url)
        webpage = self._download_webpage(url, page_id)

        entries = []
        for player_element in re.findall(
                r'(<[^>]+class="kalturaPlayer[^"]*"[^>]*>)', webpage):
            player_params = extract_attributes(player_element)
            if player_params.get('data-type') not in ('kaltura_singleArticle',):
                self.report_warning('Unsupported player type')
                continue
            entry_id = player_params['data-id']
            entries.append(self.url_result(
                'kaltura:1750922:' + entry_id, 'Kaltura', entry_id))

        return self.playlist_result(entries, page_id)
