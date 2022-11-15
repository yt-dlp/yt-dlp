from .common import InfoExtractor
from ..utils import clean_html


class OnePlacePodcastIE(InfoExtractor):
    _VALID_URL = r'https?://www\.oneplace\.com/[\w]+/[^/]+/listen/[\w-]+-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.oneplace.com/ministries/a-daily-walk/listen/living-in-the-last-days-part-2-958461.html',
        'info_dict': {
            'id': '958461',
            'ext': 'mp3',
            'title': 'Living in the Last Days Part 2 | A Daily Walk with John Randall',
            'description': 'md5:fbb8f1cf21447ac54ecaa2887fc20c6e',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_valid_url(url).group('id')
        webpage = self._download_webpage(url, video_id)

        media_url = self._search_regex(r'mp3-url="([^"]+)', webpage, 'media_url', fatal=False) or self._search_regex(
            r'<div[^>]+id\s*=\s*"player"[^>]+data-media-url\s*=\s*"(?P<media_url>[^"]+)', webpage,
            'media_url')

        return {
            'id': video_id,
            'url': media_url,
            'title': clean_html(self._search_regex(
                r'<div[^>]class\s*=\s*"details"[^>]+>[^<]<h2[^>]+>(?P<title>[^>]+)>', webpage,
                'title', fatal=False, default=None)) or self._html_search_meta(['og:title', 'title'], webpage),
            'ext': 'mp3',
            'description': clean_html(self._search_regex(
                r'<div[^>]+class="[^"]+epDesc"[^>]*>\s*(?P<desc>.+)', webpage, 'description',
                fatal=False, default=None))
        }
