from .common import InfoExtractor


class ScreenRecIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?screenrec\.com/share/(?P<id>\w{10})'
    _TESTS = [{
        'url': 'https://screenrec.com/share/DasLtbknYo',
        'info_dict': {
            'id': 'DasLtbknYo',
            'ext': 'mp4',
            'title': '02.05.2024_03.01.25_REC',
            'description': 'Recorded with ScreenRec',
            'thumbnail': r're:^https?://.*\.gif$',
        },
        'params': {
            'skip_download': True,
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
