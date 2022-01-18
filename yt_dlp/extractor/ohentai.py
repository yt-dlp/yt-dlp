# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    js_to_json,
    get_elements_by_class,
    determine_ext,
    try_get,
)


class OhentaiIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ohentai\.org/detail.php\?vid=(?P<id>[=a-zA-Z0-9]+)'
    _TESTS = [{
        'url': 'https://ohentai.org/detail.php?vid=MTA3OA==',
        'info_dict': {
            'id': 'MTA3OA==',
            'ext': 'mp4',
            'title': 'Ochiru Hitozuma',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        title = get_elements_by_class('title', webpage)[0]
        title = title.replace('\t', '').replace('\n', '').strip()

        video_params = self._parse_json(
            self._search_regex(
                r'SendPlay.setup\(({[\S\s]+})\);\s<\/script>',
                webpage, 'video parameters'),
            video_id, transform_source=js_to_json)

        formats = []
        for format_id, format_data in enumerate(video_params['sources']):
            url = format_data['file']
            formats.append({
                'format_id': str(format_id),
                'url': url,
                'ext': determine_ext(url),
            })
        self._sort_formats(formats)

        thumbnail = try_get(video_params,
                            lambda vi: 'https://ohentai.org/' + video_params['image'])

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': thumbnail,
            'age_limit': 18,
        }
