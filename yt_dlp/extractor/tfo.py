import urllib.parse

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    clean_html,
    int_or_none,
    parse_iso8601,
    str_or_none,
    url_or_none,
    urljoin,
    variadic,
)
from ..utils.traversal import require, traverse_obj


class TFOBaseIE(InfoExtractor):
    _BASE_URL = 'https://www.tfo.org'
    _GEO_COUNTRIES = ['CA']


class TFOIE(TFOBaseIE):
    IE_NAME = 'tfo'
    IE_DESC = 'Télévision française de l\'Ontario'

    _VALID_URL = r'https?://(?:www\.)?tfo\.org/(?:episode|film|regarder|titre)(?:/[\w-]+)+/(?P<id>(?:GP)?\d{6})'
    _TESTS = [{
        'url': 'https://www.tfo.org/regarder/pouletosaure-rex-partie-1-2/GP639511',
        'info_dict': {
            'id': 'GP639511',
            'ext': 'mp4',
            'title': 'Pouletosaure Rex - Partie 1 & 2',
            'age_limit': 6,
            'alt_title': 'pouletosaure-rex-partie-1-2',
            'description': 'md5:24e1b629fab54d537eb40a0ef6630afa',
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
            'thumbnail': r're:https?://.+\.(?:jpg|png)',
        },
    }, {
        'url': 'https://www.tfo.org/episode/passeport-pour-le-monde/saison-2/episode-1/vietnam-dans-loeil-du-dragon/GP938523',
        'info_dict': {
            'id': 'GP938523',
            'ext': 'mp4',
            'title': 'VIETNAM : Dans l\'oeil du dragon',
            'age_limit': 18,
            'alt_title': 'vietnam-dans-loeil-du-dragon',
            'description': 'md5:ca182241d021ba832680ccbc09dc70fd',
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
            'thumbnail': r're:https?://.+\.(?:jpg|png)',
        },
    }, {
        'url': 'https://www.tfo.org/titre/entre-les-lignes/GP704192',
        'info_dict': {
            'id': 'GP704192',
            'ext': 'mp4',
            'title': 'Entre les lignes',
            'age_limit': 0,
            'alt_title': 'entre-les-lignes',
            'genres': ['Société'],
            'release_date': '20231105',
            'release_timestamp': 1699146000,
            'release_year': 2008,
            'series': 'Entre les lignes',
            'tags': ['G'],
            'thumbnail': r're:https?://.+\.(?:jpg|png)',
        },
    }, {
        'url': 'https://www.tfo.org/film/a-nous-la-liberte/852897',
        'info_dict': {
            'id': '852897',
            'ext': 'mp4',
            'title': 'À nous la liberté',
            'age_limit': 0,
            'alt_title': 'a-nous-la-liberte',
            'description': 'md5:2e7d617f0b7451b9f31c1bfb62d6f33b',
            'genres': ['Comédie', 'Satirique'],
            'release_date': '20250811',
            'release_timestamp': 1754874007,
            'release_year': 1931,
            'series': 'À nous la liberté',
            'tags': ['G'],
            'thumbnail': r're:https?://.+\.(?:jpg|png)',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        slug = urllib.parse.urlparse(url).path.rstrip('/').split('/')[-2]
        webpage = self._download_webpage(
            f'{self._BASE_URL}/regarder/{slug}/{video_id}', video_id)
        nextjs_data = self._search_nextjs_data(webpage, video_id)

        build_id, locale = traverse_obj(nextjs_data, (('buildId', 'locale'), {str}, all))
        path = urllib.parse.urlparse(self._og_search_url(webpage)).path

        try:
            video_data = self._download_json(
                f'{self._BASE_URL}/_next/data/{build_id}/{locale}{path}.json', video_id)
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 404:
                return self.url_result(url, self.ie_key())
        product = traverse_obj(video_data, (
            'pageProps', 'product', {require('video information')}))

        page_props = nextjs_data['props']['pageProps']
        season_id = traverse_obj(page_props, ('seasonId', {str_or_none}))
        m3u8_url = traverse_obj(page_props, ('metadata', 'video', {url_or_none}))
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(m3u8_url, video_id, 'mp4')

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(product, {
                'title': ('name', {clean_html}, filter),
                'age_limit': ('ratingCode', {int_or_none}),
                'alt_title': ('slug', {str_or_none}),
                'description': ('longDescription', {clean_html}, filter),
                'genres': ('genres', ..., {clean_html}, filter),
                'release_timestamp': ('begin', {parse_iso8601}),
                'release_year': ('productionYear', {int_or_none}),
                'series': ('name', {clean_html}),
                'series_id': ('serieId', {str_or_none}),
                'tags': ('tags', ..., 'label', {clean_html}, filter),
                'thumbnail': ('bannerUrl', {url_or_none}),
            }),
            **traverse_obj(product, (
                'seasons', ..., 'episodes',
                lambda _, v: v.get('id') == video_id, any, {
                    'title': ('name', {clean_html}, filter),
                    'age_limit': ('ageRangeCode', {int_or_none}),
                    'alt_title': ('slug', {str_or_none}),
                    'description': ('description', {clean_html}, filter),
                    'episode': ('episodeName', {clean_html}, filter),
                    'episode_id': (
                        'episodeNumber', {str_or_none},
                        {lambda x: f'episode-{x}' if x else None},
                    ),
                    'episode_number': ('episodeNumber', {int_or_none}),
                    'genres': ('genres', ..., {clean_html}, filter),
                    'release_timestamp': ('begin', {parse_iso8601}),
                    'tags': ('tags', ..., 'label', {clean_html}, filter),
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
        }


class TFOSeriesIE(TFOBaseIE):
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
        'playlist_mincount': 13,
    }]

    def _real_extract(self, url):
        season_number, series_id = self._match_valid_url(url).group('season', 'id')
        webpage = self._download_webpage(url, series_id)
        nextjs_data = self._search_nextjs_data(webpage, series_id)
        path = (lambda _, v: v['seasonNumber'] == season_number) if season_number else ...

        entries = [
            self.url_result(x, TFOIE)
            for x in traverse_obj(nextjs_data, (
                'props', 'pageProps', 'product', 'seasons', *variadic(path),
                'episodes', ..., 'canonicalUrl', {urljoin(f'{self._BASE_URL}/')},
            ))
        ]

        return self.playlist_result(
            entries, series_id, self._html_search_meta(['og:image:alt', 'twitter:image:alt'], webpage))
