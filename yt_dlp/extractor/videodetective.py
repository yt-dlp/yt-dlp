from __future__ import unicode_literals

from .common import InfoExtractor
from .internetvideoarchive import InternetVideoArchiveIE


class VideoDetectiveIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?videodetective\.com/[^/]+/[^/]+/(?P<id>\d+)'

    _TEST = {
        'url': 'http://www.videodetective.com/movies/kick-ass-2/194487',
        'info_dict': {
            'id': '194487',
            'ext': 'mp4',
            'title': 'Kick-Ass 2',
            'description': 'md5:c189d5b7280400630a1d3dd17eaa8d8a',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        query = 'customerid=69249&publishedid=' + video_id
        return self.url_result(
            InternetVideoArchiveIE._build_json_url(query),
            ie=InternetVideoArchiveIE.ie_key())
