import json
import re

from .common import InfoExtractor
from ..utils import JSON_LD_RE, ExtractorError, url_or_none, urljoin
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
                'title': 'Любимова о фильме "Красный шелк"',
                'description': 'Любимова о фильме "Красный шелк"',
                'duration': 238,
                'ext': 'mp4',
                'thumbnail': r're:https://cdn\.iz\.ru/.+\.(?:jpg|png)',
                'timestamp': 1756737997,
                'view_count': 1254,
            },
        },
        {
            'url': 'https://iz.ru/1946727/video/liubimova-o-filme-krasnyi-shelk',
            'info_dict': {
                'id': '1946727',
                'title': 'Любимова о фильме "Красный шелк"',
                'description': 'Любимова о фильме "Красный шелк"',
                'duration': 238,
                'ext': 'mp4',
                'thumbnail': r're:https://cdn\.iz\.ru/.+\.(?:jpg|png)',
                'timestamp': 1756737997,
                'view_count': 1254,
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
        try:
            webpage = self._download_webpage(url, video_id)
        except ExtractorError:
            self.raise_geo_restricted(countries=self._GEO_COUNTRIES)
        iframe_url = self._search_regex(
            r'<iframe\b[^>]+\bsrc=["\'](/video/embed/[^"\']+)', webpage, 'iframe URL',
        )

        iframe_webpage = self._download_webpage(urljoin(self._BASE_URL, iframe_url), video_id, 'Download player iframe')
        info_json = self._extract_script_data(iframe_webpage, r'window\.config\s*=\s*({.*?});')
        json_ld = self._parse_json(
            self._search_regex(
                JSON_LD_RE, iframe_webpage, 'JSON-LD', '{}', group='json_ld',
            ),
            video_id,
            fatal=False,
        )
        json_ld_info = self._json_ld(json_ld, video_id, fatal=False) or {}
        if not info_json or not json_ld_info:
            raise ExtractorError('Can\'t get info_json or json_ld_info from player\'s iframe')
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            traverse_obj(info_json, ('sources', -1, 'hls', {url_or_none})),
            video_id,
            'mp4',
            m3u8_id='hls',
        )

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **json_ld_info,
        }
