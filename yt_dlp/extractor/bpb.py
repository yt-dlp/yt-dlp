# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    js_to_json,
    determine_ext,
)


class BpbIE(InfoExtractor):
    IE_DESC = 'Bundeszentrale für politische Bildung'
    _VALID_URL = r'https?://(?:www\.)?bpb\.de/mediathek/(?P<id>[0-9]+)/'

    _TEST = {
        'url': 'http://www.bpb.de/mediathek/297/joachim-gauck-zu-1989-und-die-erinnerung-an-die-ddr',
        # md5 fails in Python 2.6 due to buggy server response and wrong handling of urllib2
        'md5': 'c4f84c8a8044ca9ff68bb8441d300b3f',
        'info_dict': {
            'id': '297',
            'ext': 'mp4',
            'title': 'Joachim Gauck zu 1989 und die Erinnerung an die DDR',
            'description': 'Joachim Gauck, erster Beauftragter für die Stasi-Unterlagen, spricht auf dem Geschichtsforum über die friedliche Revolution 1989 und eine "gewisse Traurigkeit" im Umgang mit der DDR-Vergangenheit.'
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._html_search_regex(
            r'<h2 class="white">(.*?)</h2>', webpage, 'title')
        video_info_dicts = re.findall(
            r"({\s*src\s*:\s*'https?://film\.bpb\.de/[^}]+})", webpage)

        formats = []
        for video_info in video_info_dicts:
            video_info = self._parse_json(
                video_info, video_id, transform_source=js_to_json, fatal=False)
            if not video_info:
                continue
            video_url = video_info.get('src')
            if not video_url:
                continue
            quality = 'high' if '_high' in video_url else 'low'
            formats.append({
                'url': video_url,
                'quality': 10 if quality == 'high' else 0,
                'format_note': quality,
                'format_id': '%s-%s' % (quality, determine_ext(video_url)),
            })

        self._sort_formats(formats)

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'description': self._og_search_description(webpage),
        }
