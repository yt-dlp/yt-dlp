# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    dict_get,
    int_or_none,
    unescapeHTML,
)


class ATVAtIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?atv\.at/(?:[^/]+/){2}(?P<id>[dv]\d+)'
    _TESTS = [{
        'url': 'https://www.atv.at/bauer-sucht-frau-die-zweite-chance/folge-1/d3390693/',
        'md5': 'c471605591009dfb6e6c54f7e62e2807',
        'info_dict': {
            'id': '3390684',
            'ext': 'mp4',
            'title': 'Bauer sucht Frau - Die zweite Chance Folge 1',
        }
    }, {
        'url': 'https://www.atv.at/bauer-sucht-frau-staffel-17/fuenfte-eventfolge/d3339537/',
        'only_matching': True,
    }]

    def _process_source_entry(self, source, part_id):
        source_url = source.get('url')
        if not source_url:
            return
        if determine_ext(source_url) == 'm3u8':
            return self._extract_m3u8_formats(
                source_url, part_id, 'mp4', 'm3u8_native',
                m3u8_id='hls', fatal=False)
        else:
            return [{
                'url': source_url,
            }]

    def _process_entry(self, entry):
        part_id = entry.get('id')
        if not part_id:
            return
        formats = []
        for source in entry.get('sources', []):
            formats.extend(self._process_source_entry(source, part_id) or [])

        self._sort_formats(formats)
        return {
            'id': part_id,
            'title': entry.get('title'),
            'duration': int_or_none(entry.get('duration')),
            'formats': formats
        }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        video_data = self._parse_json(unescapeHTML(self._search_regex(
            r'var\splaylist\s*=\s*(?P<json>\[.*\]);',
            webpage, 'player data', group='json')),
            display_id)

        first_video = video_data[0]
        video_id = first_video['id']
        video_title = dict_get(first_video, ('tvShowTitle', 'title'))

        return {
            '_type': 'multi_video',
            'id': video_id,
            'title': video_title,
            'entries': (self._process_entry(entry) for entry in video_data),
        }
