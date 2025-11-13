from .common import InfoExtractor


class BrownPornIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tyler-brown\.com/watch/(?P<id>[0-9-_]+)'
    _TESTS = [{
        'url': 'https://tyler-brown.com/watch/-186023723_456239021',
        'md5': '22c40aaf1b7013f6d3950f3a79f5e1dd',
        'info_dict': {
            'id': '-186023723_456239021',
            'ext': 'mp4',
            'title': 'Katee owen hot big bouncing boobs dance',
            'age_limit': 18,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        formats = []

        sources = self._search_json('window.playlist =', webpage, 'sources', video_id).get('sources')

        resolutions = [
            '144',
            '240',
            '360',
            '480',
            '720',
        ]

        for resolution in resolutions:
            source = next((s for s in sources if s.get('label') == resolution), None)

            if source and source.get('file'):
                url = source.get('file')
                formats.append({
                    'url': url,
                    'format_id': resolution,
                })

        title = self._og_search_title(webpage) or self._html_search_regex(r'<h1>(.+?)</h1>', webpage, 'title')

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'age_limit': 18,
        }
