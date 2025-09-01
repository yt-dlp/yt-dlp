import json
import re

from .common import InfoExtractor
from ..utils import ExtractorError, unified_strdate, url_or_none, urljoin
from ..utils.traversal import traverse_obj


class IzRuIE(InfoExtractor):
    IE_NAME = 'iz.ru'
    _BASE_URL = 'https://iz.ru'
    _GEO_BYPASS = False
    _GEO_COUNTRIES = ['RU']
    _VALID_URL = r'https?://(?:www\.)?iz\.ru/(?P<id>[0-9]+)(?:/(?:(?P<date>[0-9-]+)|(?:video)))?/(?P<slug>[^/?#]+)'
    _TESTS = [
        {
            'url': 'https://iz.ru/1946734/2025-09-01/liubimova-nazvala-film-krasnyi-shelk-svidetelstvom-tesnykh-sviazei-rf-i-kitaia',
            'info_dict': {
                'id': '1946734',
                'title': 'Любимова назвала фильм «Красный шелк» свидетельством тесных связей РФ и Китая',
                'ext': 'mp4',
                'thumbnail': r're:https://cdn\.iz\.ru/.+\.(?:jpg|png)',
            },
        },
        {
            'url': 'https://iz.ru/1946727/video/liubimova-o-filme-krasnyi-shelk',
            'info_dict': {
                'id': '1946727',
                'title': 'Любимова о фильме "Красный шелк"',
                'ext': 'mp4',
                'thumbnail': r're:https://cdn\.iz\.ru/.+\.(?:jpg|png)',
            },
        },
    ]

    def _extract_script_data(self, webpage, pattern):
        # We are looking for <script> tags with specific content
        scripts = re.findall(r'<script\b[^>]*>(.*?)</script\s*[^>]*>', webpage, re.DOTALL | re.IGNORECASE)

        for script in scripts:
            match = re.search(pattern, script, re.DOTALL | re.IGNORECASE)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    return match.group(1)
        return None

    def _real_extract(self, url):
        video_id = self._match_id(url)
        date = self._match_valid_url(url).group('date')
        try:
            webpage = self._download_webpage(url, video_id)
        except ExtractorError:
            self.raise_geo_restricted(countries=self._GEO_COUNTRIES)
        iframe_url = self._search_regex(
            r'<iframe\b[^>]+\bsrc=["\'](/video/embed/[^"\']+)', webpage, 'iframe URL',
        )

        iframe_webpage = self._download_webpage(urljoin(self._BASE_URL, iframe_url), video_id)
        info_json = self._extract_script_data(
            iframe_webpage, r'window\.config\s*=\s*({.*?});',
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
                'upload_date': unified_strdate(date),
            }
        raise ExtractorError('Can\'t get info_json from player\'s iframe')
