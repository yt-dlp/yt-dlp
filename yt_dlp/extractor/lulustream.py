import re

from .common import InfoExtractor
from ..utils import (
    PACKED_CODES_RE,
    decode_packed_codes,
    unified_strdate,
)


class LuluVidIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?luluvid\.com/(?:d|e)/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://luluvid.com/d/yzip3nvuot20',
        'info_dict': {
            'id': 'yzip3nvuot20',
            'ext': 'mp4',
            'title': 'Big Buck Bunny',
            'thumbnail': r're:^https?://img\.lulucdn\.com/.*\.jpg$',
            'upload_date': '20260507',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(
            f'https://luluvid.com/e/{video_id}', video_id)

        formats, thumbnail = self._extract_packed_formats(webpage, video_id)

        webpage = self._download_webpage(
            f'https://luluvid.com/d/{video_id}', video_id)

        title = (
            self._html_search_regex(
                r'<h1[^>]*class=(["\'])h5\1[^>]*>(?P<title>[^<]+)',
                webpage, 'title', group='title', default=None)
            or self._og_search_title(webpage))

        upload_date = unified_strdate(self._search_regex(
            r'on\s+(\w+\s+\d+,\s+\d{4})', webpage, 'upload date',
            default=None))

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail or self._og_search_thumbnail(webpage),
            'formats': formats,
            'upload_date': upload_date,
        }

    def _extract_packed_formats(self, webpage, video_id):
        for mobj in re.finditer(PACKED_CODES_RE, webpage):
            try:
                decoded = decode_packed_codes(mobj.group(0))
            except Exception:
                continue
            m3u8_url = self._search_regex(
                r'https?://[^"\' >]+/master\.m3u8[^"\' >]*',
                decoded, 'm3u8 URL', group=0, fatal=False)
            if m3u8_url:
                formats = self._extract_m3u8_formats(
                    m3u8_url, video_id, 'mp4', fatal=False)
                thumbnail = self._search_regex(
                    r'image\s*:\s*(["\'])(?P<thumb>[^"\']+)\1',
                    decoded, 'thumbnail', group='thumb', fatal=False)
                return formats, thumbnail
        return [], None
