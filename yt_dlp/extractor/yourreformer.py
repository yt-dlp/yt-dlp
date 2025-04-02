from .common import InfoExtractor


class YourReformerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?yourreformerathome\.uscreen\.io/programs/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://yourreformerathome.uscreen.io/programs/arms-back-abs-7-with-erin?category_id=139586',
        'info_dict': {
            'id': 'arms-back-abs-7-with-erin',
            'ext': 'mp4',
            'title': 'Arms, Back & Abs 7',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        program_content_url = f'https://yourreformerathome.uscreen.io/programs/{video_id}/program_content'

        program_content = self._download_webpage(
            program_content_url, video_id,
            note='Downloading program content')
        title = self._html_search_regex(
            r'<h1[^>]*class="[^"]*program-title[^"]*"[^>]*>([^<]+)',
            program_content, 'title', default=None) or video_id.replace('-', ' ').title()
        headers = {
            'referer': 'https://yourreformerathome.uscreen.io/',
        }
        m3u8_url = self._search_regex(
            r'(https?://stream\.mux\.com/[^.]+\.m3u8(?:\?token=[^"\'&]+)?)',
            program_content, 'm3u8 url')
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            m3u8_url, video_id, 'mp4', 'm3u8_native',
            m3u8_id='hls', headers=headers)
        for f in formats:
            f.setdefault('http_headers', {}).update(headers)
        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'subtitles': subtitles,
        }
