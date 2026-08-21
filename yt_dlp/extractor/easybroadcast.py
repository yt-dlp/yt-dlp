from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    update_url,
    url_or_none,
    urljoin,
)
from ..utils.traversal import require, traverse_obj


class EasyBroadcastLiveIE(InfoExtractor):
    IE_NAME = 'easybroadcast:live'

    _VALID_URL = r'https?://(?:\w+\.)?player\.easybroadcast\.io/events/(?P<id>\w+)'
    _EMBED_REGEX = [rf'<iframe[^>]+\bsrc\s*=\s*["\'](?P<url>{_VALID_URL})']
    _TESTS = [{
        'url': 'https://al24.player.easybroadcast.io/events/66_al24_u4yga6h',
        'info_dict': {
            'id': '66_al24_u4yga6h',
            'title': str,
            'ext': 'mp4',
            'live_status': 'is_live',
        },
        'params': {
            'nocheckcertificate': True,
            'skip_download': 'Livestream',
        },
    }, {
        'url': 'https://snrt.player.easybroadcast.io/events/73_aloula_w1dqfwm',
        'info_dict': {
            'id': '73_aloula_w1dqfwm',
            'title': str,
            'ext': 'mp4',
            'live_status': 'is_live',
        },
        'params': {
            'nocheckcertificate': True,
            'skip_download': 'Livestream',
        },
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://snrtlive.ma/fr/al-aoula',
        'info_dict': {
            'id': '73_aloula_w1dqfwm',
            'title': str,
            'ext': 'mp4',
            'live_status': 'is_live',
        },
        'params': {
            'nocheckcertificate': True,
            'skip_download': 'Livestream',
        },
    }]

    def _real_extract(self, url):
        event_id = self._match_id(url)
        event = self._download_json(
            urljoin(url, f'/api/events/{event_id}'), event_id)
        m3u8_url = traverse_obj(event, (
            'stream', {url_or_none}, {require('m3u8 URL')}))

        token = None
        if traverse_obj(event, ('token_authentication', {bool})):
            token = self._download_webpage(
                'https://token.easybroadcast.io/all',
                event_id, query={'url': m3u8_url})
            if not token:
                raise ExtractorError('Unable to extract token')
            m3u8_url = update_url(m3u8_url, query=token)

        formats = self._extract_m3u8_formats(m3u8_url, event_id, 'mp4')
        if token:
            for fmt in formats:
                fmt['url'] = update_url(fmt['url'], query=token)

        return {
            'id': event_id,
            'title': traverse_obj(event, ('name', {str.upper}, filter)),
            'formats': formats,
            'is_live': True,
        }
