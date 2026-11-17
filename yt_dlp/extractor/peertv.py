from .common import InfoExtractor
from ..utils import js_to_json


class PeerTVIE(InfoExtractor):
    IE_NAME = 'peer.tv'
    _VALID_URL = r'https?://(?:www\.)?peer\.tv/(?:de|it|en)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.peer.tv/de/841',
        'info_dict': {
            'id': '841',
            'ext': 'mp4',
            'title': 'Die Brunnenburg',
            'description': 'md5:4395f6142b090338340ab88a3aae24ed',
        },
    }, {
        'url': 'https://www.peer.tv/it/404',
        'info_dict': {
            'id': '404',
            'ext': 'mp4',
            'title': 'Cascate di ghiaccio in Val Gardena',
            'description': 'md5:e8e5907f236171842674e8090e3577b8',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        video_key = self._html_search_regex(r'player\.peer\.tv/js/([a-zA-Z0-9]+)', webpage, 'video key')

        js = self._download_webpage(f'https://player.peer.tv/js/{video_key}/', video_id,
                                    headers={'Referer': 'https://www.peer.tv/'}, note='Downloading session id')

        session_id = self._search_regex(r'["\']session_id["\']:\s*["\']([a-zA-Z0-9]+)["\']', js, 'session id')

        player_webpage = self._download_webpage(
            f'https://player.peer.tv/jsc/{video_key}/{session_id}?jsr=aHR0cHM6Ly93d3cucGVlci50di9kZS84NDE=&cs=UTF-8&mq=2&ua=0&webm=p&mp4=p&hls=1',
            video_id, note='Downloading player webpage')

        m3u8_url = self._search_regex(r'["\']playlist_url["\']:\s*(["\'][^"\']+["\'])', player_webpage, 'm3u8 url')
        m3u8_url = self._parse_json(m3u8_url, video_id, transform_source=js_to_json)

        formats = self._extract_m3u8_formats(m3u8_url, video_id, m3u8_id='hls')

        return {
            'id': video_id,
            'title': self._html_search_regex(r'<h1>(.+?)</h1>', webpage, 'title').replace('\xa0', ' '),
            'formats': formats,
            'description': self._html_search_meta(('og:description', 'description'), webpage),
            'thumbnail': self._html_search_meta(('og:image', 'image'), webpage),
        }
