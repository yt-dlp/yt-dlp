import json

from .common import InfoExtractor
from ..utils import traverse_obj


class NoveTVLiveIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?nove\.tv/live-streaming-nove'

    _TESTS = [{
        'url': 'https://www.nove.tv/live-streaming-nove',
        'info_dict': {
            'id': 'nove-tv-live',
            'ext': 'mp4',
            'title': 'Nove TV Live',
        },
    }]

    def _real_extract(self, url):
        token = traverse_obj(self._download_json('https://public.aurora.enhanced.live/token?realm=it', 'nove-tv-live', 'Downloading token'),
                             ('data', 'attributes', 'token'))
        playback_info = self._download_json(
            'https://public.aurora.enhanced.live/playback/v3/channelPlaybackInfo', 'nove-tv-live', 'Downloading playback info',
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            data=json.dumps({'deviceInfo':
                             {'adBlocker': False, 'drmSupported': False, 'hdrCapabilities': ['SDR'],
                              'hwDecodingCapabilities': [], 'soundCapabilities': ['STEREO']},
                             'wisteriaProperties': {'platform': 'desktop'},
                             'channelId': '3'}).encode())
        formats = []

        for fmt in traverse_obj(playback_info, ('data', 'attributes', 'streaming')):
            if fmt.get('type') == 'hls':
                formats.extend(self._extract_m3u8_formats(fmt['url'], 'nove-tv-live'))
            elif fmt.get('type') == 'dash':
                formats.extend(self._extract_mpd_formats(fmt['url'], 'nove-tv-live'))
        return {
            'id': 'nove-tv-live',
            'title': 'Nove TV Live',
            'is_live': True,
            'formats': formats,
        }
