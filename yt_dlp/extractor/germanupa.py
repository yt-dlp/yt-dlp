import urllib.parse

from .common import InfoExtractor
from .vimeo import VimeoIE
from ..utils import traverse_obj


class GermanupaIE(InfoExtractor):
    IE_DESC = 'germanupa.de'
    _VALID_URL = r'https?://germanupa\.de/mediathek/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://germanupa.de/mediathek/4-figma-beratung-deine-sprechstunde-fuer-figma-fragen',
        'info_dict': {
            'id': '909179246',
            'title': 'Tutorial: #4 Figma Beratung - Deine Sprechstunde für Figma-Fragen',
            'ext': 'mp4',
            'uploader': 'German UPA',
            'uploader_id': 'germanupa',
            'thumbnail': 'https://i.vimeocdn.com/video/1792564420-7415283ccef8bf8702dab8c6b7515555ceeb7a1c11371ffcc133b8e887dbf70e-d_1280',
            'uploader_url': 'https://vimeo.com/germanupa',
            'duration': 3987,
        },
        'expected_warnings': ['Failed to parse XML'],
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        'url': 'https://germanupa.de/mediathek/live-vom-ux-festival-neuigkeiten-von-figma-jobmarkt-agenturszene-interview-zu-sustainable',
        'info_dict': {
            'id': '1867346676',
            'title': 'Live vom UX Festival: Neuigkeiten von Figma, Jobmarkt, Agenturszene & Interview zu Sustainable UX',
            'ext': 'opus',
            'timestamp': 1720545088,
            'upload_date': '20240709',
            'duration': 3910.557,
            'like_count': int,
            'description': 'md5:db2aed5ff131e177a7b33901e9a8db05',
            'uploader': 'German UPA',
            'repost_count': int,
            'genres': ['Science'],
            'license': 'all-rights-reserved',
            'uploader_url': 'https://soundcloud.com/user-80097677',
            'uploader_id': '471579486',
            'view_count': int,
            'comment_count': int,
            'thumbnail': 'https://i1.sndcdn.com/artworks-oCti2e9GhaZFWBqY-48ybGw-original.jpg',
        },
    }, {
        # Nur für Mitglieder, info_dict INCOMPLETE
        'url': 'https://germanupa.de/mediathek/ux-festival-2024-usability-tests-und-ai',
        'info_dict': {
            'id': '0',
            'title': 'UX Festival 2024 "Usability Tests und AI"',
            'ext': 'mp4',
        },
        'skip': 'login required',
    }]
    _IFRAME_RE = r'<iframe[^>]+data-src\s*?=\s*?([\'"])(?P<url>https://germanupa\.de/media/oembed\?url=(?:(?!\1).)+)\1'
    _LOGIN_REQUIRED_RE = r'<div[^>]+class\s*?=\s*?([\'"])(?:(?!\1).)*login-wrapper(?:(?!\1).)*\1'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        embed_url = self._search_regex(self._IFRAME_RE, webpage, 'iframe embed', None, group='url')
        if not embed_url:
            return self.url_result(url, 'Generic')  # Fall back to generic to extract audio

        param_url = traverse_obj(urllib.parse.parse_qs(urllib.parse.urlparse(embed_url).query),
                                 ('url', 0), None)
        if not param_url:
            if self._search_regex(self._LOGIN_REQUIRED_RE, webpage, 'login wrapper', default=None):
                self.raise_login_required('This video is only available for members')
            return self.url_result(url)  # Fall back

        real_url = param_url.replace('https://vimeo.com/', 'https://player.vimeo.com/video/')
        return self.url_result(VimeoIE._smuggle_referrer(real_url, url), VimeoIE)
