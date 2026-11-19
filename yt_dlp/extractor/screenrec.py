from .common import InfoExtractor
from ..utils import js_to_json, unified_strdate

class ScreenRecIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?screenrec\.com/share/(?P<id>\w{10})'
    _TESTS = [{
        'url': 'https://screenrec.com/share/ZHwdTfY23O',
        'info_dict': {
            'id': 'DasLtbknYo',
            'id': 'ZHwdTfY23O',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.*\.gif',
            'upload_date': '20261117',
            'title': '17.11.2026_12.01.13_REC',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        m3u8_url = self._search_regex(
            r'customUrl\s*:\s*(["\'])(?P<url>(?:(?!\1).)+)\1', webpage, 'm3u8 URL', group='url')

        return {
            'id': video_id,
            'title': self._og_search_title(webpage, default=None) or self._html_extract_title(webpage),
            'description': self._og_search_description(webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
            'formats': self._extract_m3u8_formats(m3u8_url, video_id, ext='mp4'),
        }
