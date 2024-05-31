from .common import InfoExtractor
from ..compat import (
    compat_urlparse,
)


class MotorsportIE(InfoExtractor):
    _WORKING = False
    IE_DESC = 'motorsport.com'
    _VALID_URL = r'https?://(?:www\.)?motorsport\.com/[^/?#]+/video/(?:[^/?#]+/)(?P<id>[^/]+)/?(?:$|[?#])'
    _TEST = {
        'url': 'http://www.motorsport.com/f1/video/main-gallery/red-bull-racing-2014-rules-explained/',
        'info_dict': {
            'id': '2-T3WuR-KMM',
            'ext': 'mp4',
            'title': 'Red Bull Racing: 2014 Rules Explained',
            'duration': 208,
            'description': 'A new clip from Red Bull sees Daniel Ricciardo and Sebastian Vettel explain the 2014 Formula One regulations – which are arguably the most complex the sport has ever seen.',
            'uploader': 'mcomstaff',
            'uploader_id': 'UC334JIYKkVnyFoNCclfZtHQ',
            'upload_date': '20140903',
            'thumbnail': r're:^https?://.+\.jpg$'
        },
        'add_ie': ['Youtube'],
        'params': {
            'skip_download': True,
        },
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        iframe_path = self._html_search_regex(
            r'<iframe id="player_iframe"[^>]+src="([^"]+)"', webpage, 'iframe path', default=None)

        if iframe_path is None:
            iframe_path = self._html_search_regex(
                r'<iframe [^>]*\bsrc="(https://motorsport\.tv/embed/[^"]+)', webpage, 'embed iframe path')
            return self.url_result(iframe_path)

        iframe = self._download_webpage(
            compat_urlparse.urljoin(url, iframe_path), display_id,
            'Downloading iframe')
        youtube_id = self._search_regex(
            r'www.youtube.com/embed/(.{11})', iframe, 'youtube id')

        return {
            '_type': 'url_transparent',
            'display_id': display_id,
            'url': 'https://youtube.com/watch?v=%s' % youtube_id,
        }
