import re

from .common import InfoExtractor
from ..utils import unified_strdate


class TeleTaskIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'https?://(?:www\.)?tele-task\.de/archive/video/html5/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'http://www.tele-task.de/archive/video/html5/26168/',
        'info_dict': {
            'id': '26168',
            'title': 'Duplicate Detection',
        },
        'playlist': [{
            'md5': '290ef69fb2792e481169c3958dbfbd57',
            'info_dict': {
                'id': '26168-speaker',
                'ext': 'mp4',
                'title': 'Duplicate Detection',
                'upload_date': '20141218',
            }
        }, {
            'md5': 'e1e7218c5f0e4790015a437fcf6c71b4',
            'info_dict': {
                'id': '26168-slides',
                'ext': 'mp4',
                'title': 'Duplicate Detection',
                'upload_date': '20141218',
            }
        }]
    }

    def _real_extract(self, url):
        lecture_id = self._match_id(url)
        webpage = self._download_webpage(url, lecture_id)

        title = self._html_search_regex(
            r'itemprop="name">([^<]+)</a>', webpage, 'title')
        upload_date = unified_strdate(self._html_search_regex(
            r'Date:</td><td>([^<]+)</td>', webpage, 'date', fatal=False))

        entries = [{
            'id': '%s-%s' % (lecture_id, format_id),
            'url': video_url,
            'title': title,
            'upload_date': upload_date,
        } for format_id, video_url in re.findall(
            r'<video class="([^"]+)"[^>]*>\s*<source src="([^"]+)"', webpage)]

        return self.playlist_result(entries, lecture_id, title)
