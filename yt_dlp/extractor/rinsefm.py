from .common import InfoExtractor
from ..utils import format_field, parse_iso8601


class RinseFMIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rinse\.fm/episodes/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://rinse.fm/episodes/club-glow-15-12-2023-2000/',
        'md5': '76ee0b719315617df42e15e710f46c7b',
        'info_dict': {
            'id': '1536535',
            'ext': 'mp3',
            'title': 'Club Glow - 15/12/2023 - 20:00',
            'thumbnail': r're:^https://.+\.(?:jpg|JPG)$',
            'release_timestamp': 1702598400,
            'release_date': '20231215'
        }
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        entry = self._search_nextjs_data(webpage, display_id)['props']['pageProps']['entry']

        return {
            'id': entry['id'],
            'title': entry.get('title'),
            'url': entry['fileUrl'],
            'vcodec': 'none',
            'release_timestamp': parse_iso8601(entry.get('episodeDate')),
            'thumbnail': format_field(
                entry, [('featuredImage', 0, 'filename')], 'https://rinse.imgix.net/media/%s', default=None),
        }
