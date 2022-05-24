from .common import InfoExtractor
from ..utils import (
    try_get,
    unified_strdate,
)


class SkyNewsAUIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?skynews\.com\.au/[^/]+/[^/]+/[^/]+/video/(?P<id>[a-z0-9]+)'

    _TESTS = [{
        'url': 'https://www.skynews.com.au/world-news/united-states/incredible-vision-shows-lava-overflowing-from-spains-la-palma-volcano/video/0f4c6243d6903502c01251f228b91a71',
        'info_dict': {
            'id': '6277184925001',
            'ext': 'mp4',
            'title': 'md5:60594f1ea6d5ae93e292900f4d34e9ae',
            'description': 'md5:60594f1ea6d5ae93e292900f4d34e9ae',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 76.394,
            'timestamp': 1634271300,
            'uploader_id': '5348771529001',
            'tags': ['fblink', 'msn', 'usa', 'world', 'yt'],
            'upload_date': '20211015',
        },
        'params': {'skip_download': True, 'format': 'bv'}
    }]

    _API_KEY = '6krsj3w249nk779d8fukqx9f'

    def _real_extract(self, url):
        id = self._match_id(url)
        webpage = self._download_webpage(url, id)
        embedcode = self._search_regex(r'embedcode\s?=\s?\"([^\"]+)\"', webpage, 'embedcode')
        data_json = self._download_json(
            f'https://content.api.news/v3/videos/brightcove/{embedcode}?api_key={self._API_KEY}', id)['content']
        return {
            'id': id,
            '_type': 'url_transparent',
            'url': 'https://players.brightcove.net/%s/default_default/index.html?videoId=%s' % tuple(embedcode.split('-')),
            'ie_key': 'BrightcoveNew',
            'title': data_json.get('caption'),
            'upload_date': unified_strdate(try_get(data_json, lambda x: x['date']['created'])),
        }
