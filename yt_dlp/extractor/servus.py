# coding: utf-8
from __future__ import unicode_literals

import time

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    ExtractorError,
    int_or_none,
    url_or_none,
)


class ServusIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.)?
                        (?:
                            servus\.com/(?:(?:at|de)/p/[^/]+|tv/videos)|
                            (?:servustv|pm-wissen)\.com/(?:videos|[^/]+/v)
                        )
                        /(?P<id>[aA]{2}-\w+|\d+-\d+)
                    '''
    _TESTS = [{
        # new URL schema
        'url': 'https://www.servustv.com/unterhaltung/v/aa-1w4q6mek11w12/',
        'md5': '3e2e439b02a3672b19f62ca9ca9a8b19',
        'info_dict': {
            'id': 'AA-1W4Q6MEK11W12',
            'ext': 'mp4',
            'title': 'Von Lüttichau ganz privat',
            'description': 'md5:127992801b14b032576597bb25555115',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 357,
            'series': 'Hubert und Staller',
            'season': 'Season 7',
            'episode': 'Episode 1 - Der Räucherschorsch dreht durch',
        }
    }, {
        # old URL schema
        'url': 'https://www.servustv.com/videos/aa-1t6vbu5pw1w12/',
        'only_matching': True,
    }, {
        # old URL schema
        'url': 'https://www.servus.com/de/p/Die-Gr%C3%BCnen-aus-Sicht-des-Volkes/AA-1T6VBU5PW1W12/',
        'only_matching': True,
    }, {
        'url': 'https://www.servus.com/at/p/Wie-das-Leben-beginnt/1309984137314-381415152/',
        'only_matching': True,
    }, {
        'url': 'https://www.servus.com/tv/videos/aa-1t6vbu5pw1w12/',
        'only_matching': True,
    }, {
        'url': 'https://www.servus.com/tv/videos/1380889096408-1235196658/',
        'only_matching': True,
    }, {
        'url': 'https://www.pm-wissen.com/videos/aa-24mus4g2w2112/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url).upper()

        # TODO: timezone should be IANA tz database name (`Intl.DateTimeFormat().resolvedOptions().timeZone` with JavaScript)
        # but api server only seems to check the format with regex `^([A-Z][A-Za-z]+)(\/.+)?$` for now
        timezone = 'Etc/GMT%+d' % int(time.timezone / 3600)
        attrs = self._download_json(
            'https://api-player.redbull.com/stv/servus-tv?videoId=%s&timeZone=%s' % (video_id, timezone),
            video_id, 'Downloading video JSON')

        if 'GEO_BLOCKED' in attrs.get('playabilityErrors', ''):
            countries = ', '.join(attrs.get('blockedCountries', ['Unknown']))
            raise ExtractorError(
                'Video is geo restricted (restricted countries: %s). '
                'Try bypassing with --geo-bypass-country option, VPN or --proxy option' % countries, expected=True)

        formats = []
        format_url = url_or_none(attrs.get('videoUrl'))
        if format_url:
            ext = determine_ext(format_url)
            if ext == 'mpd':
                formats.extend(self._extract_mpd_formats(
                    format_url, video_id, mpd_id='dash', fatal=False))
            elif ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    format_url, video_id, 'mp4', m3u8_id='hls', fatal=False))
            elif ext == 'mp4':
                formats.append({
                    'url': format_url,
                })
        self._sort_formats(formats)

        title = attrs.get('title') or video_id
        description = attrs.get('description')
        series = attrs.get('label')
        season = attrs.get('season')
        episode = attrs.get('chapter')
        duration = int_or_none(attrs.get('duration'))
        thumbnail = url_or_none(attrs.get('poster'))

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'series': series,
            'season': season,
            'episode': episode,
            'formats': formats,
        }
