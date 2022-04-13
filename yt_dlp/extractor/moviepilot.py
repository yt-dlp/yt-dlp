from .dailymotion import DailymotionIE
from .common import InfoExtractor
from ..utils import (
    parse_iso8601,
    try_get,
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
            'thumbnail': r're:https://\w+\.dmcdn\.net/v/SaXev1VvzitVZMFsR/x720',
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
            'thumbnail': r're:https://\w+\.dmcdn\.net/v/SbUM71WtomSjVmI_q/x720',
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
            'thumbnail': r're:https://\w+\.dmcdn\.net/v/SaMes1WfAm1d6maq_/x720',
            'uploader': 'Moviepilot',
            'like_count': int,
            'view_count': int,
            'tags': ['Alle Trailer', 'Movie', 'Verleih'],
            'uploader_id': 'x6nd9k',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(f'https://www.moviepilot.de/movies/{video_id}/trailer', video_id)

        duration = try_get(
            re.match(r'P(?P<hours>\d+)H(?P<mins>\d+)M(?P<secs>\d+)S',
                     self._html_search_meta('duration', webpage, fatal=False) or ''),
            lambda mobj: sum(float(x) * y for x, y in zip(mobj.groups(), (3600, 60, 1))))
        # _html_search_meta is not used since we don't want name=description to match
        description = self._html_search_regex(
            '<meta[^>]+itemprop="description"[^>]+content="([^>"]+)"', webpage, 'description', fatal=False)

        return {
            '_type': 'url_transparent',
            'ie_key': DailymotionIE.ie_key(),
            'display_id': video_id,
            'title': self._og_search_title(webpage),
            'url': self._html_search_meta('embedURL', webpage),
            'thumbnail': self._html_search_meta('thumbnailURL', webpage),
            'description': description,
            'duration': duration,
            'timestamp': parse_iso8601(self._html_search_meta('uploadDate', webpage), delimiter=' ')
        }
