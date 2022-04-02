# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_duration,
    parse_iso8601,
    unescapeHTML,
)


class MoviepilotIE(InfoExtractor):
    _IE_NAME = "moviepilot"
    _IE_DESC = "Moviepilot trailer"
    _VALID_URL = r'https?://(?:www\.)?moviepilot\.de/movies/(?P<id>[^/]+)/?.*'

    _TESTS = [{
        'url': 'https://www.moviepilot.de/movies/interstellar-2/',
        'info_dict': {
            # 'id': 'interstellar-2',
            'id': 'x7xdut5',
            'ext': 'mp4',
            'title': 'Interstellar',
            'thumbnail': 'https://s1.dmcdn.net/v/SaXev1VvzitVZMFsR/x720',
            'timestamp': 1400491705,
            'description': 'md5:7dfc5c1758e7322a7346934f1f0c489c',
            # coming from Dailymotion
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
        'url': 'https://www.moviepilot.de/movies/interstellar-2',
        'only_matching': True,
    }, {
        'url': 'https://www.moviepilot.de/movies/interstellar-2/kinoprogramm/berlin',
        'only_matching': True,
    }, {
        'url': 'https://www.moviepilot.de/movies/queen-slim/trailer',
        'info_dict': {
            'id': 'x7xj6o7',
            # 'id': 'queen-slim',
            'title': 'Queen & Slim',  # test escaping
            'ext': 'mp4',
            'thumbnail': 'https://s2.dmcdn.net/v/SbUM71WtomSjVmI_q/x720',
            'timestamp': 1571838685,
            'description': 'md5:73058bcd030aa12d991e4280d65fbebe',
            # coming from Dailymotion
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
            # 'id': 'muellers-buero',
            'title': 'Müllers Büro',  # test umlauts
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

        # normalize url
        url = f"https://www.moviepilot.de/movies/{video_id}/trailer"

        webpage = self._download_webpage(url, video_id)

        return {'_type': 'url_transparent',
                'ie_key': 'Dailymotion',
                'id': video_id,
                # Currently, the movie title is extracted, e.g. "Interstellar" or "Müllers Büro"
                # The actual trailer title is: "Interstellar - Trailer 2 (Deutsch) HD" or
                # "MÃ¼llers BÃ¼ro - Trailer (Deutsch)", umlauts are really broken here.
                # I prefer to keep the actual movie title or is there an extra metadata field for that?
                'title': self._og_search_title(webpage),
                'url': self._get_property("embedURL", webpage),
                'thumbnail': self._get_property("thumbnailURL", webpage, fatal=False),
                # The duration is something like "P00H02M20S" but parse_duration cannot parse this
                # should I write an extra function for that or should parse_duration be able to parse this?
                # 'duration': parse_duration(self._get_property("duration", webpage, fatal=False))
                'description': unescapeHTML(self._get_property('description', webpage, fatal=False)),
                'timestamp': parse_iso8601(self._get_property('uploadDate', webpage, fatal=False),
                                           delimiter=" "),
                'height': int_or_none(self._get_property('height', webpage, fatal=False)),
                'width': int_or_none(self._get_property('width', webpage, fatal=False))}
