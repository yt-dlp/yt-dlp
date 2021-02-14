from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import parse_duration


class HistoricFilmsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?historicfilms\.com/(?:tapes/|play)(?P<id>\d+)'
    _TEST = {
        'url': 'http://www.historicfilms.com/tapes/4728',
        'md5': 'd4a437aec45d8d796a38a215db064e9a',
        'info_dict': {
            'id': '4728',
            'ext': 'mov',
            'title': 'Historic Films: GP-7',
            'description': 'md5:1a86a0f3ac54024e419aba97210d959a',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 2096,
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        tape_id = self._search_regex(
            [r'class="tapeId"[^>]*>([^<]+)<', r'tapeId\s*:\s*"([^"]+)"'],
            webpage, 'tape id')

        title = self._og_search_title(webpage)
        description = self._og_search_description(webpage)
        thumbnail = self._html_search_meta(
            'thumbnailUrl', webpage, 'thumbnails') or self._og_search_thumbnail(webpage)
        duration = parse_duration(self._html_search_meta(
            'duration', webpage, 'duration'))

        video_url = 'http://www.historicfilms.com/video/%s_%s_web.mov' % (tape_id, video_id)

        return {
            'id': video_id,
            'url': video_url,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
        }
