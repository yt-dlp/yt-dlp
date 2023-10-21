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
            'channel': '超!A&G+',
            'description': str,
            'live_status': 'is_live',
        },
        'params': {
            'skip_download': True,
            'ignore_no_formats_error': True,
        },
    }, {
        'url': 'https://www.uniqueradio.jp/agplayer5/inc-player-hls.php',
        'only_matching': True,
    }, {
        'url': 'https://www.joqr.co.jp/ag/article/103760/',
        'only_matching': True,
    }, {
        'url': 'http://www.joqr.co.jp/qr/agdailyprogram/',
        'only_matching': True,
    }, {
        'url': 'http://www.joqr.co.jp/qr/agregularprogram/',
        'only_matching': True,
    }]

    def _extract_metadata(self, variable, html, name):
        return clean_html(urllib.parse.unquote_plus(self._search_regex(
            rf'var\s+{variable}\s*=\s*["\']([^"\']+)["\']', html, name, default=''))) or None

    def _real_extract(self, url):
        video_id = 'live'

        metadata = self._download_webpage(
            'https://www.uniqueradio.jp/aandg', video_id,
            note='Downloading metadata', errnote='Failed to download metadata')
        title = self._extract_metadata('Program_name', metadata, 'program title')
        desc = self._extract_metadata('Program_text', metadata, 'program description')

        if title == '放送休止':
            self.raise_no_formats('This stream has not started yet', expected=True)
            formats = []
            live_status = 'is_upcoming'
        else:
            m3u8_path = self._search_regex(
                r'<source\s[^>]*\bsrc="([^"]+)"',
                self._download_webpage(
                    'https://www.uniqueradio.jp/agplayer5/inc-player-hls.php', video_id,
                    note='Downloading player data', errnote='Failed to download player data'),
                'm3u8 url')
            formats = self._extract_m3u8_formats(
                urljoin('https://www.uniqueradio.jp/', m3u8_path), video_id, fatal=False)
            live_status = 'is_live'

        return {
            'id': video_id,
            'title': title,
            'channel': '超!A&G+',
            'description': desc,
            'formats': formats,
            'live_status': live_status,
        }
