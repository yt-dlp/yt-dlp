import re

from .common import InfoExtractor
from .youtube import YoutubeIE
from ..utils import (
    parse_iso8601,
    str_to_int,
)


class CrackedIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?cracked\.com/video_(?P<id>\d+)_[\da-z-]+\.html'
    _TESTS = [{
        'url': 'http://www.cracked.com/video_19070_if-animal-actors-got-e21-true-hollywood-stories.html',
        'md5': '89b90b9824e3806ca95072c4d78f13f7',
        'info_dict': {
            'id': '19070',
            'ext': 'mp4',
            'title': 'If Animal Actors Got E! True Hollywood Stories',
            'timestamp': 1404954000,
            'upload_date': '20140710',
        }
    }, {
        # youtube embed
        'url': 'http://www.cracked.com/video_19006_4-plot-holes-you-didnt-notice-in-your-favorite-movies.html',
        'md5': 'ccd52866b50bde63a6ef3b35016ba8c7',
        'info_dict': {
            'id': 'EjI00A3rZD0',
            'ext': 'mp4',
            'title': "4 Plot Holes You Didn't Notice in Your Favorite Movies - The Spit Take",
            'description': 'md5:c603708c718b796fe6079e2b3351ffc7',
            'upload_date': '20140725',
            'uploader_id': 'Cracked',
            'uploader': 'Cracked',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        youtube_url = YoutubeIE._extract_url(webpage)
        if youtube_url:
            return self.url_result(youtube_url, ie=YoutubeIE.ie_key())

        video_url = self._html_search_regex(
            [r'var\s+CK_vidSrc\s*=\s*"([^"]+)"', r'<video\s+src="([^"]+)"'],
            webpage, 'video URL')

        title = self._search_regex(
            [r'property="?og:title"?\s+content="([^"]+)"', r'class="?title"?>([^<]+)'],
            webpage, 'title')

        description = self._search_regex(
            r'name="?(?:og:)?description"?\s+content="([^"]+)"',
            webpage, 'description', default=None)

        timestamp = self._html_search_regex(
            r'"date"\s*:\s*"([^"]+)"', webpage, 'upload date', fatal=False)
        if timestamp:
            timestamp = parse_iso8601(timestamp[:-6])

        view_count = str_to_int(self._html_search_regex(
            r'<span\s+class="?views"? id="?viewCounts"?>([\d,\.]+) Views</span>',
            webpage, 'view count', fatal=False))
        comment_count = str_to_int(self._html_search_regex(
            r'<span\s+id="?commentCounts"?>([\d,\.]+)</span>',
            webpage, 'comment count', fatal=False))

        m = re.search(r'_(?P<width>\d+)X(?P<height>\d+)\.mp4$', video_url)
        if m:
            width = int(m.group('width'))
            height = int(m.group('height'))
        else:
            width = height = None

        return {
            'id': video_id,
            'url': video_url,
            'title': title,
            'description': description,
            'timestamp': timestamp,
            'view_count': view_count,
            'comment_count': comment_count,
            'height': height,
            'width': width,
        }
