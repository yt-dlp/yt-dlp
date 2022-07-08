from .common import InfoExtractor


class Liputan6IE(InfoExtractor):
    _VALID_URL = r'https?://www\.liputan6\.com/news/read/\d+/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.liputan6.com/news/read/5007510/video-duh-perawat-rs-di-medan-diduga-salah-berikan-obat-ke-pasien',
        'info_dict': {
            'id': 'fixme',
            'ext': 'mp4',
        }
    }]
    
    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        
        json_data = self._search_json(
        r'window.kmklabs.gtm\s*=\s*', webpage, 'json_data', display_id)
        
        m3u8_url = None
        video_id = json_data['videos']['video_1']['video_id']
        if json_data['videoSource'] == 'Vidio':
            m3u8_url = f'https://www.vidio.com/videos/{video_id}/common_tokenized_playlist.m3u8'
        
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(m3u8_url, video_id)
        
        self._sort_formats(formats)
        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'title': self._html_search_meta('title', webpage)
        }