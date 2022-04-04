# coding: utf-8
from __future__ import unicode_literals

from .dailymotion import DailymotionIE
from .common import InfoExtractor
from ..utils import (
    parse_iso8601,
    unescapeHTML,
)

import re


class MoviepilotIE(InfoExtractor):
    _IE_NAME = 'moviepilot'
    _IE_DESC = 'Moviepilot trailer'
    _VALID_URL = r'https?://(?:www\.)?moviepilot\.de/movies/(?P<id>[^/]+)'

    _TESTS = [{
        'url': 'https://www.moviepilot.de/movies/interstellar-2/',
        'info_dict': {
            'id': 'x7xdut5',
            'display_id': 'interstellar-2',
            'ext': 'mp4',
            'title': 'Interstellar',
            'thumbnail': 'https://s1.dmcdn.net/v/SaXev1VvzitVZMFsR/x720',
            'timestamp': 1400491705,
            'description': 'md5:7dfc5c1758e7322a7346934f1f0c489c',
            'uploader': 'Moviepilot',
            'like_count': int,
            'view_count': int,
            'uploader_id': 'x6nd9k',
            'upload_date': '20140519',
            'duration': 140,
            'age_limit': 0,
            'tags': ['Alle Trailer', 'Movie', 'Third Party'],
        },
    }, {
        'url': 'https://www.moviepilot.de/movies/interstellar-2/trailer',
        'only_matching': True,
    }, {
        'url': 'https://www.moviepilot.de/movies/interstellar-2/kinoprogramm/berlin',
        'only_matching': True,
    }, {
        'url': 'https://www.moviepilot.de/movies/queen-slim/trailer',
        'info_dict': {
            'id': 'x7xj6o7',
            'display_id': 'queen-slim',
            'title': 'Queen & Slim',
            'ext': 'mp4',
            'thumbnail': 'https://s2.dmcdn.net/v/SbUM71WtomSjVmI_q/x720',
            'timestamp': 1571838685,
            'description': 'md5:73058bcd030aa12d991e4280d65fbebe',
            'uploader': 'Moviepilot',
            'like_count': int,
            'view_count': int,
            'uploader_id': 'x6nd9k',
            'upload_date': '20191023',
            'duration': 138,
            'age_limit': 0,
            'tags': ['Movie', 'Verleih', 'Neue Trailer'],
        },
    }, {
        'url': 'https://www.moviepilot.de/movies/der-geiger-von-florenz/trailer',
        'info_dict': {
            'id': 'der-geiger-von-florenz',
            'title': 'Der Geiger von Florenz',
            'ext': 'mp4',
        },
        'skip': 'No trailer for this movie.',
    }, {
        'url': 'https://www.moviepilot.de/movies/muellers-buero/',
        'info_dict': {
            'id': 'x7xcw1i',
            'display_id': 'muellers-buero',
            'title': 'Müllers Büro',
            'ext': 'mp4',
            'description': 'md5:57501251c05cdc61ca314b7633e0312e',
            'timestamp': 1287584475,
            'age_limit': 0,
            'duration': 82,
            'upload_date': '20101020',
            'thumbnail': 'https://s1.dmcdn.net/v/SaMes1WfAm1d6maq_/x720',
            'uploader': 'Moviepilot',
            'like_count': int,
            'view_count': int,
            'tags': ['Alle Trailer', 'Movie', 'Verleih'],
            'uploader_id': 'x6nd9k',
        },
    }]

    def _get_property(self, name, webpage, fatal=True):
        return self._search_regex(f'meta itemprop="{name}" content="(.*?)"', webpage, name, fatal=fatal)

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(f'https://www.moviepilot.de/movies/{video_id}/trailer', video_id)

        # oriented on parse_duration()
        d = re.match(r'P(?P<hours>[0-9]+)H(?P<mins>[0-9]{2})M(?P<secs>[0-9]{2})S',
                     self._get_property("duration", webpage, fatal=False))
        if d:
            hours, mins, secs = d.groups()
            duration = float(hours) * 60 * 60 + float(mins) * 60 + float(secs)
        else:
            duration = None

        return {
            '_type': 'url_transparent',
            'ie_key': DailymotionIE.ie_key(),
            'display_id': video_id,
            'title': self._og_search_title(webpage),
            'url': self._get_property('embedURL', webpage),
            'thumbnail': self._get_property('thumbnailURL', webpage, fatal=False),
            'description': unescapeHTML(self._get_property('description', webpage, fatal=False)),
            'duration': duration,
            'timestamp': parse_iso8601(self._get_property('uploadDate', webpage, fatal=False), delimiter=' ')
        }
