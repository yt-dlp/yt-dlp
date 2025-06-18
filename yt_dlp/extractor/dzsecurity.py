import re

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import ExtractorError


class DzsecurityLiveIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(echoroukonline\.com/live(?:-news)?|ennaharonline\.com/live(?:-news)?|elhayat\.dz/%D8%A7%D9%84%D8%A8%D8%AB-%D8%A7%D9%84%D8%AD%D9%8A)'

    _TESTS = [{
        'url': 'https://www.ennaharonline.com/live',
        'info_dict': {
            'id': 'ennahartv',
            'title': r're:البث الحي لقناة النهار &#8211; النهار أونلاين',
            'ext': 'mp4',
            'live_status': 'is_live',
        },
        'skip': 'Geo-restricted to Algeria',
    }, {
        'url': 'https://www.echoroukonline.com/live',
        'info_dict': {
            'id': 'echorouktv',
            'title': r're:البث الحي لقناة الشروق تي في',
            'ext': 'mp4',
            'live_status': 'is_live',
        },
    }, {
        'url': 'https://www.echoroukonline.com/live-news',
        'info_dict': {
            'id': 'echorouknews',
            'title': r're:البث الحي لقناة الشروق نيوز - آخر أخبار الجزائر',
            'ext': 'mp4',
            'live_status': 'is_live',
        },
    }, {
        'url': 'https://elhayat.dz/%D8%A7%D9%84%D8%A8%D8%AB-%D8%A7%D9%84%D8%AD%D9%8A',
        'info_dict': {
            'id': 'elhayattv',
            'title': r're:البث الحي - الحياة',
            'ext': 'mp4',
            'live_status': 'is_live',
        },
    }]

    def _real_extract(self, url):
        webpage = self._download_webpage(url, url)

        title = self._html_extract_title(webpage, default='Live Stream')

        player_url_match = re.search(
            r'https://live\.dzsecurity\.net/live/player/([a-zA-Z0-9_-]+)',
            webpage,
        )
        if not player_url_match:
            raise ExtractorError('Player URL not found in the page')

        player_url = player_url_match.group(0)
        stream_id = player_url_match.group(1)

        base_url_match = re.match(r'(https?://[^/]+)', url)
        if not base_url_match:
            raise ExtractorError('Failed to extract base URL from input URL')

        base_url = base_url_match.group(1)

        headers = {
            'Referer': base_url,
        }

        player_page = self._download_webpage(player_url, player_url, headers=headers)

        m3u8_match = re.search(
            r'src:\s*location\.protocol\s*\+\s*"(?P<url>//[^"]+\.m3u8\?[^"]+)"',
            player_page,
        )
        if not m3u8_match:
            raise ExtractorError('M3U8 stream URL not found in player page')

        m3u8_url = 'https:' + m3u8_match.group('url')

        return {
            'id': stream_id,
            'title': title,
            'formats': self._extract_m3u8_formats(
                m3u8_url, stream_id, ext='mp4', entry_protocol='m3u8',
                m3u8_id='hls', fatal=True,
            ),
            'is_live': True,
        }
