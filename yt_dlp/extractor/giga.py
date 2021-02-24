# coding: utf-8
from __future__ import unicode_literals

import itertools

from .common import InfoExtractor
from ..utils import (
    qualities,
    compat_str,
    parse_duration,
    parse_iso8601,
    str_to_int,
)


class GigaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?giga\.de/(?:[^/]+/)*(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'http://www.giga.de/filme/anime-awesome/trailer/anime-awesome-chihiros-reise-ins-zauberland-das-beste-kommt-zum-schluss/',
        'md5': '6bc5535e945e724640664632055a584f',
        'info_dict': {
            'id': '2622086',
            'display_id': 'anime-awesome-chihiros-reise-ins-zauberland-das-beste-kommt-zum-schluss',
            'ext': 'mp4',
            'title': 'Anime Awesome: Chihiros Reise ins Zauberland – Das Beste kommt zum Schluss',
            'description': 'md5:afdf5862241aded4718a30dff6a57baf',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 578,
            'timestamp': 1414749706,
            'upload_date': '20141031',
            'uploader': 'Robin Schweiger',
            'view_count': int,
        },
    }, {
        'url': 'http://www.giga.de/games/channel/giga-top-montag/giga-topmontag-die-besten-serien-2014/',
        'only_matching': True,
    }, {
        'url': 'http://www.giga.de/extra/netzkultur/videos/giga-games-tom-mats-robin-werden-eigene-wege-gehen-eine-ankuendigung/',
        'only_matching': True,
    }, {
        'url': 'http://www.giga.de/tv/jonas-liest-spieletitel-eingedeutscht-episode-2/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        video_id = self._search_regex(
            [r'data-video-id="(\d+)"', r'/api/video/jwplayer/#v=(\d+)'],
            webpage, 'video id')

        playlist = self._download_json(
            'http://www.giga.de/api/syndication/video/video_id/%s/playlist.json?content=syndication/key/368b5f151da4ae05ced7fa296bdff65a/'
            % video_id, video_id)[0]

        quality = qualities(['normal', 'hd720'])

        formats = []
        for format_id in itertools.count(0):
            fmt = playlist.get(compat_str(format_id))
            if not fmt:
                break
            formats.append({
                'url': fmt['src'],
                'format_id': '%s-%s' % (fmt['quality'], fmt['type'].split('/')[-1]),
                'quality': quality(fmt['quality']),
            })
        self._sort_formats(formats)

        title = self._html_search_meta(
            'title', webpage, 'title', fatal=True)
        description = self._html_search_meta(
            'description', webpage, 'description')
        thumbnail = self._og_search_thumbnail(webpage)

        duration = parse_duration(self._search_regex(
            r'(?s)(?:data-video-id="{0}"|data-video="[^"]*/api/video/jwplayer/#v={0}[^"]*")[^>]*>.+?<span class="duration">([^<]+)</span>'.format(video_id),
            webpage, 'duration', fatal=False))

        timestamp = parse_iso8601(self._search_regex(
            r'datetime="([^"]+)"', webpage, 'upload date', fatal=False))
        uploader = self._search_regex(
            r'class="author">([^<]+)</a>', webpage, 'uploader', fatal=False)

        view_count = str_to_int(self._search_regex(
            r'<span class="views"><strong>([\d.,]+)</strong>',
            webpage, 'view count', fatal=False))

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'timestamp': timestamp,
            'uploader': uploader,
            'view_count': view_count,
            'formats': formats,
        }
