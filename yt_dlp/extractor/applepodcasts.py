from .common import InfoExtractor
from ..utils import (
    clean_html,
    clean_podcast_url,
    int_or_none,
    parse_iso8601,
)
from ..utils.traversal import traverse_obj


class ApplePodcastsIE(InfoExtractor):
    _VALID_URL = r'https?://podcasts\.apple\.com/(?:[^/]+/)?podcast(?:/[^/]+){1,2}.*?\bi=(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://podcasts.apple.com/us/podcast/urbana-podcast-724-by-david-penn/id1531349107?i=1000748574256',
        'md5': 'f8a6f92735d0cfbd5e6a7294151e28d8',
        'info_dict': {
            'id': '1000748574256',
            'ext': 'm4a',
            'title': 'URBANA PODCAST 724 BY DAVID PENN',
            'episode': 'URBANA PODCAST 724 BY DAVID PENN',
            'description': 'md5:fec77bacba32db8c9b3dda5486ed085f',
            'upload_date': '20260206',
            'timestamp': 1770400801,
            'duration': 3602,
            'series': 'Urbana Radio Show',
            'thumbnail': 're:.+[.](png|jpe?g|webp)',
        },
    }, {
        'url': 'https://podcasts.apple.com/us/podcast/207-whitney-webb-returns/id1135137367?i=1000482637777',
        'md5': 'baf8a6b8b8aa6062dbb4639ed73d0052',
        'info_dict': {
            'id': '1000482637777',
            'ext': 'mp3',
            'title': '207 - Whitney Webb Returns',
            'episode': '207 - Whitney Webb Returns',
            'episode_number': 207,
            'description': 'md5:75ef4316031df7b41ced4e7b987f79c6',
            'upload_date': '20200705',
            'timestamp': 1593932400,
            'duration': 5369,
            'series': 'The Tim Dillon Show',
            'thumbnail': 're:.+[.](png|jpe?g|webp)',
        },
    }, {
        'url': 'https://podcasts.apple.com/podcast/207-whitney-webb-returns/id1135137367?i=1000482637777',
        'only_matching': True,
    }, {
        'url': 'https://podcasts.apple.com/podcast/207-whitney-webb-returns?i=1000482637777',
        'only_matching': True,
    }, {
        'url': 'https://podcasts.apple.com/podcast/id1135137367?i=1000482637777',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        episode_id = self._match_id(url)
        webpage = self._download_webpage(url, episode_id)
        server_data = self._search_json(
            r'<script [^>]*\bid=["\']serialized-server-data["\'][^>]*>', webpage,
            'server data', episode_id)['data'][0]['data']
        model_data = traverse_obj(server_data, (
            'headerButtonItems', lambda _, v: v['$kind'] == 'share' and v['modelType'] == 'EpisodeLockup',
            'model', {dict}, any))

        return {
            'id': episode_id,
            **traverse_obj(model_data, {
                'title': ('title', {str}),
                'description': ('summary', {clean_html}),
                'url': ('playAction', 'episodeOffer', 'streamUrl', {clean_podcast_url}),
                'timestamp': ('releaseDate', {parse_iso8601}),
                'duration': ('duration', {int_or_none}),
                'episode': ('title', {str}),
                'episode_number': ('episodeNumber', {int_or_none}),
                'series': ('showTitle', {str}),
            }),
            'thumbnail': self._og_search_thumbnail(webpage),
            'vcodec': 'none',
        }
