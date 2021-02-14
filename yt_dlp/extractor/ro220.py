from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import compat_urllib_parse_unquote


class Ro220IE(InfoExtractor):
    IE_NAME = '220.ro'
    _VALID_URL = r'(?x)(?:https?://)?(?:www\.)?220\.ro/(?P<category>[^/]+)/(?P<shorttitle>[^/]+)/(?P<id>[^/]+)'
    _TEST = {
        'url': 'http://www.220.ro/sport/Luati-Le-Banii-Sez-4-Ep-1/LYV6doKo7f/',
        'md5': '03af18b73a07b4088753930db7a34add',
        'info_dict': {
            'id': 'LYV6doKo7f',
            'ext': 'mp4',
            'title': 'Luati-le Banii sez 4 ep 1',
            'description': r're:^Iata-ne reveniti dupa o binemeritata vacanta\. +Va astept si pe Facebook cu pareri si comentarii.$',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)
        url = compat_urllib_parse_unquote(self._search_regex(
            r'(?s)clip\s*:\s*{.*?url\s*:\s*\'([^\']+)\'', webpage, 'url'))
        title = self._og_search_title(webpage)
        description = self._og_search_description(webpage)
        thumbnail = self._og_search_thumbnail(webpage)

        formats = [{
            'format_id': 'sd',
            'url': url,
            'ext': 'mp4',
        }]

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
        }
