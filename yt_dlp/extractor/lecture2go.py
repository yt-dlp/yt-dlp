import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    determine_protocol,
    int_or_none,
    parse_duration,
)


class Lecture2GoIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'https?://lecture2go\.uni-hamburg\.de/veranstaltungen/-/v/(?P<id>\d+)'
    _TEST = {
        'url': 'https://lecture2go.uni-hamburg.de/veranstaltungen/-/v/17473',
        'md5': 'ac02b570883020d208d405d5a3fd2f7f',
        'info_dict': {
            'id': '17473',
            'ext': 'mp4',
            'title': '2 - Endliche Automaten und reguläre Sprachen',
            'creator': 'Frank Heitmann',
            'duration': 5220,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._html_search_regex(r'<em[^>]+class="title">(.+)</em>', webpage, 'title')

        formats = []
        for url in set(re.findall(r'var\s+playerUri\d+\s*=\s*"([^"]+)"', webpage)):
            ext = determine_ext(url)
            protocol = determine_protocol({'url': url})
            if ext == 'f4m':
                formats.extend(self._extract_f4m_formats(url, video_id, f4m_id='hds'))
            elif ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(url, video_id, ext='mp4', m3u8_id='hls'))
            else:
                if protocol == 'rtmp':
                    continue  # XXX: currently broken
                formats.append({
                    'format_id': protocol,
                    'url': url,
                })

        creator = self._html_search_regex(
            r'<div[^>]+id="description">([^<]+)</div>', webpage, 'creator', fatal=False)
        duration = parse_duration(self._html_search_regex(
            r'Duration:\s*</em>\s*<em[^>]*>([^<]+)</em>', webpage, 'duration', fatal=False))
        view_count = int_or_none(self._html_search_regex(
            r'Views:\s*</em>\s*<em[^>]+>(\d+)</em>', webpage, 'view count', fatal=False))

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'creator': creator,
            'duration': duration,
            'view_count': view_count,
        }
