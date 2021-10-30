# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    js_to_json,
    extract_attributes,
    try_get,
    int_or_none,
)


class TagesschauIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tagesschau\.de/(?P<path>[^/]+/(?:[^/]+/)*?(?P<id>[^/#?]+?(?:-?[0-9]+)?))(?:~_?[^/#?]+?)?\.html'

    _TESTS = [{
        'url': 'http://www.tagesschau.de/multimedia/video/video-102143.html',
        'md5': '7a7287612fa881a1ae1d087df45c2fd6',
        'info_dict': {
            'id': 'video-102143-1',
            'ext': 'mp4',
            'title': 'Regierungsumbildung in Athen: Neue Minister in Griechenland vereidigt',
        },
    }, {
        'url': 'http://www.tagesschau.de/multimedia/sendung/ts-5727.html',
        'md5': '3c54c1f6243d279b706bde660ceec633',
        'info_dict': {
            'id': 'ts-5727-1',
            'ext': 'mp4',
            'title': 'Ganze Sendung',
        },
    }, {
        # exclusive audio
        'url': 'http://www.tagesschau.de/multimedia/audio/audio-29417.html',
        'md5': '4cf22023c285f35e99c24d290ba58cc9',
        'info_dict': {
            'id': 'audio-29417-1',
            'ext': 'mp3',
            'title': 'Brasilianischer Präsident Bolsonaro unter Druck: Corona-Bericht wird vorgestellt',
        },
    }, {
        'url': 'http://www.tagesschau.de/inland/bnd-303.html',
        'md5': '12cfb212d9325b5ba0d52b625f1aa61c',
        'info_dict': {
            'id': 'bnd-303-1',
            'ext': 'mp4',
            'title': 'SPD-Gruppenbild mit Bärbel Bas nach der Fraktionssitzung | dpa',
        },
    }, {
        'url': 'http://www.tagesschau.de/inland/afd-parteitag-135.html',
        'info_dict': {
            'id': 'afd-parteitag-135',
            'title': 'AfD',
        },
        'playlist_count': 20,
    }, {
        'url': 'https://www.tagesschau.de/multimedia/audio/audio-29417~player.html',
        'info_dict': {
            'id': 'audio-29417-1',
            'ext': 'mp3',
            'title': 'Brasilianischer Präsident Bolsonaro unter Druck: Corona-Bericht wird vorgestellt',
        },
    }, {
        'url': 'http://www.tagesschau.de/multimedia/sendung/tsg-3771.html',
        'only_matching': True,
    }, {
        'url': 'http://www.tagesschau.de/multimedia/sendung/tt-3827.html',
        'only_matching': True,
    }, {
        'url': 'http://www.tagesschau.de/multimedia/sendung/nm-3475.html',
        'only_matching': True,
    }, {
        'url': 'http://www.tagesschau.de/multimedia/sendung/weltspiegel-3167.html',
        'only_matching': True,
    }, {
        'url': 'http://www.tagesschau.de/multimedia/tsvorzwanzig-959.html',
        'only_matching': True,
    }, {
        'url': 'http://www.tagesschau.de/multimedia/sendung/bab/bab-3299~_bab-sendung-209.html',
        'only_matching': True,
    }, {
        'url': 'http://www.tagesschau.de/multimedia/video/video-102303~_bab-sendung-211.html',
        'only_matching': True,
    }, {
        'url': 'http://www.tagesschau.de/100sekunden/index.html',
        'only_matching': True,
    }, {
        # playlist article with collapsing sections
        'url': 'http://www.tagesschau.de/wirtschaft/faq-freihandelszone-eu-usa-101.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id') or mobj.group('path')
        display_id = video_id.lstrip('-')

        webpage = self._download_webpage(url, display_id)

        title = self._html_search_regex(
            r'<span[^>]*class="headline"[^>]*>(.+?)</span>',
            webpage, 'title', default=None) or self._og_search_title(webpage, fatal=False)

        entries = []
        videos = re.findall(r'<div[^>]+>', webpage)
        num = 0
        for video in videos:
            video = extract_attributes(video).get('data-config')
            if not video:
                continue
            video = self._parse_json(video, video_id, transform_source=js_to_json, fatal=False)
            video_formats = try_get(video, lambda x: x['mc']['_mediaArray'][0]['_mediaStreamArray'])
            if not video_formats:
                continue
            num += 1
            for video_format in video_formats:
                media_url = video_format.get('_stream') or ''
                formats = []
                if media_url.endswith('master.m3u8'):
                    formats = self._extract_m3u8_formats(media_url, video_id, 'mp4', m3u8_id='hls')
                elif media_url.endswith('.hi.mp3') and media_url.startswith('https://download'):
                    formats = [{
                        'url': media_url,
                        'vcodec': 'none',
                    }]
                if not formats:
                    continue
                entries.append({
                    'id': '%s-%d' % (display_id, num),
                    'title': try_get(video, lambda x: x['mc']['_title']),
                    'duration': int_or_none(try_get(video, lambda x: x['mc']['_duration'])),
                    'formats': formats
                })
        if len(entries) > 1:
            return self.playlist_result(entries, display_id, title)
        formats = entries[0]['formats']
        video_info = self._search_json_ld(webpage, video_id)
        description = video_info.get('description')
        thumbnail = self._og_search_thumbnail(webpage) or video_info.get('thumbnail')
        timestamp = video_info.get('timestamp')
        title = title or video_info.get('description')

        self._sort_formats(formats)

        return {
            'id': display_id,
            'title': title,
            'thumbnail': thumbnail,
            'formats': formats,
            'timestamp': timestamp,
            'description': description,
        }
