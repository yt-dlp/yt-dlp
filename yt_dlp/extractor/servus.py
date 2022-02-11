# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
)


class ServusIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.)?
                        (?:
                            (?:servustv|pm-wissen)\.com/[^/]+/v
                        )
                        /(?P<id>[a-z0-9-]+)
                    '''
    _TESTS = [
        {
            'url': 'https://www.servustv.com/natur/v/aa-2732ksuwd2111/',
            'md5': 'd6c0fa9d70ccfec3367c101782d83fcf',
            'file_minsize': None,
            'info_dict': {
                'id': 'AA-2732KSUWD2111',
                'ext': 'mp4',
                'title': 'Amerikas Gärten - Der Süden',
                'description': 'Eine Reise zu märchenhaften Gärten!',
                'thumbnail': r're:^https?://.*\.jpg',
                'duration': 2.842,
                'series': 'Monty Don’s America Gardens',
                'season': 'Staffel 1',
                'season_number': 1,
                'episode': 'Episode 2 - Amerikas Gärten - Der Süden',
                'episode_number': 2,
            },
        }, {
            'url': 'https://www.servustv.com/aktuelles/v/aawg5w341t7378lvmwth/',
            'only_matching': True,
        }, {
            'url': 'https://www.pm-wissen.com/umwelt/v/aa-28wxenx9s2111/',
            'only_matching': True,
        }]

    def _real_extract(self, url):
        video_id = self._match_id(url).upper()

        # We need to specify a timezone here in order for the endpoint to work.
        video = self._download_json(
            'https://api-player.redbull.com/stv/servus-tv?videoId=%s&timeZone=%s' % (video_id, 'Europe%2FVienna'),
            video_id,
            'Downloading video JSON'
        )

        formats = self._extract_m3u8_formats(
            video['videoUrl'],
            video_id,
            ext='mp4',
            entry_protocol='m3u8_native',
            m3u8_id='hls',
            fatal=False
        )

        title = video['title']
        description = video['description']
        thumbnail = video['poster']
        series = video['label']
        season = video['season']
        episode = video['chapter']
        duration = float_or_none(video['duration'], scale=1000)
        print(season)
        season_number = int_or_none(self._search_regex(
            r'(?:Season|Staffel) (\d+)', season or '', 'season number', default=None))
        episode_number = int_or_none(self._search_regex(
            r'Episode (\d+)', episode or '', 'episode number', default=None))

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'series': series,
            'season': season,
            'season_number': season_number,
            'episode': episode,
            'episode_number': episode_number,
            'formats': formats,
        }
