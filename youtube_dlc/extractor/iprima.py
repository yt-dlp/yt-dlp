# coding: utf-8
from __future__ import unicode_literals

import re
import time

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    js_to_json,
)


class IPrimaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[^/]+)\.iprima\.cz/(?:[^/]+/)*(?P<id>[^/?#&]+)'
    _GEO_BYPASS = False

    _TESTS = [{
        'url': 'https://prima.iprima.cz/particka/92-epizoda',
        'info_dict': {
            'id': 'p51388',
            'ext': 'mp4',
            'title': 'Partička (92)',
            'description': 'md5:859d53beae4609e6dd7796413f1b6cac',
        },
        'params': {
            'skip_download': True,  # m3u8 download
        },
    }, {
        'url': 'https://cnn.iprima.cz/videa/70-epizoda',
        'info_dict': {
            'id': 'p681554',
            'ext': 'mp4',
            'title': 'HLAVNÍ ZPRÁVY 3.5.2020',
        },
        'params': {
            'skip_download': True,  # m3u8 download
        },
    }, {
        'url': 'http://play.iprima.cz/particka/particka-92',
        'only_matching': True,
    }, {
        # geo restricted
        'url': 'http://play.iprima.cz/closer-nove-pripady/closer-nove-pripady-iv-1',
        'only_matching': True,
    }, {
        # iframe api.play-backend.iprima.cz
        'url': 'https://prima.iprima.cz/my-little-pony/mapa-znameni-2-2',
        'only_matching': True,
    }, {
        # iframe prima.iprima.cz
        'url': 'https://prima.iprima.cz/porady/jak-se-stavi-sen/rodina-rathousova-praha',
        'only_matching': True,
    }, {
        'url': 'http://www.iprima.cz/filmy/desne-rande',
        'only_matching': True,
    }, {
        'url': 'https://zoom.iprima.cz/10-nejvetsich-tajemstvi-zahad/posvatna-mista-a-stavby',
        'only_matching': True,
    }, {
        'url': 'https://krimi.iprima.cz/mraz-0/sebevrazdy',
        'only_matching': True,
    }, {
        'url': 'https://cool.iprima.cz/derava-silnice-nevadi',
        'only_matching': True,
    }, {
        'url': 'https://love.iprima.cz/laska-az-za-hrob/slib-dany-bratrovi',
        'only_matching': True,
    }, {
        'url': 'https://autosalon.iprima.cz/motorsport/7-epizoda-1',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        self._set_cookie('play.iprima.cz', 'ott_adult_confirmed', '1')

        webpage = self._download_webpage(url, video_id)

        title = self._og_search_title(
            webpage, default=None) or self._search_regex(
            r'<h1>([^<]+)', webpage, 'title')

        video_id = self._search_regex(
            (r'<iframe[^>]+\bsrc=["\'](?:https?:)?//(?:api\.play-backend\.iprima\.cz/prehravac/embedded|prima\.iprima\.cz/[^/]+/[^/]+)\?.*?\bid=(p\d+)',
             r'data-product="([^"]+)">',
             r'id=["\']player-(p\d+)"',
             r'playerId\s*:\s*["\']player-(p\d+)',
             r'\bvideos\s*=\s*["\'](p\d+)'),
            webpage, 'real id')

        playerpage = self._download_webpage(
            'http://play.iprima.cz/prehravac/init',
            video_id, note='Downloading player', query={
                '_infuse': 1,
                '_ts': round(time.time()),
                'productId': video_id,
            }, headers={'Referer': url})

        formats = []

        def extract_formats(format_url, format_key=None, lang=None):
            ext = determine_ext(format_url)
            new_formats = []
            if format_key == 'hls' or ext == 'm3u8':
                new_formats = self._extract_m3u8_formats(
                    format_url, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False)
            elif format_key == 'dash' or ext == 'mpd':
                return
                new_formats = self._extract_mpd_formats(
                    format_url, video_id, mpd_id='dash', fatal=False)
            if lang:
                for f in new_formats:
                    if not f.get('language'):
                        f['language'] = lang
            formats.extend(new_formats)

        options = self._parse_json(
            self._search_regex(
                r'(?s)(?:TDIPlayerOptions|playerOptions)\s*=\s*({.+?});\s*\]\]',
                playerpage, 'player options', default='{}'),
            video_id, transform_source=js_to_json, fatal=False)
        if options:
            for key, tracks in options.get('tracks', {}).items():
                if not isinstance(tracks, list):
                    continue
                for track in tracks:
                    src = track.get('src')
                    if src:
                        extract_formats(src, key.lower(), track.get('lang'))

        if not formats:
            for _, src in re.findall(r'src["\']\s*:\s*(["\'])(.+?)\1', playerpage):
                extract_formats(src)

        if not formats and '>GEO_IP_NOT_ALLOWED<' in playerpage:
            self.raise_geo_restricted(countries=['CZ'])

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'formats': formats,
            'description': self._og_search_description(webpage, default=None),
        }
