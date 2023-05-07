from .common import InfoExtractor
from .rtvcplay import RTVCKalturaIE


class SenalColombiaLiveIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?senalcolombia\.tv/(?P<id>senal-en-vivo)'

    _TESTS = [{
        'url': 'https://www.senalcolombia.tv/senal-en-vivo',
        'info_dict': {
            'id': 'indexSC',
            'title': 're:^Señal Colombia',
            'description': 'md5:799f16a401d97f40c33a2c6a3e2a507b',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'live_status': 'is_live',
            'ext': 'mp4',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        hydration = self._search_json(
            r'<script\b[^>]*data-drupal-selector\s*=\s*"[^"]*drupal-settings-json[^"]*"[^>]*>',
            webpage, 'hydration', display_id)

        return self.url_result(hydration['envivosrc'], RTVCKalturaIE, display_id)
