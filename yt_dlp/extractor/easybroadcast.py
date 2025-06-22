
from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import (
    ExtractorError,
)


class EasyBroadcastLiveIE(InfoExtractor):
    _VALID_URL = r'https?://(?:\w+\.)?player\.easybroadcast\.io/events/(?P<id>[0-9a-zA-Z_]+)'
    _TESTS = [
        {
            'url': 'https://al24.player.easybroadcast.io/events/66_al24_u4yga6h',
            'info_dict': {
                'id': '66_al24_u4yga6h',
                'title': 'Al24',
                'ext': 'mp4',
                'live_status': 'is_live',
            },
        },
        {
            'url': 'https://snrt.player.easybroadcast.io/events/73_aloula_w1dqfwm',
            'info_dict': {
                'id': '73_aloula_w1dqfwm',
                'title': 'Aloula',
                'ext': 'mp4',
                'live_status': 'is_live',
            },
        },
        {
            'url': 'https://captaprod.player.easybroadcast.io/events/54_tvr_vtucuxt',
            'info_dict': {
                'id': '54_tvr_vtucuxt',
                'title': 'TVR',
                'ext': 'mp4',
                'live_status': 'is_live',
            },
        },
    ]

    def _real_extract(self, url):
        event_id = self._match_id(url)

        base_url = url.split('/events/')[0]
        api_url = f'{base_url}/api/events/{event_id}'
        metadata = self._download_json(api_url, event_id, note='Downloading EasyBroadcast event metadata')

        m3u8_url = metadata.get('stream')
        token = None
        if metadata.get('token_authentication', False):
            token_api_url = f'https://token.easybroadcast.io/all?url={m3u8_url}'
            token = self._download_webpage(token_api_url, event_id, note='Fetching stream token').strip()
            m3u8_url = m3u8_url + '?' + token
            if not token:
                raise ExtractorError('Empty token returned from token server.')

        formats = self._extract_m3u8_formats(m3u8_url, video_id=event_id, ext='mp4', m3u8_id='hls', live=True)

        if token:
            for fmt in formats:
                fmt['url'] = fmt['url'] + '?' + token

        return {
            'id': event_id,
            'title': metadata.get('name', event_id),
            'formats': formats,
            'is_live': True,
        }
