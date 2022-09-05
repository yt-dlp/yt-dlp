from .common import InfoExtractor
from ..utils import *


class PStreamIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?pstream\.net/(e|v)/(?P<id>[a-zA-Z0-9]+)'
    _TESTS = [{
        'url': 'https://www.pstream.net/e/YdX2V1RLJjJVayY',
        'md5': 'ff370a5aea3f7bbb1e5a7535a80b1e8aebf5c8d7a1f7c80995e550696d2f7659',
        'info_dict': {
            'id': 'mQN5YQKD6jLXvRa',
            'ext': 'mp4',
            'title': 'How I Keep My House In Order',
            'thumbnail': r're^https?://i.pstream\.net/\w*/\w*/\w*\.jpg$',
            # TODO more properties, either as:
            # * A value
            # * MD5 checksum; start the string with md5:
            # * A regular expression; start the string with re:
            # * Any Python type, e.g. int or float
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        # TODO more code goes here, for example ...
        title = self._html_search_regex(r'<meta name="og:title" content="(\w*)">', webpage, 'title')

        return {
            'id': video_id,
            'title': title,
            # 'description': self._og_search_description(webpage),
            # 'uploader': self._search_regex(r'<div[^>]+id="uploader"[^>]*>([^<]+)<', webpage, 'uploader', fatal=False),
            # TODO more properties (see yt_dlp/extractor/common.py)
        }


# print(PStreamIE._real_extract("https://www.pstream.net/e/YdX2V1RLJjJVayY"))
