from .common import InfoExtractor
from .dailymotion import DailymotionIE


class MoviepilotIE(InfoExtractor):
    IE_NAME = 'moviepilot'
    IE_DESC = 'Moviepilot trailer'
    _VALID_URL = r'https?://(?:www\.)?moviepilot\.de/movies/(?P<id>[^/]+)'

    _TESTS = [{
        'url': 'https://www.moviepilot.de/movies/interstellar-2/',
        'info_dict': {
            'id': 'x7xdpkk',
            'display_id': 'interstellar-2',
            'ext': 'mp4',
            'title': 'Interstellar',
            'thumbnail': r're:https://\w+\.dmcdn\.net/v/SaV-q1.*/x1080',
            'timestamp': 1605010596,
            'description': 'md5:0ae9cb452af52610c9ffc60f2fd0474c',
            'uploader': 'Moviepilot',
            'like_count': int,
            'view_count': int,
            'uploader_id': 'x6nd9k',
            'upload_date': '20201110',
            'duration': 97,
            'age_limit': 0,
            'tags': ['Alle Trailer', 'Movie', 'Verleih'],
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
            'thumbnail': r're:https://\w+\.dmcdn\.net/v/SbUM71ZeG2N975lf2/x1080',
            'timestamp': 1605555825,
            'description': 'md5:83228bb86f5367dd181447fdc4873989',
            'uploader': 'Moviepilot',
            'like_count': int,
            'view_count': int,
            'uploader_id': 'x6nd9k',
            'upload_date': '20201116',
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
            'description': 'md5:4d23a8f4ca035196cd4523863c4fe5a4',
            'timestamp': 1604958457,
            'age_limit': 0,
            'duration': 82,
            'upload_date': '20201109',
            'thumbnail': r're:https://\w+\.dmcdn\.net/v/SaMes1Z.*/x1080',
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

        clip = self._search_nextjs_data(webpage, video_id)['props']['initialProps']['pageProps']

        return {
            '_type': 'url_transparent',
            'ie_key': DailymotionIE.ie_key(),
            'display_id': video_id,
            'title': clip.get('title'),
            'url': f'https://www.dailymotion.com/video/{clip["video"]["remoteId"]}',
            'description': clip.get('summary'),
        }
