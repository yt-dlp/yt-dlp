import re

from .archiveorg import ArchiveOrgIE
from .common import InfoExtractor
from ..utils import (
    InAdvancePagedList,
    int_or_none,
    orderedSet,
    str_to_int,
    urljoin,
)


class AltCensoredIE(InfoExtractor):
    IE_NAME = 'altcensored'
    _VALID_URL = r'https?://(?:www\.)?altcensored\.com/(?:watch\?v=|embed/)(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.altcensored.com/watch?v=k0srjLSkga8',
        'info_dict': {
            'id': 'youtube-k0srjLSkga8',
            'ext': 'webm',
            'title': "QUELLES SONT LES CONSÉQUENCES DE L'HYPERSEXUALISATION DE LA SOCIÉTÉ ?",
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
            'view_count': int,
            'categories': ['News & Politics'],
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        return {
            '_type': 'url_transparent',
            'url': f'https://archive.org/details/youtube-{video_id}',
            'ie_key': ArchiveOrgIE.ie_key(),
            'view_count': str_to_int(self._html_search_regex(
                r'YouTube Views:(?:\s|&nbsp;)*([\d,]+)', webpage, 'view count', default=None)),
            'categories': self._html_search_regex(
                r'<a href="/category/\d+">\s*\n?\s*([^<]+)</a>',
                webpage, 'category', default='').split() or None,
        }


class AltCensoredChannelIE(InfoExtractor):
    IE_NAME = 'altcensored:channel'
    _VALID_URL = r'https?://(?:www\.)?altcensored\.com/channel/(?!page|table)(?P<id>[^/?#]+)'
    _PAGE_SIZE = 24
    _TESTS = [{
        'url': 'https://www.altcensored.com/channel/UCFPTO55xxHqFqkzRZHu4kcw',
        'info_dict': {
            'title': 'Virginie Vota',
            'id': 'UCFPTO55xxHqFqkzRZHu4kcw',
        },
        'playlist_count': 91
    }, {
        'url': 'https://altcensored.com/channel/UC9CcJ96HKMWn0LZlcxlpFTw',
        'info_dict': {
            'title': 'yukikaze775',
            'id': 'UC9CcJ96HKMWn0LZlcxlpFTw',
        },
        'playlist_count': 4
    }]

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        webpage = self._download_webpage(
            url, channel_id, 'Download channel webpage', 'Unable to get channel webpage')
        title = self._html_search_meta('altcen_title', webpage, 'title', fatal=False)
        page_count = int_or_none(self._html_search_regex(
            r'<a[^>]+href="/channel/\w+/page/(\d+)">(?:\1)</a>',
            webpage, 'page count', default='1'))

        def page_func(page_num):
            page_num += 1
            webpage = self._download_webpage(
                f'https://altcensored.com/channel/{channel_id}/page/{page_num}',
                channel_id, note=f'Downloading page {page_num}')

            items = re.findall(r'<a[^>]+href="(/watch\?v=[^"]+)', webpage)
            return [self.url_result(urljoin('https://www.altcensored.com', path), AltCensoredIE)
                    for path in orderedSet(items)]

        return self.playlist_result(
            InAdvancePagedList(page_func, page_count, self._PAGE_SIZE),
            playlist_id=channel_id, playlist_title=title)
