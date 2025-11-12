import functools

from .dplay import DiscoveryPlusBaseIE
from ..utils import join_nonempty
from ..utils.traversal import traverse_obj


class Tele5IE(DiscoveryPlusBaseIE):
    _VALID_URL = r'https?://(?:www\.)?tele5\.de/(?P<parent_slug>[\w-]+)/(?P<slug_a>[\w-]+)(?:/(?P<slug_b>[\w-]+))?'
    _TESTS = [{
        # slug_a and slug_b
        'url': 'https://tele5.de/mediathek/stargate-atlantis/quarantane',
        'info_dict': {
            'id': '6852024',
            'ext': 'mp4',
            'title': 'Quarantäne',
            'description': 'md5:6af0373bd0fcc4f13e5d47701903d675',
            'episode': 'Episode 73',
            'episode_number': 73,
            'season': 'Season 4',
            'season_number': 4,
            'series': 'Stargate Atlantis',
            'upload_date': '20240525',
            'timestamp': 1716643200,
            'duration': 2503.2,
            'thumbnail': 'https://eu1-prod-images.disco-api.com/2024/05/21/c81fcb45-8902-309b-badb-4e6d546b575d.jpeg',
            'creators': ['Tele5'],
            'tags': [],
        },
    }, {
        # only slug_a
        'url': 'https://tele5.de/mediathek/inside-out',
        'info_dict': {
            'id': '6819502',
            'ext': 'mp4',
            'title': 'Inside out',
            'description': 'md5:7e5f32ed0be5ddbd27713a34b9293bfd',
            'series': 'Inside out',
            'upload_date': '20240523',
            'timestamp': 1716494400,
            'duration': 5343.4,
            'thumbnail': 'https://eu1-prod-images.disco-api.com/2024/05/15/181eba3c-f9f0-3faf-b14d-0097050a3aa4.jpeg',
            'creators': ['Tele5'],
            'tags': [],
        },
    }, {
        # playlist
        'url': 'https://tele5.de/mediathek/schlefaz',
        'info_dict': {
            'id': 'mediathek-schlefaz',
        },
        'playlist_mincount': 3,
    }]

    def _real_extract(self, url):
        parent_slug, slug_a, slug_b = self._match_valid_url(url).group('parent_slug', 'slug_a', 'slug_b')
        playlist_id = join_nonempty(parent_slug, slug_a, slug_b, delim='-')

        query = {'environment': 'tele5', 'v': '2'}
        if not slug_b:
            endpoint = f'page/{slug_a}'
            query['parent_slug'] = parent_slug
        else:
            endpoint = f'videos/{slug_b}'
            query['filter[show.slug]'] = slug_a
        cms_data = self._download_json(f'https://de-api.loma-cms.com/feloma/{endpoint}/', playlist_id, query=query)

        return self.playlist_result(map(
            functools.partial(self._get_disco_api_info, url, disco_host='eu1-prod.disco-api.com', realm='dmaxde', country='DE'),
            traverse_obj(cms_data, ('blocks', ..., 'videoId', {str}))), playlist_id)

    def _update_disco_api_headers(self, headers, disco_base, display_id, realm):
        headers.update({
            'x-disco-params': f'realm={realm}',
            'x-disco-client': 'Alps:HyogaPlayer:0.0.0',
            'Authorization': self._get_auth(disco_base, display_id, realm),
        })
