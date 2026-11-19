from .common import InfoExtractor
from ..utils import js_to_json, unified_strdate

class ScreenRecIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?screenrec\.com/share/(?P<id>\w{10})'
    _TESTS = [{
        'url': 'https://screenrec.com/share/ZHwdTfY23O',
        'info_dict': {
            'id': 'ZHwdTfY23O',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.*\.gif',
            'upload_date': '20261117',
            'title': '17.11.2026_12.01.13_REC',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        clip_id = self._search_json(
            r'var\s+vars\s*=',
            webpage,
            'player vars',
            video_id,
            transform_source=js_to_json,
        )['clip_id']

        info_xml = self._download_xml(
            f'https://service.webvideocore.net/?l=info&a=xmlClipPath&page_url={url}&clip_id={clip_id}&version=5&preview=0&timezone_offset=0&init=true',
            video_id,
        ).find('info')

        return {
            'id': video_id,
            'title': self._og_search_title(webpage, default=None) or self._html_extract_title(webpage),
            'description': self._og_search_description(webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
            'formats': self._extract_m3u8_formats(m3u8_url, video_id, ext='mp4'),
        }
