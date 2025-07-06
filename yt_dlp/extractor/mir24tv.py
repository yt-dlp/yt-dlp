from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    filter_dict,
    unsmuggle_url,
)
import urllib

class Mir24tvIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?mir24\.tv/news/(?P<id>[0-9]+)/[^/?#]+'
    _BASE_URL = 'https://mir24.tv'
    _HEADERS = {
        'Origin': _BASE_URL,
        'Referer': f'{_BASE_URL}/',
    }
    _TESTS = [{
        'url': 'https://mir24.tv/news/16635210/dni-kultury-rossii-otkrylis-v-uzbekistane.-na-prazdnichnom-koncerte-vystupili-zvezdy-rossijskoj-estrada',
        'info_dict': {
            'id': '16635210',
            'title': 'Дни культуры России открылись в Узбекистане. На праздничном концерте выступили звезды российской эстрады',
            'ext': 'mp4',
        },
        'params': {'skip_download': True},
    }]
    _IMPERSONATE_TARGET = True

    def _real_extract(self, url):
        video_id = self._match_id(url)
        url, smuggled_data = unsmuggle_url(url, {})
        impersonate = self._configuration_arg('impersonate', [''])
        try:
            webpage = self._request_webpage(url, video_id, headers=filter_dict({
                'Accept-Encoding': 'identity',
                'Referer': smuggled_data.get('referer'),
            }), impersonate=impersonate)
        except ExtractorError:
            raise ExtractorError('try again with  --extractor-args "generic:impersonate"', expected=True)
        webpage = webpage.read().decode()

        iframe_url = self._search_regex(
            r'<iframe[^>]+src=["\'](https?://mir24\.tv/players/[^"\']+)',
            webpage, 'iframe URL')

        parsed_url = urllib.parse.urlparse(iframe_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        m3u8_url_encoded = query_params.get('source', [''])[0]
        if not m3u8_url_encoded:
            raise self.raise_no_formats('Не удалось найти параметр source в iframe')

        m3u8_url = urllib.parse.unquote(m3u8_url_encoded).replace('///', '//')

        title = self._og_search_title(webpage, default=None) or self._html_search_meta(
            'og:title', webpage, 'title', default=video_id)

        return {
            'id': video_id,
            'title': title,
            'formats': self._extract_m3u8_formats(m3u8_url, video_id, 'mp4'),
        }
