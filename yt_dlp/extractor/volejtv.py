from .common import InfoExtractor


class VolejTVIE(InfoExtractor):
    _VALID_URL = r'https?://volej\.tv/video/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://volej.tv/video/725742/',
        'info_dict': {
            'id': '725742',
            'ext': 'mp4',
            'description': 'Zápas VK Královo Pole vs VK Prostějov 10.12.2022 v 19:00 na Volej.TV',
            'thumbnail': 'https://volej.tv/images/og/16/17186/og.png',
            'title': 'VK Královo Pole vs VK Prostějov',
        }
    }, {
        'url': 'https://volej.tv/video/725605/',
        'info_dict': {
            'id': '725605',
            'ext': 'mp4',
            'thumbnail': 'https://volej.tv/images/og/15/17185/og.png',
            'title': 'VK Lvi Praha vs VK Euro Sitex Příbram',
            'description': 'Zápas VK Lvi Praha vs VK Euro Sitex Příbram 11.12.2022 v 19:00 na Volej.TV',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        json_data = self._search_json(
            r'<\s*!\[CDATA[^=]+=', webpage, 'CDATA', video_id)
        formats, subtitle = self._extract_m3u8_formats_and_subtitles(
            json_data['urls']['hls'], video_id)
        return {
            'id': video_id,
            'title': self._html_search_meta(['og:title', 'twitter:title'], webpage),
            'thumbnail': self._html_search_meta(['og:image', 'twitter:image'], webpage),
            'description': self._html_search_meta(['description', 'og:description', 'twitter:description'], webpage),
            'formats': formats,
            'subtitles': subtitle,
        }
