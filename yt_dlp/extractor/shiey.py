import json

from .common import InfoExtractor
from .vimeo import VimeoIE
from ..utils import extract_attributes
from ..utils.traversal import find_element, traverse_obj


class ShieyIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?shiey\.com/videos/v/(?P<id>[^/?#]+)'

    _TESTS = [{
        'url': 'https://www.shiey.com/videos/v/train-journey-to-edge-of-serbia-ep-2',
        'info_dict': {
            'id': '1103409448',
            'ext': 'mp4',
            'title': 'Train Journey To Edge of Serbia (Ep. 2)',
            'uploader': 'shiey',
            'uploader_url': '',
            'duration': 1364,
            'thumbnail': r're:^https?://.+',
        },
        'params': {'skip_download': True},
        'expected_warnings': ['Failed to parse XML: not well-formed'],
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        oembed_html = traverse_obj(webpage, (
            {find_element(attr='data-controller', value='VideoEmbed', html=True)},
            {extract_attributes}, 'data-config-embed-video', {json.loads}, 'oembedHtml', {str}))

        return self.url_result(VimeoIE._extract_url(url, oembed_html), VimeoIE)
