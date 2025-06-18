from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import ExtractorError
import re
from urllib.parse import urlparse


class DzsecurityLiveIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(echoroukonline|ennaharonline)\.com/live(?:-news)?'

    _TESTS = [{
        'url': 'https://www.echoroukonline.com/live',
        'info_dict': {
            'id': 'echorouktv',
            'title': r're:البث الحي لقناة الشروق تي في \d{4}-\d{2}-\d{2} \d{2}:\d{2}',
            'ext': 'mp4',
            'live_status': 'is_live',
        }
    }, {
        'url': 'https://www.echoroukonline.com/live-news',
        'info_dict': {
            'id': 'echorouknews',
            'title': r're:البث الحي لقناة الشروق نيوز - آخر أخبار الجزائر \d{4}-\d{2}-\d{2} \d{2}:\d{2}',
            'ext': 'mp4',
            'live_status': 'is_live',
        }
    }]

    def _real_extract(self, url):
        webpage = self._download_webpage(url, url)

        title_match = re.search(r'<title>(.*?)</title>', webpage, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else 'Live Stream'

        player_url_match = re.search(
            r'https://live\.dzsecurity\.net/live/player/([a-zA-Z0-9_-]+)',
            webpage
        )
        if not player_url_match:
            raise ExtractorError("Player URL not found in the page")

        player_url = player_url_match.group(0)
        stream_id = player_url_match.group(1)

        parsed = urlparse(url)
        base_url = f'{parsed.scheme}://{parsed.netloc}'

        headers = {
            'Referer': base_url,
        }

        player_page = self._download_webpage(player_url, player_url, headers=headers)

        m3u8_match = re.search(
            r'src:\s*location\.protocol\s*\+\s*"(?P<url>//[^"]+\.m3u8\?[^"]+)"',
            player_page
        )
        if not m3u8_match:
            raise ExtractorError("M3U8 stream URL not found in player page")

        m3u8_url = parsed.scheme + ':' + m3u8_match.group('url')

        return {
            'id': stream_id,
            'title': title,
            'formats': self._extract_m3u8_formats(
                m3u8_url, stream_id, ext='mp4', entry_protocol='m3u8',
                m3u8_id='hls', fatal=True
            ),
            'is_live': True,
        }
