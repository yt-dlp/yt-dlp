import re
from itertools import groupby

from .common import InfoExtractor
from .archiveorg import ArchiveOrgIE
from ..utils import (
    InAdvancePagedList,
)


class AltCensoredIE(InfoExtractor):
    IE_NAME = 'altcensored'
    _VALID_URL = r'https?://(?:www\.)altcensored\.com/(?:watch\?v=|embed/)(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.altcensored.com/watch?v=k0srjLSkga8',
        'info_dict': {
            "id": "youtube-k0srjLSkga8",
            "ext": "webm",
            "title": "QUELLES SONT LES CONSÉQUENCES DE L'HYPERSEXUALISATION DE LA SOCIÉTÉ ?",
            'display_id': 'k0srjLSkga8.webm',
            'release_date': '20180403',
            'creator': 'Virginie Vota',
            'release_year': 2018,
            'upload_date': '20230318',
            'uploader': 'admin@altcensored.com',
            'description': 'md5:0b38a8fc04103579d5c1db10a247dc30',
            'timestamp': 1679161343,
            'track': 'k0srjLSkga8',
            'duration': 926.09,
            'thumbnail': 'https://archive.org/download/youtube-k0srjLSkga8/youtube-k0srjLSkga8.thumbs/k0srjLSkga8_000925.jpg',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        res = self.url_result(f'https://archive.org/details/youtube-{video_id}', ArchiveOrgIE)
        # Extractor indirection doesn't allow merging info from the original extractor.
        # Youtube view count or thumbnail extracted from altcensored can't be merge back
        # into underlying archive.org info json
        return res


class AltCensoredChannelIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)altcensored\.com/channel/(?P<id>[^/?#]+)'
    _PAGE_SIZE = 24
    _TESTS = [{
        'url': 'https://www.altcensored.com/channel/UCFPTO55xxHqFqkzRZHu4kcw',
        'info_dict': {
            'title': 'Virginie Vota Channel (91 Censored Videos)',
            'id': 'UCFPTO55xxHqFqkzRZHu4kcw',
        },
        'playlist_count': 91
    }]

    def _real_extract(self, url):
        channel_id = self._match_id(url)

        webpage = self._download_webpage(url, channel_id, note='Download channel info',
                                         errnote='Unable to get channel info')
        title = self._html_search_meta('og:title', webpage)
        page_count = int_or_none(self._html_search_regex(
            r'<a[^>]+href="/channel/\w+/page/(\d+)">(?:\1)</a>', webpage, 'page count', default='1'))

        def page_func(page_num):
            page_num += 1
            webpage = self._download_webpage(
                f'https://altcensored.com/channel/{channel_id}/page/{page_num}',
                channel_id, note=f'Downloading page {page_num}')

            items = re.findall(r'<a[^>]+href="(/watch\?v=[^"]+)', webpage)
            # deduplicate consecutive items (multiple <a> per video)
            items = [self.url_result('https://www.altcensored.com' + key, AltCensoredIE) for key, _group in groupby(items)]
            return items

        entries = InAdvancePagedList(page_func, page_count, self._PAGE_SIZE)
        return self.playlist_result(entries, playlist_id=channel_id, playlist_title=title)
