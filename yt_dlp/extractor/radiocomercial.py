import functools

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    unified_strdate,
    get_element_by_class,
    get_element_html_by_class,
    extract_attributes,
    try_call,
    get_element_text_and_html_by_tag,
    join_nonempty,
    get_elements_html_by_class,
    traverse_obj,
    OnDemandPagedList
)


class RadioComercialIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?radiocomercial\.pt/podcasts/[^/]+/\w(?P<season>\d+)/(?P<id>[-\w]+)/*$'
    _TESTS = [{
        'url': 'https://radiocomercial.pt/podcasts/o-homem-que-mordeu-o-cao/t6/taylor-swift-entranhando-se-que-nem-uma-espada-no-ventre-dos-fas',
        'md5': '5f4fe8e485b29d2e8fd495605bc2c7e4',
        'info_dict': {
            'id': 'taylor-swift-entranhando-se-que-nem-uma-espada-no-ventre-dos-fas',
            'ext': 'mp3',
            'title': 'Taylor Swift entranhando-se que nem uma espada no ventre dos fãs.',
            'description': '',
            'release_date': '20231025',
            'thumbnail': r're:https://radiocomercial.pt/upload/[^.]+.jpg',
            'season': 6
        }
    },
        {
        'url': 'https://radiocomercial.pt/podcasts/convenca-me-num-minuto/t3/convenca-me-num-minuto-que-os-lobisomens-existem',
        'md5': '47e96c273aef96a8eb160cd6cf46d782',
        'info_dict': {
            'id': 'convenca-me-num-minuto-que-os-lobisomens-existem',
            'ext': 'mp3',
            'title': 'Convença-me num minuto que os lobisomens existem',
            'description': '',
            'release_date': '20231026',
            'thumbnail': r're:https://radiocomercial.pt/upload/[^.]+.jpg',
            'season': 3
        }
    },
        {
        'url': 'https://radiocomercial.pt/podcasts/inacreditavel-by-ines-castel-branco/t2/o-desastre-de-aviao',
        'md5': '69be64255420fec23b7259955d771e54',
        'info_dict': {
            'id': 'o-desastre-de-aviao',
            'ext': 'mp3',
            'title': 'O desastre de avião',
            'description': 'md5:8a82beeb372641614772baab7246245f',
            'release_date': '20231101',
            'thumbnail': r're:https://radiocomercial.pt/upload/[^.]+.jpg',
            'season': 2
        }
    },
    ]

    def _real_extract(self, url):
        video_id, season = self._match_valid_url(url).group('id', 'season')
        webpage = self._download_webpage(url, video_id)
        return {
            'id': video_id,
            'title': self._html_extract_title(webpage),
            'description': self._og_search_description(webpage, default=''),
            'release_date': unified_strdate(
                get_element_by_class('date', get_element_html_by_class('descriptions', webpage))),
            'thumbnail': self._og_search_thumbnail(webpage),
            'season': int_or_none(season),
            'url': extract_attributes(get_element_html_by_class('audiofile', webpage) or '').get('href'),
        }


class RadioComercialPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?radiocomercial\.pt/podcasts/(?P<id>[-\w]+)[/\w\d+]*$'
    _PAGE_SIZE = 19
    _TESTS = [{
        'url': 'https://radiocomercial.pt/podcasts/convenca-me-num-minuto/t3',
        'info_dict': {
            'id': 'convenca-me-num-minuto',
            'title': 'Convença-me num Minuto - Temporada 3',
        },
        'playlist_mincount': 32
    }, {
        'url': 'https://radiocomercial.pt/podcasts/o-homem-que-mordeu-o-cao',
        'info_dict': {
            'id': 'o-homem-que-mordeu-o-cao',
            'title': 'O Homem Que Mordeu o Cão',
        },
        'playlist_mincount': 19
    }, {
        'url': 'https://radiocomercial.pt/podcasts/as-minhas-coisas-favoritas',
        'info_dict': {
            'id': 'as-minhas-coisas-favoritas',
            'title': 'As Minhas Coisas Favoritas',
        },
        'playlist_mincount': 131
    },
    ]

    def _fetch_page(self, url, season, page):
        page += 1
        next_page = f'{url}{"/" + str(page) if page > 1 else ""}'
        webpage = self._download_webpage(next_page, season, headers={'X-Requested-With': 'XMLHttpRequest'},
                                         note=f'Downloading page: {next_page}')
        episodes = set(traverse_obj(get_elements_html_by_class('tm-ouvir-podcast', webpage),
                                    (..., {extract_attributes}, 'href')))
        for entry in episodes:
            yield self.url_result(f'https://radiocomercial.pt{entry}', RadioComercialIE)

    def _real_extract(self, url):
        podcast = self._match_id(url)
        webpage = self._download_webpage(url, podcast)

        name = try_call(lambda: get_element_text_and_html_by_tag('h1', webpage)[0])
        season = self._html_extract_title(webpage)
        title = name if name == season else join_nonempty(name, season, delim=' - ')

        return self.playlist_result(OnDemandPagedList(functools.partial(self._fetch_page, url, season),
                                                      self._PAGE_SIZE), podcast, title)
