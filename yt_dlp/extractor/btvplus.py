from .common import InfoExtractor


class BTVPlusIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?btvplus\.bg/produkt/predavaniya/(?P<id>\d+)/.*'
    _TESTS = [{
        'url': 'https://btvplus.bg/produkt/predavaniya/60119/sezon-1/ostrovat-na-100-te-grivni-sezon-1-epizod-11-02-10-2024',
        'info_dict': {
            'id': '6011911111',
            'title': 'Островът на 100-те гривни Сезон 1, епизод 11',
            'formats': 'count:1',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        product_url = self._search_regex(
            r"var videoUrl\s*=\s*['\"]([^'\"]+)['\"];",
            webpage, 'product player URL')

        product_url = 'https://btvplus.bg' + product_url

        player_data = self._download_json(product_url, video_id)

        m3u8_url = self._search_regex(
            r'(https?://[^"]+\.m3u8)',
            player_data['config'], 'M3U8 URL')

        formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', m3u8_id='hls')

        title = self._search_regex(
            r'<span class="title">\s*(.*?)\s*</span>',
            webpage, 'video title', default='Unknown Title')

        return {
            'id': video_id,
            'title': title,
            'thumbnail': self._og_search_thumbnail(webpage),
            'description': self._og_search_description(webpage),
            'formats': formats,
        }
