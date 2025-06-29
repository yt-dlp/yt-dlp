import re

from .common import InfoExtractor
from ..utils import ExtractorError
from ..utils.traversal import traverse_obj


class FaulioLiveIE(InfoExtractor):
    _VALID_URL = (
        r'https?://(?P<domain>aloula\.sba\.sa|maraya\.sba\.net\.ae|sat7plus\.org)/'
        r'(?:en/)?live/(?P<faulio_url>[a-zA-Z0-9\-]+)'
    )

    _TESTS = [{
        'url': 'https://aloula.sba.sa/live/saudiatv',
        'info_dict': {
            'id': '2',
            'title': str,
            'description': str,
            'ext': 'mp4',
            'live_status': 'is_live',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }, {
        'url': 'https://aloula.sba.sa/live/sbc-channel',
        'info_dict': {
            'id': '1',
            'title': str,
            'description': str,
            'ext': 'mp4',
            'live_status': 'is_live',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }, {
        'url': 'https://maraya.sba.net.ae/live/1',
        'info_dict': {
            'id': '1',
            'title': str,
            'description': str,
            'ext': 'mp4',
            'live_status': 'is_live',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }, {
        'url': 'https://maraya.sba.net.ae/live/14',
        'info_dict': {
            'id': '14',
            'title': str,
            'description': str,
            'ext': 'mp4',
            'live_status': 'is_live',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        faulio_url = mobj.group('faulio_url')

        webpage = self._download_webpage(url, faulio_url)

        api_url_match = re.search(r'TRANSLATIONS_API_URL\s*:\s*"(https?://[^"]+)"', webpage)
        if not api_url_match:
            raise ExtractorError('Could not find TRANSLATIONS_API_URL in the page')
        api_base = api_url_match.group(1)

        channels_json = self._download_json(f'{api_base}/channels', faulio_url)

        channel_json = next(
            (c for c in channels_json if str(c.get('url')) == faulio_url),
            None,
        )
        if not channel_json:
            raise ExtractorError(f'Channel "{faulio_url}" not found in API')

        hls_url = traverse_obj(channel_json, ('streams', 'hls'))
        if not hls_url:
            raise ExtractorError(f'HLS stream not found for channel "{faulio_url}"')

        domain = mobj.group('domain')
        headers = {
            'Referer': f'https://{domain}/',
            'Origin': f'https://{domain}',
        }

        return {
            'id': str(channel_json.get('id')),
            'title': channel_json.get('title'),
            'description': channel_json.get('description'),
            'formats': self._extract_m3u8_formats(hls_url, faulio_url, 'mp4', m3u8_id='hls', live=True,
                                                  headers=headers),
            'is_live': True,
            'http_headers': headers,
        }
