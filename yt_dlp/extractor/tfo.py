import urllib.parse

from .common import InfoExtractor
from .uplynk import UplynkBaseIE
from ..utils import (
    clean_html,
    int_or_none,
    parse_iso8601,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import require, traverse_obj


class TFOIE(UplynkBaseIE):
    IE_NAME = 'tfo'
    IE_DESC = 'Télévision française de l\'Ontario'

    _BASE_URL = 'https://www.tfo.org'
    _VALID_URL = r'https?://(?:www\.)?tfo\.org/(?:episode|film|regarder|titre)(?:/[\w-]+)+/(?P<id>(?:GP)?\d{6})'
    _TESTS = [{
        'url': 'https://www.tfo.org/regarder/bardot-la-meprise/GP701766',
        'info_dict': {
            'id': 'GP701766',
            'ext': 'mp4',
            'title': 'Bardot, la Méprise',
            'age_limit': 13,
            'alt_title': 'bardot-la-meprise',
            'description': 'md5:16ca832101b6c3838bb61cd8fa06aa9e',
            'duration': 3134.8480000000022,
            'genres': ['Biographie et portraits'],
            'release_timestamp': 1747875610,
            'release_date': '20250522',
            'release_year': 2013,
            'series': 'Bardot, la Méprise',
            'tags': ['13+'],
            'thumbnail': r're:https?://.+\.jpg',
            'uploader_id': '872295f75a144bcf880cf68f4ad35db1',
        },
        'skip': True,
    }, {
        'url': 'https://www.tfo.org/regarder/pouletosaure-rex-partie-1-2/GP639511',
        'info_dict': {
            'id': 'GP639511',
            'ext': 'mp4',
            'title': 'Pouletosaure Rex - Partie 1 & 2',
            'age_limit': 6,
            'alt_title': 'pouletosaure-rex-partie-1-2',
            'description': 'md5:24e1b629fab54d537eb40a0ef6630afa',
            'duration': 1321.216000000001,
            'episode': 'Pouletosaure Rex - Partie 1 & 2',
            'episode_id': 'episode-1',
            'episode_number': 1,
            'genres': ['6 à 9 ans'],
            'release_date': '20250406',
            'release_timestamp': 1743912000,
            'release_year': 2025,
            'season': 'Saison 1',
            'season_id': 'saison-1',
            'season_number': 1,
            'series': 'Dino Dex',
            'series_id': '003051136',
            'tags': ['G'],
            'thumbnail': r're:https?://.+\.jpg',
            'uploader_id': '872295f75a144bcf880cf68f4ad35db1',
        },
        'skip': True,
    }, {
        'url': 'https://www.tfo.org/episode/passeport-pour-le-monde/saison-2/episode-1/vietnam-dans-loeil-du-dragon/GP938523',
        'info_dict': {
            'id': 'GP938523',
            'ext': 'mp4',
            'title': 'VIETNAM : Dans l\'oeil du dragon',
            'age_limit': 18,
            'alt_title': 'vietnam-dans-loeil-du-dragon',
            'description': 'md5:ca182241d021ba832680ccbc09dc70fd',
            'duration': 3120.0000000000023,
            'episode': 'VIETNAM : Dans l\'oeil du dragon',
            'episode_id': 'episode-1',
            'episode_number': 1,
            'genres': ['Voyage et découverte'],
            'release_date': '20250331',
            'release_timestamp': 1743393600,
            'release_year': 2025,
            'season': 'Saison 2',
            'season_id': 'saison-2',
            'season_number': 2,
            'series': 'Passeport pour le monde',
            'series_id': '002968508',
            'tags': ['G'],
            'thumbnail': r're:https?://.+\.jpg',
            'uploader_id': '872295f75a144bcf880cf68f4ad35db1',
        },
        'skip': True,
    }, {
        'url': 'https://www.tfo.org/titre/entre-les-lignes/GP704192',
        'info_dict': {
            'id': 'GP704192',
            'ext': 'mp4',
            'title': 'Entre les lignes',
            'age_limit': 0,
            'alt_title': 'entre-les-lignes',
            'duration': 2042.8800000000015,
            'genres': ['Société'],
            'release_date': '20231105',
            'release_timestamp': 1699146000,
            'release_year': 2008,
            'series': 'Entre les lignes',
            'tags': ['G'],
            'thumbnail': r're:https?://.+\.jpg',
            'uploader_id': '872295f75a144bcf880cf68f4ad35db1',
        },
        'skip': True,
    }, {
        'url': 'https://www.tfo.org/film/le-chat/498047',
        'info_dict': {
            'id': '498047',
            'ext': 'mp4',
            'title': 'Le Chat',
            'age_limit': 16,
            'alt_title': 'le-chat',
            'description': 'md5:1e19c39fff1a48e3875feb73a52146b7',
            'duration': 5257.7279999998755,
            'genres': ['Drame', 'Psychologique'],
            'release_date': '20250617',
            'release_timestamp': 1750122010,
            'release_year': 1971,
            'series': 'Le Chat',
            'tags': ['16+'],
            'thumbnail': r're:https?://.+\.jpg',
            'uploader_id': '872295f75a144bcf880cf68f4ad35db1',
        },
        'skip': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        slug = urllib.parse.urlparse(url).path.rstrip('/').split('/')[-2]
        webpage = self._download_webpage(
            f'{self._BASE_URL}/regarder/{slug}/{video_id}', video_id)

        next_data = self._search_nextjs_data(webpage, video_id)
        page_props = next_data['props']['pageProps']
        season_id = traverse_obj(page_props, ('seasonId', {str_or_none}))

        build_id, locale = traverse_obj(next_data, (('buildId', 'locale'), {str}, all))
        path = urllib.parse.urlparse(self._og_search_url(webpage)).path

        video_data = self._download_json(
            f'{self._BASE_URL}/_next/data/{build_id}/{locale}{path}.json',
            video_id, expected_status=404)
        product = traverse_obj(video_data, (
            'pageProps', 'product', {require('video information')}))

        return {
            **self._extract_uplynk_info(traverse_obj(page_props, (
                'metadata', 'video', {url_or_none},
            ))),
            **traverse_obj(product, {
                'title': ('name', {str}),
                'age_limit': ('ratingCode', {int_or_none}),
                'alt_title': ('slug', {str_or_none}),
                'description': ('longDescription', {clean_html}),
                'genres': ('genres', ..., {str}),
                'release_timestamp': ('begin', {parse_iso8601}),
                'release_year': ('productionYear', {int_or_none}),
                'series': ('name', {str}),
                'series_id': ('serieId', {str_or_none}),
                'tags': ('tags', ..., 'label', {str}),
                'thumbnail': ('bannerUrl', {url_or_none}),
            }),
            **traverse_obj(product, (
                'seasons', ..., 'episodes',
                lambda _, v: v.get('id') == video_id, any, {
                    'title': ('name', {str}),
                    'age_limit': ('ageRangeCode', {int_or_none}),
                    'alt_title': ('slug', {str_or_none}),
                    'description': ('description', {clean_html}),
                    'episode': ('episodeName', {str}),
                    'episode_id': (
                        'episodeNumber', {str_or_none},
                        {lambda x: f'episode-{x}' if x else None},
                    ),
                    'episode_number': ('episodeNumber', {int_or_none}),
                    'genres': ('genres', ..., {str}),
                    'release_timestamp': ('begin', {parse_iso8601}),
                    'tags': ('tags', ..., 'label', {str}),
                    'thumbnail': ('imageUrl', {url_or_none}),
                },
            )),
            **traverse_obj(product, (
                'seasons', lambda _, v: v.get('id') == season_id, any, {
                    'season': ('slug', {str_or_none}, {lambda x: f'Saison {x}' if x else None}),
                    'season_id': ('slug', {str_or_none}, {lambda x: f'saison-{x}' if x else None}),
                    'season_number': ('seasonNumber', {int_or_none}),
                },
            )),
            'id': video_id,
        }


class TFOSeriesIE(InfoExtractor):
    IE_NAME = 'tfo:series'

    _VALID_URL = r'https?://(?:www\.)?tfo\.org/serie/[\w-]+(?:/saison-(?P<season>\d+))?/(?P<id>\d{9})'
    _TESTS = [{
        'url': 'https://www.tfo.org/serie/super-mini-monstres/002748228',
        'info_dict': {
            'id': '002748228',
            'title': 'Super mini monstres',
        },
        'playlist_count': 44,
    }, {
        'url': 'https://www.tfo.org/serie/chacun-son-ile/saison-2/002981471',
        'info_dict': {
            'id': '002981471',
            'title': 'Chacun son île | Saison 2',
        },
        'playlist_mincount': 8,
    }]

    def _real_extract(self, url):
        season, series_id = self._match_valid_url(url).groups()
        webpage = self._download_webpage(url, series_id)
        json_ld = next(self._yield_json_ld(webpage, series_id))

        entries = [
            self.url_result(x, TFOIE)
            for x in traverse_obj(json_ld, (
                '@graph', ..., *(() if season else ('seasons', ...)),
                'episode', ..., 'url', {url_or_none},
            ))
        ]

        return self.playlist_result(
            entries, series_id, self._html_search_meta(['og:image:alt', 'twitter:image:alt'], webpage))
