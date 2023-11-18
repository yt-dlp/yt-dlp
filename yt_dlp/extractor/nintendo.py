import re

from .common import InfoExtractor
from .ooyala import OoyalaIE


class NintendoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?nintendo\.com/(?:games/detail|nintendo-direct)/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.nintendo.com/games/detail/duck-hunt-wii-u/',
        'info_dict': {
            'id': 'MzMmticjp0VPzO3CCj4rmFOuohEuEWoW',
            'ext': 'flv',
            'title': 'Duck Hunt Wii U VC NES - Trailer',
            'duration': 60.326,
        },
        'params': {
            'skip_download': True,
        },
        'add_ie': ['Ooyala'],
    }, {
        'url': 'http://www.nintendo.com/games/detail/tokyo-mirage-sessions-fe-wii-u',
        'info_dict': {
            'id': 'tokyo-mirage-sessions-fe-wii-u',
            'title': 'Tokyo Mirage Sessions ♯FE',
        },
        'playlist_count': 4,
    }, {
        'url': 'https://www.nintendo.com/nintendo-direct/09-04-2019/',
        'info_dict': {
            'id': 'J2bXdmaTE6fe3dWJTPcc7m23FNbc_A1V',
            'ext': 'mp4',
            'title': 'Switch_ROS_ND0904-H264.mov',
            'duration': 2324.758,
        },
        'params': {
            'skip_download': True,
        },
        'add_ie': ['Ooyala'],
    }]

    def _real_extract(self, url):
        page_id = self._match_id(url)

        webpage = self._download_webpage(url, page_id)

        entries = [
            OoyalaIE._build_url_result(m.group('code'))
            for m in re.finditer(
                r'data-(?:video-id|directVideoId)=(["\'])(?P<code>(?:(?!\1).)+)\1', webpage)]

        title = self._html_search_regex(
            r'(?s)<(?:span|div)[^>]+class="(?:title|wrapper)"[^>]*>.*?<h1>(.+?)</h1>',
            webpage, 'title', fatal=False)

        return self.playlist_result(
            entries, page_id, title)
