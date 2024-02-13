from .common import InfoExtractor
from ..utils import (
    parse_duration,
    unescapeHTML,
)


class MovingImageIE(InfoExtractor):
    _VALID_URL = r'https?://movingimage\.nls\.uk/film/(?P<id>\d+)'
    _TEST = {
        'url': 'http://movingimage.nls.uk/film/3561',
        'md5': '4caa05c2b38453e6f862197571a7be2f',
        'info_dict': {
            'id': '3561',
            'ext': 'mp4',
            'title': 'SHETLAND WOOL',
            'description': 'md5:c5afca6871ad59b4271e7704fe50ab04',
            'duration': 900,
            'thumbnail': r're:^https?://.*\.jpg$',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        formats = self._extract_m3u8_formats(
            self._html_search_regex(r'file\s*:\s*"([^"]+)"', webpage, 'm3u8 manifest URL'),
            video_id, ext='mp4', entry_protocol='m3u8_native')

        def search_field(field_name, fatal=False):
            return self._search_regex(
                r'<span\s+class="field_title">%s:</span>\s*<span\s+class="field_content">([^<]+)</span>' % field_name,
                webpage, 'title', fatal=fatal)

        title = unescapeHTML(search_field('Title', fatal=True)).strip('()[]')
        description = unescapeHTML(search_field('Description'))
        duration = parse_duration(search_field('Running time'))
        thumbnail = self._search_regex(
            r"image\s*:\s*'([^']+)'", webpage, 'thumbnail', fatal=False)

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'description': description,
            'duration': duration,
            'thumbnail': thumbnail,
        }
