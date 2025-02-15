import re

from .common import InfoExtractor
from .youtube import YoutubeIE
from ..utils import extract_attributes


class France24IE(InfoExtractor):

    IE_NAME = 'france24'
    _VALID_URL = (
        # Front-page livestream.
        r'https?://www\.france24\.com(?P<id>/?|/en/?$|/fr/?)$',
        # Articles and shows.
        r'https?://www\.france24\.com/(?:en|fr)/(?:[^/#]+/)+(?P<id>\d{8}-[\w-]+)$',
    )
    _TESTS = [{
        'url': 'https://www.france24.com/fr/émissions/invité-du-jour/20230608-eva-jospin-plasticienne-le-propre-de-la-sculpture-c-est-le-rapport-à-l-espace',
        'info_dict': {
            'age_limit': 0,
            'availability': 'public',
            'categories': ['News & Politics'],
            'channel': 'FRANCE 24',
            'channel_follower_count': int,
            'channel_id': 'UCCCPCZNChQdGa9EkATeye4g',
            'channel_is_verified': True,
            'channel_url': 'https://www.youtube.com/channel/UCCCPCZNChQdGa9EkATeye4g',
            'chapters': [
                {'start_time': 0.0, 'title': 'Introduction', 'end_time': 30.0},
                {'start_time': 30.0, 'title': 'Palais des Papes', 'end_time': 80.0},
                {'start_time': 80.0, 'title': 'Forêt', 'end_time': 140.0},
                {'start_time': 140.0, 'title': 'Carton', 'end_time': 260.0},
                {'start_time': 260.0, 'title': 'Le repentir', 'end_time': 395.0},
                {'start_time': 395.0, 'title': 'Les architectures de fête', 'end_time': 480.0},
                {'start_time': 480.0, 'title': "L'art contemporain", 'end_time': 535.0},
                {'start_time': 535.0, 'title': "L'habitat troglodyte", 'end_time': 605.0},
                {'start_time': 605.0, 'title': "L'urgence climatique", 'end_time': 701},
            ],
            'comment_count': int,
            'description': 'md5:7a7cc352189bbc16132b5f4819f2ed8a',
            'duration': 701,
            'ext': 'mp4',
            'id': '4fFMuXLWfAo',
            'like_count': int,
            'live_status': 'not_live',
            'playable_in_embed': True,
            'tags': ['Art', 'Culture', "Festival d'Avignon", 'L_INVITE DU JOUR', 'Sculpture', 'france24', 'news'],
            'thumbnail': 'https://i.ytimg.com/vi/4fFMuXLWfAo/sddefault.jpg',
            'timestamp': 1686218017,
            'title': '''Eva Jospin, plasticienne : "Le propre de la sculpture, c'est le rapport à l'espace" • FRANCE 24''',
            'upload_date': '20230608',
            'uploader': 'FRANCE 24',
            'uploader_id': '@FRANCE24',
            'uploader_url': 'https://www.youtube.com/@FRANCE24',
            'view_count': int,
        },
    }, {
        'url': 'https://www.france24.com/en/europe/20250213-ukraine-europe-must-be-involved-peace-talks-say-nato-european-members-russia-trump-rutte',
        'info_dict': {
            'id': '20250213-ukraine-europe-must-be-involved-peace-talks-say-nato-european-members-russia-trump-rutte',
        },
        'playlist': [{
            'info_dict': {
                'age_limit': 0,
                'availability': 'public',
                'categories': ['News & Politics'],
                'channel': 'FRANCE 24 English',
                'channel_follower_count': int,
                'channel_id': 'UCQfwfsi5VrQ8yKZ-UWmAEFg',
                'channel_is_verified': True,
                'channel_url': 'https://www.youtube.com/channel/UCQfwfsi5VrQ8yKZ-UWmAEFg',
                'comment_count': int,
                'description': 'md5:0c13773aaf75c3c4985735dd1242e360',
                'duration': 356,
                'ext': 'mp4',
                'id': 'NxjkC-5a0lo',
                'like_count': int,
                'live_status': 'not_live',
                'playable_in_embed': True,
                'tags': ['Europe', 'NATO', 'USA', 'Ukraine', 'europe', 'nato', 'trump'],
                'thumbnail': 'https://i.ytimg.com/vi/NxjkC-5a0lo/maxresdefault.jpg',
                'timestamp': 1739433984,
                'title': 'Europeans in ‘difficult position’ after US defence chief suggests Ukraine abandon NATO hopes',
                'upload_date': '20250213',
                'uploader': 'FRANCE 24 English',
                'uploader_id': '@France24_en',
                'uploader_url': 'https://www.youtube.com/@France24_en',
                'view_count': int,
            },
        }, {
            'info_dict': {
                'age_limit': 0,
                'availability': 'unlisted',
                'categories': ['News & Politics'],
                'channel': 'FRANCE 24 English',
                'channel_follower_count': int,
                'channel_id': 'UCQfwfsi5VrQ8yKZ-UWmAEFg',
                'channel_is_verified': True,
                'channel_url': 'https://www.youtube.com/channel/UCQfwfsi5VrQ8yKZ-UWmAEFg',
                'description': 'md5:64ba0c95def2144bcd145956a9dfc0d3',
                'duration': 427,
                'ext': 'mp4',
                'id': 'kanu61l-OUg',
                'like_count': int,
                'live_status': 'not_live',
                'playable_in_embed': True,
                'tags': 'count:12',
                'thumbnail': 'https://i.ytimg.com/vi/kanu61l-OUg/sddefault.jpg',
                'timestamp': 1739429955,
                'title': 'Scholz rejects ‘dictated peace’ for Ukraine as Europe reels after Trump-Putin call • FRANCE 24',
                'upload_date': '20250213',
                'uploader': 'FRANCE 24 English',
                'uploader_id': '@France24_en',
                'uploader_url': 'https://www.youtube.com/@France24_en',
                'view_count': int,
            },
        }],
    }, {
        'url': 'https://www.france24.com/en/europe/20250214-drone-warfare-stalls-progress-on-ukraine-s-front-line',
        'only_matching': True,
    }, {
        'url': 'https://www.france24.com/fr/vidéo/20250215-gaza-l-accord-très-fragile-entre-gaza-et-israël-permet-la-libération-de-trois-otages',
        'only_matching': True,
    }, {
        'url': 'https://www.france24.com/en/',
        'only_matching': True,
    }, {
        'url': 'https://www.france24.com',
        'only_matching': True,
    }]
    _USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; rv:135.0) Gecko/20100101 Firefox/135.0'

    def _real_extract(self, url):
        display_id = self._match_id(url).strip('/')
        webpage = self._download_webpage(url, None, 'Downloading video page', headers={'User-Agent': self._USER_AGENT})
        entries = []
        for player in re.findall(r'<(?:youtube|video)-player\b[^>]*>', webpage):
            attrs = extract_attributes(player)
            if not attrs.get('playlist') and attrs.get('video-type') == 'youtube':
                entries.append(self.url_result(attrs.get('source'), video_id=attrs.get('video-id'), ie=YoutubeIE))
        return self.playlist_result(entries, playlist_id=display_id)
