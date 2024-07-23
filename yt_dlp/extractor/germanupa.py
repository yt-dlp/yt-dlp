import urllib.parse

from .common import InfoExtractor
from .vimeo import VimeoIE
from ..utils import traverse_obj


class GermanupaIE(InfoExtractor):
    _VALID_URL = r'https?://germanupa\.de/(?!media\b)[\w-]+/(?P<id>[\w-]+)'
    _IFRAME_RE = r'<iframe[^>]+data-src\s*?=\s*?([\'"])(?P<url>https://germanupa\.de/media/oembed\?url=(?:(?!\1).)+)\1'
    _LOGIN_REQUIRED_RE = r'<div[^>]+class\s*?=\s*?([\'"])(?:(?!\1).)*login-wrapper(?:(?!\1).)*\1'
    _TESTS = [{
        'url': 'https://germanupa.de/mediathek/4-figma-beratung-deine-sprechstunde-fuer-figma-fragen',
        'info_dict': {
            'id': '909179246',
            'title': 'Tutorial: #4 Figma Beratung - Deine Sprechstunde für Figma-Fragen',
            'ext': 'mp4',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        embed_url = self._search_regex(self._IFRAME_RE, webpage, 'iframe embed', default=None,
                                       group='url')
        real_url = traverse_obj(urllib.parse.parse_qs(urllib.parse.urlparse(embed_url).query),
                                ('url', 0), None)
        if not real_url:
            if not self._search_regex(self._LOGIN_REQUIRED_RE, webpage, 'login required div',
                                      default=None):
                return self.url_result(url, 'Generic')  # Fall back to generic to extract audio
            self.raise_login_required('This video is only available for members')
        self.to_screen(embed_url)
        return self.url_result(
            VimeoIE._smuggle_referrer(
                real_url.replace('https://vimeo.com/', 'https://player.vimeo.com/video/'), url),
            VimeoIE)
