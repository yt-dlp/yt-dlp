
from .common import InfoExtractor
from ..utils import (
    smuggle_url,
    unsmuggle_url,
)
from ..utils.traversal import traverse_obj


class DzsecurityLiveIE(InfoExtractor):
    _VALID_URL = r'https?://live\.dzsecurity\.net/live/player/(?P<id>[\w-]+)'
    _EMBED_REGEX = [rf'<iframe[^>]+\bsrc\s*=\s*["\'](?P<url>{_VALID_URL})']

    _WEBPAGE_TESTS = [{
        'url': 'https://www.echoroukonline.com/live',
        'info_dict': {
            'id': 'echorouktv',
            'title': str,
            'ext': 'mp4',
            'live_status': 'is_live',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }, {
        'url': 'https://www.echoroukonline.com/live-news',
        'info_dict': {
            'id': 'echorouknews',
            'title': str,
            'ext': 'mp4',
            'live_status': 'is_live',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }, {
        'url': 'https://elhayat.dz/%D8%A7%D9%84%D8%A8%D8%AB-%D8%A7%D9%84%D8%AD%D9%8A/',
        'info_dict': {
            'id': 'elhayattv',
            'title': str,
            'ext': 'mp4',
            'live_status': 'is_live',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }, {
        'url': 'https://www.ennaharonline.com/live',
        'info_dict': {
            'id': 'ennahartv',
            'title': str,
            'ext': 'mp4',
            'live_status': 'is_live',
        },
        'params': {
            'skip_download': 'Livestream',
        },
        'skip': 'Geo-restricted to Algeria',
    }]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        for embed_url in super()._extract_embed_urls(url, webpage):
            yield smuggle_url(embed_url, {'referer': url})

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})

        stream_id = self._match_id(url)

        title = stream_id
        referer = smuggled_data['referer']
        if referer:
            webpage = self._download_webpage(referer, referer)
            title = self._html_extract_title(webpage, default=title)

        player_page = self._download_webpage(url, stream_id, headers=traverse_obj(smuggled_data, {'Referer': 'referer'}))

        m3u8_url = 'https:' + self._search_regex(
            r'src:\s*location\.protocol\s*\+\s*"(//[^"]+\.m3u8\?[^"]+)"',
            player_page,
            'm3u8 URL',
        )

        return {
            'id': stream_id,
            'title': title,
            'formats': self._extract_m3u8_formats(m3u8_url, stream_id),
            'is_live': True,
        }
