# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    int_or_none,
    js_to_json,
    strip_or_none,
    try_get,
    unescapeHTML,
    unified_timestamp,
)


class WatchBoxIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?watchbox\.de/(?P<kind>serien|filme)/(?:[^/]+/)*[^/]+-(?P<id>\d+)'
    _TESTS = [{
        # film
        'url': 'https://www.watchbox.de/filme/free-jimmy-12325.html',
        'info_dict': {
            'id': '341368',
            'ext': 'mp4',
            'title': 'Free Jimmy',
            'description': 'md5:bcd8bafbbf9dc0ef98063d344d7cc5f6',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 4890,
            'age_limit': 16,
            'release_year': 2009,
        },
        'params': {
            'format': 'bestvideo',
            'skip_download': True,
        },
        'expected_warnings': ['Failed to download m3u8 information'],
    }, {
        # episode
        'url': 'https://www.watchbox.de/serien/ugly-americans-12231/staffel-1/date-in-der-hoelle-328286.html',
        'info_dict': {
            'id': '328286',
            'ext': 'mp4',
            'title': 'S01 E01 - Date in der Hölle',
            'description': 'md5:2f31c74a8186899f33cb5114491dae2b',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 1291,
            'age_limit': 12,
            'release_year': 2010,
            'series': 'Ugly Americans',
            'season_number': 1,
            'episode': 'Date in der Hölle',
            'episode_number': 1,
        },
        'params': {
            'format': 'bestvideo',
            'skip_download': True,
        },
        'expected_warnings': ['Failed to download m3u8 information'],
    }, {
        'url': 'https://www.watchbox.de/serien/ugly-americans-12231/staffel-2/der-ring-des-powers-328270',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        kind, video_id = mobj.group('kind', 'id')

        webpage = self._download_webpage(url, video_id)

        player_config = self._parse_json(
            self._search_regex(
                r'data-player-conf=(["\'])(?P<data>{.+?})\1', webpage,
                'player config', default='{}', group='data'),
            video_id, transform_source=unescapeHTML, fatal=False)

        if not player_config:
            player_config = self._parse_json(
                self._search_regex(
                    r'playerConf\s*=\s*({.+?})\s*;', webpage, 'player config',
                    default='{}'),
                video_id, transform_source=js_to_json, fatal=False) or {}

        source = player_config.get('source') or {}

        video_id = compat_str(source.get('videoId') or video_id)

        devapi = self._download_json(
            'http://api.watchbox.de/devapi/id/%s' % video_id, video_id, query={
                'format': 'json',
                'apikey': 'hbbtv',
            }, fatal=False)

        item = try_get(devapi, lambda x: x['items'][0], dict) or {}

        title = item.get('title') or try_get(
            item, lambda x: x['movie']['headline_movie'],
            compat_str) or source['title']

        formats = []
        hls_url = item.get('media_videourl_hls') or source.get('hls')
        if hls_url:
            formats.extend(self._extract_m3u8_formats(
                hls_url, video_id, 'mp4', entry_protocol='m3u8_native',
                m3u8_id='hls', fatal=False))
        dash_url = item.get('media_videourl_wv') or source.get('dash')
        if dash_url:
            formats.extend(self._extract_mpd_formats(
                dash_url, video_id, mpd_id='dash', fatal=False))
        mp4_url = item.get('media_videourl')
        if mp4_url:
            formats.append({
                'url': mp4_url,
                'format_id': 'mp4',
                'width': int_or_none(item.get('width')),
                'height': int_or_none(item.get('height')),
                'tbr': int_or_none(item.get('bitrate')),
            })
        self._sort_formats(formats)

        description = strip_or_none(item.get('descr'))
        thumbnail = item.get('media_content_thumbnail_large') or source.get('poster') or item.get('media_thumbnail')
        duration = int_or_none(item.get('media_length') or source.get('length'))
        timestamp = unified_timestamp(item.get('pubDate'))
        view_count = int_or_none(item.get('media_views'))
        age_limit = int_or_none(try_get(item, lambda x: x['movie']['fsk']))
        release_year = int_or_none(try_get(item, lambda x: x['movie']['rel_year']))

        info = {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'timestamp': timestamp,
            'view_count': view_count,
            'age_limit': age_limit,
            'release_year': release_year,
            'formats': formats,
        }

        if kind.lower() == 'serien':
            series = try_get(
                item, lambda x: x['special']['title'],
                compat_str) or source.get('format')
            season_number = int_or_none(self._search_regex(
                r'^S(\d{1,2})\s*E\d{1,2}', title, 'season number',
                default=None) or self._search_regex(
                    r'/staffel-(\d+)/', url, 'season number', default=None))
            episode = source.get('title')
            episode_number = int_or_none(self._search_regex(
                r'^S\d{1,2}\s*E(\d{1,2})', title, 'episode number',
                default=None))
            info.update({
                'series': series,
                'season_number': season_number,
                'episode': episode,
                'episode_number': episode_number,
            })

        return info
