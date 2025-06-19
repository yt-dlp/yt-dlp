from .common import InfoExtractor

class TheHighWireIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?thehighwire\.com/ark-videos/(?P<id>[^/?#]+)'
    _EMBED_URL = 'https://app.arkengine.com/embed/{id}'
    _TESTS = [{
        'url': 'https://thehighwire.com/ark-videos/the-deposition-of-stanley-plotkin/',
        'info_dict': {
            'id': 'clllgcra301z4ik01x8cwhfu2',
            'title': 'THE DEPOSITION OF STANLEY PLOTKIN',
            'ext': 'mp4',
        },
        'params': {'skip_download': True},
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        iframe_url = self._search_regex(
            r'<iframe[^>]+src=["\'](https?://app\.arkengine\.com/embed/[^"\']+)',
            webpage, 'iframe URL')
        video_id = self._search_regex(
            r'embed/([a-zA-Z0-9]+)', iframe_url, 'video ID')

        player_page = self._download_webpage(
            self._EMBED_URL.format(id=video_id), video_id,
            note='Downloading player page')

        m3u8_url = self._search_regex(
            r'<source[^>]+src=["\']([^"\']+\.m3u8)',
            player_page, 'm3u8 URL')

        title = self._og_search_title(webpage, default=None) or self._html_search_meta(
            'og:title', webpage, 'title', default=video_id)

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'formats': self._extract_m3u8_formats(m3u8_url, video_id, 'mp4'),
        }
