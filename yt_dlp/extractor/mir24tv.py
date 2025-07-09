from .common import InfoExtractor
from ..utils import parse_qs, url_or_none
from ..utils.traversal import require, traverse_obj


class Mir24tvIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?mir24\.tv/news/(?P<id>[0-9]+)/[^/?#]+'
    _TESTS = [{
        'url': 'https://mir24.tv/news/16635210/dni-kultury-rossii-otkrylis-v-uzbekistane.-na-prazdnichnom-koncerte-vystupili-zvezdy-rossijskoj-estrada',
        'info_dict': {
            'id': '16635210',
            'title': 'Дни культуры России открылись в Узбекистане. На праздничном концерте выступили звезды российской эстрады',
            'ext': 'mp4',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id, impersonate=True)

        iframe_url = self._search_regex(
            r'<iframe\b[^>]+\bsrc=["\'](https?://mir24\.tv/players/[^"\']+)',
            webpage, 'iframe URL')

        m3u8_url = traverse_obj(iframe_url, (
            {parse_qs}, 'source', -1, {self._proto_relative_url}, {url_or_none}, {require('m3u8 URL')}))

        return {
            'id': video_id,
            'title': self._og_search_title(webpage, default=None) or self._html_extract_title(webpage),
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'formats': self._extract_m3u8_formats(m3u8_url, video_id, 'mp4'),
        }
