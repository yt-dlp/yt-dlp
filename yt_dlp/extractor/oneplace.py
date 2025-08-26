from .common import InfoExtractor


class OnePlacePodcastIE(InfoExtractor):
    _VALID_URL = r'https?://www\.oneplace\.com/[\w]+/[^/]+/listen/[\w-]+-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.oneplace.com/ministries/a-daily-walk/listen/living-in-the-last-days-part-2-958461.html',
        'info_dict': {
            'id': '958461',
            'ext': 'mp3',
            'title': 'Living in the Last Days Part 2 | A Daily Walk with John Randall',
            'description': 'md5:fbb8f1cf21447ac54ecaa2887fc20c6e',
        },
    }, {
        'url': 'https://www.oneplace.com/ministries/ankerberg-show/listen/ep-3-relying-on-the-constant-companionship-of-the-holy-spirit-part-2-922513.html',
        'info_dict': {
            'id': '922513',
            'ext': 'mp3',
            'description': 'md5:8b810b4349aa40a5d033b4536fe428e1',
            'title': 'md5:ce10f7d8d5ddcf485ed8905ef109659d',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        return {
            'id': video_id,
            'url': self._search_regex((
                r'mp3-url\s*=\s*"([^"]+)',
                r'<div[^>]+id\s*=\s*"player"[^>]+data-media-url\s*=\s*"(?P<media_url>[^"]+)',
            ), webpage, 'media url'),
            'ext': 'mp3',
            'vcodec': 'none',
            'title': self._html_search_regex((
                r'<div[^>]class\s*=\s*"details"[^>]+>[^<]<h2[^>]+>(?P<content>[^>]+)>',
                self._meta_regex('og:title'), self._meta_regex('title'),
            ), webpage, 'title', group='content', default=None),
            'description': self._html_search_regex(
                r'<div[^>]+class="[^"]+epDesc"[^>]*>\s*(?P<desc>.+?)\s*</div>',
                webpage, 'description', default=None),
        }
