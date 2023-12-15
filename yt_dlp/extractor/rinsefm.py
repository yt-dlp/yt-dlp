from .common import InfoExtractor
from ..utils import (
    parse_iso8601,
    format_field,
)


class RinseFMIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rinse\.fm/episodes/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://rinse.fm/episodes/cameo-blush-01-09-2023-2300/',
        'md5': '9284abbd785e6b86e67d1cdca6224feb',
        'info_dict': {
            'id': '1351562',
            'ext': 'mp3',
            'title': 'Cameo Blush - 01/09/2023 - 23:00',
            'thumbnail': r're:^https?://.*\.JPG$',
            'release_timestamp': 1693522800,
            'release_date': '20230831'
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        entry = self._search_nextjs_data(webpage, video_id)['props']['pageProps']['entry']
        return {
            'id': entry['id'],
            'title': entry.get('title'),
            'url': entry['fileUrl'],
            'vcodec': 'none',
            'release_timestamp': parse_iso8601(entry.get('episodeDate')),
            'thumbnail': format_field(
                entry, [('featuredImage', 0, 'filename')], 'https://rinse.imgix.net/media/%s', default=None),
        }
