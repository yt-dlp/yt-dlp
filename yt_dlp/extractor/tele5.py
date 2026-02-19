import functools

from .dplay import DiscoveryPlusBaseIE
from ..utils import join_nonempty
from ..utils.traversal import traverse_obj


class Tele5IE(DiscoveryPlusBaseIE):
    _VALID_URL = r'https?://(?:www\.)?tele5\.de/(?P<parent_slug>[\w-]+)/(?P<slug_a>[\w-]+)(?:/(?P<slug_b>[\w-]+))?'
    _TESTS = [{
        # slug_a and slug_b
        'url': 'https://tele5.de/mediathek/star-trek-enterprise/vox-sola',
        'info_dict': {
            'id': '4140114',
            'ext': 'mp4',
            'title': 'Vox Sola',
            'description': 'md5:329d115f74324d4364efc1a11c4ea7c9',
            'duration': 2542.76,
            'thumbnail': r're:https://[^/.]+\.disco-api\.com/.+\.jpe?g',
            'tags': [],
            'creators': ['Tele5'],
            'series': 'Star Trek - Enterprise',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 22',
            'episode_number': 22,
            'timestamp': 1770491100,
            'upload_date': '20260207',
        },
    }, {
        # only slug_a
        'url': 'https://tele5.de/mediathek/30-miles-from-nowhere-im-wald-hoert-dich-niemand-schreien',
        'info_dict': {
            'id': '4102641',
            'ext': 'mp4',
            'title': '30 Miles from Nowhere - Im Wald hört dich niemand schreien',
            'description': 'md5:0b731539f39ee186ebcd9dd444a86fc2',
            'duration': 4849.96,
            'thumbnail': r're:https://[^/.]+\.disco-api\.com/.+\.jpe?g',
            'tags': [],
            'creators': ['Tele5'],
            'series': '30 Miles from Nowhere - Im Wald hört dich niemand schreien',
            'timestamp': 1770417300,
            'upload_date': '20260206',
        },
    }, {
        # playlist
        'url': 'https://tele5.de/mediathek/schlefaz',
        'info_dict': {
            'id': 'mediathek-schlefaz',
        },
        'playlist_mincount': 3,
        'skip': 'Dead link',
    }]

    def _real_extract(self, url):
        parent_slug, slug_a, slug_b = self._match_valid_url(url).group('parent_slug', 'slug_a', 'slug_b')
        playlist_id = join_nonempty(parent_slug, slug_a, slug_b, delim='-')

        query = {
            'include': 'default',
            'filter[environment]': 'tele5',
            'v': '2',
        }

        if not slug_b:
            endpoint = f'page/{slug_a}'
            query['parent_slug'] = parent_slug
        else:
            endpoint = f'shows/{slug_a}'
            query['filter[video.slug]'] = slug_b

        cms_data = self._download_json(f'https://public.aurora.enhanced.live/site/{endpoint}/', playlist_id, query=query)

        return self.playlist_result(map(
            functools.partial(self._get_disco_api_info, url, disco_host='eu1-prod.disco-api.com', realm='dmaxde', country='DE'),
            traverse_obj(cms_data, ('blocks', ..., 'videoId', {str}))), playlist_id)

    def _update_disco_api_headers(self, headers, disco_base, display_id, realm):
        headers.update({
            'x-disco-params': f'realm={realm}',
            'x-disco-client': 'Alps:HyogaPlayer:0.0.0',
            'Authorization': self._get_auth(disco_base, display_id, realm),
        })
