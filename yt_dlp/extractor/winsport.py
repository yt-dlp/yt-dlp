from .common import InfoExtractor


class WinsportIE(InfoExtractor):
    _VALID_URL = r'https?://www\.winsports\.co/videos/(?P<display_id>[\w-]+)-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.winsports.co/videos/siempre-castellanos-gran-atajada-del-portero-cardenal-para-evitar-la-caida-de-su-arco-60536',
        'info_dict': {
            'id': 'fixme',
            'ext': 'mp4',
        }
    }]
    
    def _real_extract(self, url):
        display_id, video_id = self._match_valid_url(url).group('display_id', 'id')
        webpage = self._download_webpage(url, display_id)
        mediastream_json = self._search_json('mediastream_formatter"', webpage, 'mediastream_formatter', display_id)
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(mediastream_json.get('mediastream_id'), display_id)
        self._sort_formats(formats)
        return {
            'id': video_id,
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
            'title': self._html_extract_title(webpage),
        }
        
        