from .common import InfoExtractor
from ..utils import parse_iso8601


class HowcastIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?howcast\.com/videos/(?P<id>\d+)'
    _TEST = {
        'url': 'http://www.howcast.com/videos/390161-How-to-Tie-a-Square-Knot-Properly',
        'md5': '7d45932269a288149483144f01b99789',
        'info_dict': {
            'id': '390161',
            'ext': 'mp4',
            'title': 'How to Tie a Square Knot Properly',
            'description': 'md5:dbe792e5f6f1489027027bf2eba188a3',
            'timestamp': 1276081287,
            'upload_date': '20100609',
            'duration': 56.823,
        },
        'params': {
            'skip_download': True,
        },
        'add_ie': ['Ooyala'],
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        embed_code = self._search_regex(
            r'<iframe[^>]+src="[^"]+\bembed_code=([^\b]+)\b',
            webpage, 'ooyala embed code')

        return {
            '_type': 'url_transparent',
            'ie_key': 'Ooyala',
            'url': 'ooyala:%s' % embed_code,
            'id': video_id,
            'timestamp': parse_iso8601(self._html_search_meta(
                'article:published_time', webpage, 'timestamp')),
        }
