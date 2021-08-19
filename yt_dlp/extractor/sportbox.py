# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    js_to_json,
    merge_dicts,
)


class SportBoxIE(InfoExtractor):
    _VALID_URL = r'https?://(?:news\.sportbox|matchtv)\.ru/vdl/player(?:/[^/]+/|\?.*?\bn?id=)(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://news.sportbox.ru/vdl/player/ci/211355',
        'info_dict': {
            'id': '109158',
            'ext': 'mp4',
            'title': 'В Новороссийске прошел детский турнир «Поле славы боевой»',
            'description': 'В Новороссийске прошел детский турнир «Поле славы боевой»',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 292,
            'view_count': int,
            'timestamp': 1426237001,
            'upload_date': '20150313',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'http://news.sportbox.ru/vdl/player?nid=370908&only_player=1&autostart=false&playeri=2&height=340&width=580',
        'only_matching': True,
    }, {
        'url': 'https://news.sportbox.ru/vdl/player/media/193095',
        'only_matching': True,
    }, {
        'url': 'https://news.sportbox.ru/vdl/player/media/109158',
        'only_matching': True,
    }, {
        'url': 'https://matchtv.ru/vdl/player/media/109158',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_urls(webpage):
        return re.findall(
            r'<iframe[^>]+src="(https?://(?:news\.sportbox|matchtv)\.ru/vdl/player[^"]+)"',
            webpage)

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        sources = self._parse_json(
            self._search_regex(
                r'(?s)playerOptions\.sources(?:WithRes)?\s*=\s*(\[.+?\])\s*;\s*\n',
                webpage, 'sources'),
            video_id, transform_source=js_to_json)

        formats = []
        for source in sources:
            src = source.get('src')
            if not src:
                continue
            if determine_ext(src) == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    src, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False))
            else:
                formats.append({
                    'url': src,
                })
        self._sort_formats(formats)

        player = self._parse_json(
            self._search_regex(
                r'(?s)playerOptions\s*=\s*({.+?})\s*;\s*\n', webpage,
                'player options', default='{}'),
            video_id, transform_source=js_to_json)
        media_id = player['mediaId']

        info = self._search_json_ld(webpage, media_id, default={})

        view_count = int_or_none(self._search_regex(
            r'Просмотров\s*:\s*(\d+)', webpage, 'view count', default=None))

        return merge_dicts(info, {
            'id': media_id,
            'title': self._og_search_title(webpage, default=None) or media_id,
            'thumbnail': player.get('poster'),
            'duration': int_or_none(player.get('duration')),
            'view_count': view_count,
            'formats': formats,
        })
