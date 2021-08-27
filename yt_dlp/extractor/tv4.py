# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_iso8601,
)


class TV4IE(InfoExtractor):
    IE_DESC = 'tv4.se and tv4play.se'
    _VALID_URL = r'''(?x)https?://(?:www\.)?
        (?:
            tv4\.se/(?:[^/]+)/klipp/(?:.*)-|
            tv4play\.se/
            (?:
                (?:program|barn)/(?:(?:[^/]+/){1,2}|(?:[^\?]+)\?video_id=)|
                iframe/video/|
                film/|
                sport/|
            )
        )(?P<id>[0-9]+)'''
    _GEO_COUNTRIES = ['SE']
    _TESTS = [
        {
            'url': 'http://www.tv4.se/kalla-fakta/klipp/kalla-fakta-5-english-subtitles-2491650',
            'md5': 'cb837212f342d77cec06e6dad190e96d',
            'info_dict': {
                'id': '2491650',
                'ext': 'mp4',
                'title': 'Kalla Fakta 5 (english subtitles)',
                'thumbnail': r're:^https?://.*\.jpg$',
                'timestamp': int,
                'upload_date': '20131125',
            },
        },
        {
            'url': 'http://www.tv4play.se/iframe/video/3054113',
            'md5': 'cb837212f342d77cec06e6dad190e96d',
            'info_dict': {
                'id': '3054113',
                'ext': 'mp4',
                'title': 'Så här jobbar ficktjuvarna - se avslöjande bilder',
                'thumbnail': r're:^https?://.*\.jpg$',
                'description': 'Unika bilder avslöjar hur turisternas fickor vittjas mitt på Stockholms central. Två experter på ficktjuvarna avslöjar knepen du ska se upp för.',
                'timestamp': int,
                'upload_date': '20150130',
            },
        },
        {
            'url': 'http://www.tv4play.se/sport/3060959',
            'only_matching': True,
        },
        {
            'url': 'http://www.tv4play.se/film/2378136',
            'only_matching': True,
        },
        {
            'url': 'http://www.tv4play.se/barn/looney-tunes?video_id=3062412',
            'only_matching': True,
        },
        {
            'url': 'http://www.tv4play.se/program/farang/3922081',
            'only_matching': True,
        },
        {
            'url': 'https://www.tv4play.se/program/nyheterna/avsnitt/13315940',
            'only_matching': True,
        }
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        info = self._download_json(
            'https://playback-api.b17g.net/asset/%s' % video_id,
            video_id, 'Downloading video info JSON', query={
                'service': 'tv4',
                'device': 'browser',
                'protocol': 'hls,dash',
                'drm': 'widevine',
            })['metadata']

        title = info['title']

        manifest_url = self._download_json(
            'https://playback-api.b17g.net/media/' + video_id,
            video_id, query={
                'service': 'tv4',
                'device': 'browser',
                'protocol': 'hls',
            })['playbackItem']['manifestUrl']
        formats = []
        subtitles = {}

        fmts, subs = self._extract_m3u8_formats_and_subtitles(
            manifest_url, video_id, 'mp4',
            'm3u8_native', m3u8_id='hls', fatal=False)
        formats.extend(fmts)
        subtitles = self._merge_subtitles(subtitles, subs)

        fmts, subs = self._extract_mpd_formats_and_subtitles(
            manifest_url.replace('.m3u8', '.mpd'),
            video_id, mpd_id='dash', fatal=False)
        formats.extend(fmts)
        subtitles = self._merge_subtitles(subtitles, subs)

        fmts = self._extract_f4m_formats(
            manifest_url.replace('.m3u8', '.f4m'),
            video_id, f4m_id='hds', fatal=False)
        formats.extend(fmts)

        fmts, subs = self._extract_ism_formats_and_subtitles(
            re.sub(r'\.ism/.*?\.m3u8', r'.ism/Manifest', manifest_url),
            video_id, ism_id='mss', fatal=False)
        formats.extend(fmts)
        subtitles = self._merge_subtitles(subtitles, subs)

        if not formats and info.get('is_geo_restricted'):
            self.raise_geo_restricted(countries=self._GEO_COUNTRIES, metadata_available=True)

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'subtitles': subtitles,
            'description': info.get('description'),
            'timestamp': parse_iso8601(info.get('broadcast_date_time')),
            'duration': int_or_none(info.get('duration')),
            'thumbnail': info.get('image'),
            'is_live': info.get('isLive') is True,
            'series': info.get('seriesTitle'),
            'season_number': int_or_none(info.get('seasonNumber')),
            'episode': info.get('episodeTitle'),
            'episode_number': int_or_none(info.get('episodeNumber')),
        }
