from .common import InfoExtractor


class HentaiStigmaIE(InfoExtractor):
    _VALID_URL = r'^https?://hentai\.animestigma\.com/(?P<id>[^/]+)'
    _TEST = {
        'url': 'http://hentai.animestigma.com/inyouchuu-etsu-bonus/',
        'md5': '4e3d07422a68a4cc363d8f57c8bf0d23',
        'info_dict': {
            'id': 'inyouchuu-etsu-bonus',
            'ext': 'mp4',
            'title': 'Inyouchuu Etsu Bonus',
            'age_limit': 18,
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        title = self._html_search_regex(
            r'<h2[^>]+class="posttitle"[^>]*><a[^>]*>([^<]+)</a>',
            webpage, 'title')
        wrap_url = self._html_search_regex(
            r'<iframe[^>]+src="([^"]+mp4)"', webpage, 'wrapper url')
        wrap_webpage = self._download_webpage(wrap_url, video_id)

        video_url = self._html_search_regex(
            r'file\s*:\s*"([^"]+)"', wrap_webpage, 'video url')

        return {
            'id': video_id,
            'url': video_url,
            'title': title,
            'age_limit': 18,
        }
