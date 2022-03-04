# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import compat_b64decode
from ..utils import (
    get_elements_by_class,
    int_or_none,
    js_to_json,
    parse_count,
    parse_duration,
    try_get,
)


class DaftsexIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?daftsex\.com/watch/(?P<id>-?\d+_\d+)'
    _TESTS = [{
        'url': 'https://daftsex.com/watch/-156601359_456242791',
        'info_dict': {
            'id': '-156601359_456242791',
            'ext': 'mp4',
            'title': 'Skye Blue - Dinner And A Show',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        title = get_elements_by_class('heading', webpage)[-1]
        duration = parse_duration(self._search_regex(
            r'Duration: ((?:[0-9]{2}:){0,2}[0-9]{2})',
            webpage, 'duration', fatal=False))
        views = parse_count(self._search_regex(
            r'Views: ([0-9 ]+)',
            webpage, 'views', fatal=False))

        player_hash = self._search_regex(
            r'DaxabPlayer\.Init\({[\s\S]*hash:\s*"([0-9a-zA-Z_\-]+)"[\s\S]*}',
            webpage, 'player hash')
        player_color = self._search_regex(
            r'DaxabPlayer\.Init\({[\s\S]*color:\s*"([0-9a-z]+)"[\s\S]*}',
            webpage, 'player color', fatal=False) or ''

        embed_page = self._download_webpage(
            'https://daxab.com/player/%s?color=%s' % (player_hash, player_color),
            video_id, headers={'Referer': url})
        video_params = self._parse_json(
            self._search_regex(
                r'window\.globParams\s*=\s*({[\S\s]+})\s*;\s*<\/script>',
                embed_page, 'video parameters'),
            video_id, transform_source=js_to_json)

        server_domain = 'https://%s' % compat_b64decode(video_params['server'][::-1]).decode('utf-8')
        formats = []
        for format_id, format_data in video_params['video']['cdn_files'].items():
            ext, height = format_id.split('_')
            extra_quality_data = format_data.split('.')[-1]
            url = f'{server_domain}/videos/{video_id.replace("_", "/")}/{height}.mp4?extra={extra_quality_data}'
            formats.append({
                'format_id': format_id,
                'url': url,
                'height': int_or_none(height),
                'ext': ext,
            })
        self._sort_formats(formats)

        thumbnail = try_get(video_params,
                            lambda vi: 'https:' + compat_b64decode(vi['video']['thumb']).decode('utf-8'))

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'duration': duration,
            'thumbnail': thumbnail,
            'view_count': views,
            'age_limit': 18,
        }
