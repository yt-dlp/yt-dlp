import urllib.parse

from .common import InfoExtractor
from ..utils import clean_html, urljoin


class JoqrAgIE(InfoExtractor):
    IE_DESC = '超!A&G+ 文化放送 Nippon Cultural Broadcasting, Inc. (JOQR)'
    _VALID_URL = [r'https?://www\.uniqueradio\.jp/agplayer5/player\.php',
                  r'https?://www\.uniqueradio\.jp/agplayer5/inc-player-hls\.php',
                  r'https?://(?:www\.)?joqr\.co\.jp/ag/',
                  r'https?://(?:www\.)?joqr\.co\.jp/qr/(?:agdailyprogram|agregularprogram)/']
    _TESTS = [{
        'url': 'https://www.uniqueradio.jp/agplayer5/player.php',
        'info_dict': {
            'id': 'live',
            'title': str,
            'description': str,
            'live_status': 'is_live',
        },
        'params': {
            'skip_download': True,
            'ignore_no_formats_error': True,
        },
    }]

    def _real_extract(self, url):
        video_id = 'live'

        metadata = self._download_webpage(
            'https://www.uniqueradio.jp/aandg', video_id,
            note='Downloading metadata', errnote='Failed to download metadata')
        title = clean_html(urllib.parse.unquote_plus(
            self._search_regex(r'var\s+Program_name\s*=\s*["\']([^"\']+)["\']', metadata, 'program title')))
        desc = clean_html(urllib.parse.unquote_plus(
            self._search_regex(r'var\s+Program_text\s*=\s*["\']([^"\']+)["\']', metadata, 'program description')))

        m3u8_path = self._search_regex(
            r'<source\s[^>]*\bsrc="([^"]+)"',
            self._download_webpage(
                'https://www.uniqueradio.jp/agplayer5/inc-player-hls.php', video_id,
                note='Downloading player data', errnote='Failed to download player data'),
            'm3u8 url')
        formats = self._extract_m3u8_formats(
            urljoin('https://www.uniqueradio.jp/', m3u8_path), video_id, fatal=False)

        return {
            'id': video_id,
            'title': title,
            'channel': '超!A&G+',
            'description': desc,
            'formats': formats,
            'live_status': 'is_live',
        }
