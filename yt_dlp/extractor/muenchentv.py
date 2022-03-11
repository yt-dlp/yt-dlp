# coding: utf-8
from __future__ import unicode_literals

import json

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    js_to_json,
)


class MuenchenTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?muenchen\.tv/livestream'
    IE_DESC = 'münchen.tv'
    _TEST = {
        'url': 'http://www.muenchen.tv/livestream/',
        'info_dict': {
            'id': '5334',
            'display_id': 'live',
            'ext': 'mp4',
            'title': 're:^münchen.tv-Livestream [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'is_live': True,
            'thumbnail': r're:^https?://.*\.jpg$'
        },
        'params': {
            'skip_download': True,
        }
    }

    def _real_extract(self, url):
        display_id = 'live'
        webpage = self._download_webpage(url, display_id)

        title = self._og_search_title(webpage)

        data_js = self._search_regex(
            r'(?s)\nplaylist:\s*(\[.*?}\]),',
            webpage, 'playlist configuration')
        data_json = js_to_json(data_js)
        data = json.loads(data_json)[0]

        video_id = data['mediaid']
        thumbnail = data.get('image')

        formats = []
        for format_num, s in enumerate(data['sources']):
            ext = determine_ext(s['file'], None)
            label_str = s.get('label')
            if label_str is None:
                label_str = '_%d' % format_num

            if ext is None:
                format_id = label_str
            else:
                format_id = '%s-%s' % (ext, label_str)

            formats.append({
                'url': s['file'],
                'tbr': int_or_none(s.get('label')),
                'ext': 'mp4',
                'format_id': format_id,
                'preference': -100 if '.smil' in s['file'] else 0,  # Strictly inferior than all other formats?
            })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'formats': formats,
            'is_live': True,
            'thumbnail': thumbnail,
        }
