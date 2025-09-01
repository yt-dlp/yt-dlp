import json
import re

from .common import InfoExtractor
from ..utils import ExtractorError, url_or_none
from ..utils.traversal import traverse_obj


class IzRuIE(InfoExtractor):
    IE_NAME = 'iz.ru'
    _VALID_URL = r'(?P<urlstart>https?://(?:www\.)?iz\.ru)/(?P<id>[0-9]+)/(?P<date>[0-9-]+)/(?P<slug>[^/?#]+)'
    _TESTS = [
        {
            'url': 'https://iz.ru/1946734/2025-09-01/liubimova-nazvala-film-krasnyi-shelk-svidetelstvom-tesnykh-sviazei-rf-i-kitaia',
            'info_dict': {
                'id': '1946734',
                'title': 'Любимова назвала фильм «Красный шелк» свидетельством тесных связей РФ и Китая',
                'ext': 'mp4',
                'thumbnail': r're:https://cdn\.iz\.ru/.+\.(?:jpg|png)',
            },
        }
    ]

    def _extract_script_data(self, webpage, pattern):
        # We are looking for <script> tags with specific content
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', webpage, re.DOTALL)

        for script in scripts:
            match = re.search(pattern, script, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    return match.group(1)
        return None

    def _real_extract(self, url):
        video_id = self._match_id(url)
        urlstart, date = self._match_valid_url(url).group('urlstart', 'date')
        webpage = self._download_webpage(url, video_id)
        iframe_url = self._search_regex(
            r'<iframe\b[^>]+\bsrc=["\'](/video/embed/[^"\']+)', webpage, 'iframe URL'
        )

        iframe_webpage = self._download_webpage(urlstart + iframe_url, video_id)
        info_json = self._extract_script_data(
            iframe_webpage, r'window\.config\s*=\s*({.*?});'
        )
        if info_json:
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                traverse_obj(info_json, ('sources', -1, 'hls', {url_or_none})),
                video_id,
                'mp4',
                m3u8_id='hls',
            )

            return {
                'id': video_id,
                'title': self._og_search_title(webpage, default=None) or self._html_extract_title(webpage),
                'thumbnail': traverse_obj(info_json, ('image', 'path', {url_or_none})),
                'formats': formats,
                'subtitles': subtitles,
            }
        raise ExtractorError('Can\'t get info_json from player\'s iframe')
