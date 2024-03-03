from .common import InfoExtractor
from ..utils import (
    ExtractorError
)


class StreaminOneIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?streamin\.one/v/(?P<id>[0-9a-fA-F]+)'
    _TESTS = [{
        'url': 'https://streamin.one/v/6346fb95',
        'md5': 'e97bf97769dbbd09e4e58f703bb008c2',
        'info_dict': {
            'title': 'Video - Sep 30, 2023',
            'id': '6346fb95',
            'ext': 'mp4',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._html_search_regex(
            r'<title>(.+)<', webpage, 'title', default=None)

        # Search for the video URL in the meta tag
        video_url = self._html_search_regex(
            r'<meta property="og:video" content="([^"]+)"',
            webpage, 'video URL', default=None)

        # If not found in the meta tag, search in the video tag
        if not video_url:
            video_url = self._html_search_regex(
                r'<video[^>]+src="([^"]+)"',
                webpage, 'video URL')

        # If the video URL is still not found, raise an error
        if not video_url:
            raise ExtractorError('Could not find video URL')

        # Return the extracted information
        return {
            'title': title,
            'id': video_id,
            'url': video_url,
            'ext': 'mp4',  # you can use a method to determine the file extension from the URL
        }
