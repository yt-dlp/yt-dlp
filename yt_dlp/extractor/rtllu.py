from .common import InfoExtractor


class RTLLuIE(InfoExtractor):
    IE_NAME = 'rtl.lu'
    _VALID_URL = r'https?://www\.rtl\.lu/(?:tele)?/(?P<slug>[\w-]+)/v/(?P<id>\d+)\.html'
    _TESTS = [{
        'url': 'https://www.rtl.lu/tele/de-journal-vun-der-tele/v/3266757.html',
        'info_dict': {
            'id': '3266757',
            'title': '""',
            'ext': 'mp4',
            'display_id': 'de-journal-vun-der-tele',
            'thumbnail': '"https://replay-assets.rtl.lu/2021/11/16/d3647fc4-470d-11ec-adc2-3a00abd6e90f_00008.jpg"'
        }
    }]
    
    def _real_extract(self, url):
        video_slug, video_id = self._match_valid_url(url).group('slug', 'id')
        webpage = self._download_webpage(url, video_slug)
        
        thumbnail_url, title, hls_url = self._search_regex(
            r'<rtl-player\s*poster\s*=\s*(?P<thumbnail_url>[\"\w\.://-]+)\s*title\s*=\s*(?P<title>[\"\w\.-]+)\s*hls\s*=\s*\"(?P<hls_url>[\w\.\:/-]+)\"',
            webpage, 'required_data', group=('thumbnail_url', 'title', 'hls_url'))
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(hls_url, video_slug)
        self._sort_formats(formats)
        return {
            'id': video_id,
            'display_id': video_slug,
            'title': title,
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': thumbnail_url,
        }