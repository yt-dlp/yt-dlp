from .common import InfoExtractor
from .vimeo import VimeoIE


class ShieyIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?shiey\.com/videos/v/(?P<id>[^/]+)'

    _TESTS = [{
        'url': 'https://www.shiey.com/videos/v/train-journey-to-edge-of-serbia-ep-2',
        'info_dict': {
            'id': 'train-journey-to-edge-of-serbia-ep-2',
            'title': 'Train Journey to the Edge of Serbia - Ep. 2',
            'uploader': 'Shiey',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        vimeo_url = self._search_regex(r'iframe src=\\&quot;(https?://player\.vimeo\.com/video/[^\\&]+)', webpage, 'vimeo url')
        return self.url_result(VimeoIE._smuggle_referrer(vimeo_url, url), VimeoIE)
