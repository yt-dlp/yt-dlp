from .common import InfoExtractor
from ..utils import decode_packed_codes, try_get


class FilemoonIE(InfoExtractor):
    _VALID_URL = r'https?://filemoon\.sx/[e,d]/(?P<id>[^\/$]+)' 
    _SITE_URL = 'https://filemoon.sx'

    def _real_extract(self, url):
        videoid = self._match_id(url)
        _url = f"{self._SITE_URL}/d/{videoid}"
        webpage = try_get(ie._download_webpage(_url, videoid), lambda x: re.sub('[\t\n]', '', x))
        packed = self._search_regex(r'<script data-cfasync=[^>]+>eval\((.+)\)</script>', webpage, 'packed code')
        unpacked = decode_packed_codes(packed)
        m3u8_url = try_get(re.search(r'file:"(?P<url>[^"]+)"', unpacked), lambda x: x.group('url'))        
        formats = self._extract_m3u8_formats(m3u8_url, videoid, ext="mp4", entry_protocol='m3u8_native', m3u8_id="hls"
        title = self._html_extract_title(webpage)
        return {
            'id': videoid,
            'title': title,
            'formats': formats,
            'ext': 'mp4'
        }
