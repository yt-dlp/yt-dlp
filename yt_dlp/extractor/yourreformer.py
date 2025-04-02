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

        # Extract category_id from the URL
        category_id = None
        if '?' in url:
            query = url.split('?', 1)[1]
            for param in query.split('&'):
                if param.startswith('category_id='):
                    category_id = param.split('=', 1)[1]
                    break

        # Construct the program_content URL
        program_content_url = f'https://yourreformerathome.uscreen.io/programs/{video_id}/program_content'
        query_params = {
            'category_id': category_id,
            'playlist_position': 'sidebar',
            'preview': 'false',
        }

        # Request headers for both requests
        headers = {
            'accept': '*/*',
            'accept-language': 'en-AU,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'no-cache',
            'origin': 'https://yourreformerathome.uscreen.io',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://yourreformerathome.uscreen.io/',
            'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        }

        # Get the program content
        program_content = self._download_webpage(
            program_content_url, video_id, query=query_params,
            note='Downloading program content')

        # Extract the video title
        title = self._html_search_regex(
            r'<h1[^>]*class="[^"]*program-title[^"]*"[^>]*>([^<]+)',
            program_content, 'title', default=None) or video_id.replace('-', ' ').title()

        # Extract the m3u8 URL
        m3u8_url = self._search_regex(
            r'(https?://stream\.mux\.com/[^.]+\.m3u8(?:\?token=[^"\'&]+)?)',
            program_content, 'm3u8 url')

        # Get the m3u8 manifest
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            m3u8_url, video_id, 'mp4', 'm3u8_native',
            m3u8_id='hls', headers=headers)

        # Set the http headers for all formats to ensure proper download
        for f in formats:
            f.setdefault('http_headers', {}).update(headers)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'subtitles': subtitles,
        }
