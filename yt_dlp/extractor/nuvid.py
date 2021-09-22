# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    parse_duration,
    int_or_none,
    try_get,
)


class NuvidIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www|m)\.nuvid\.com/video/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.nuvid.com/video/6513023/italian-babe',
        'md5': '772d2f8288f3d3c5c45f7a41761c7844',
        'info_dict': {
            'id': '6513023',
            'ext': 'mp4',
            'title': 'italian babe',
            'duration': 321.0,
            'age_limit': 18,
        }
    }, {
        'url': 'https://m.nuvid.com/video/6523263',
        'info_dict': {
            'id': '6523263',
            'ext': 'mp4',
            'age_limit': 18,
            'title': 'Slut brunette college student anal dorm',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        qualities = {
            'lq': '360p',
            'hq': '720p',
        }

        json_url = f'https://www.nuvid.com/player_config_json/?vid={video_id}&aid=0&domain_id=0&embed=0&check_speed=0'
        video_data = self._download_json(
            json_url, video_id, headers={
                'Accept': 'application/json, text/javascript, */*; q = 0.01',
                'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
            })

        formats = [{
            'url': source,
            'format_id': qualities.get(quality),
            'height': int_or_none(qualities.get(quality)[:-1]),
        } for quality, source in video_data.get('files').items() if source]

        self._check_formats(formats, video_id)
        self._sort_formats(formats)

        title = video_data.get('title')
        thumbnail_base_url = try_get(video_data, lambda x: x['thumbs']['url'])
        thumbnail_extension = try_get(video_data, lambda x: x['thumbs']['extension'])
        thumbnail_id = self._search_regex(
            r'/media/videos/tmb/6523263/preview/(/d+)' + thumbnail_extension, video_data.get('poster', ''), 'thumbnail id', default=19)
        thumbnail = f'{thumbnail_base_url}player/{thumbnail_id}{thumbnail_extension}'
        duration = parse_duration(video_data.get('duration') or video_data.get('duration_format'))

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'thumbnail': thumbnail,
            'duration': duration,
            'age_limit': 18,
        }
