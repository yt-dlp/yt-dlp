import itertools

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    extract_attributes,
    get_element_by_class,
    get_element_html_by_class,
    get_element_text_and_html_by_tag,
    get_elements_html_by_class,
    int_or_none,
    join_nonempty,
    try_call,
    unified_strdate,
    update_url,
    urljoin
)
from ..utils.traversal import traverse_obj


class RadioComercialIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?radiocomercial\.pt/podcasts/[^/?#]+/t?(?P<season>\d+)/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://radiocomercial.pt/podcasts/o-homem-que-mordeu-o-cao/t6/taylor-swift-entranhando-se-que-nem-uma-espada-no-ventre-dos-fas#page-content-wrapper',
        'md5': '5f4fe8e485b29d2e8fd495605bc2c7e4',
        'info_dict': {
            'id': 'taylor-swift-entranhando-se-que-nem-uma-espada-no-ventre-dos-fas',
            'ext': 'mp3',
            'title': 'Taylor Swift entranhando-se que nem uma espada no ventre dos fãs.',
            'release_date': '20231025',
            'thumbnail': r're:https://radiocomercial.pt/upload/[^.]+.jpg',
            'season': 6
        }
    }, {
        'url': 'https://radiocomercial.pt/podcasts/convenca-me-num-minuto/t3/convenca-me-num-minuto-que-os-lobisomens-existem',
        'md5': '47e96c273aef96a8eb160cd6cf46d782',
        'info_dict': {
            'id': 'convenca-me-num-minuto-que-os-lobisomens-existem',
            'ext': 'mp3',
            'title': 'Convença-me num minuto que os lobisomens existem',
            'release_date': '20231026',
            'thumbnail': r're:https://radiocomercial.pt/upload/[^.]+.jpg',
            'season': 3
        }
    }, {
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
        },
        'params': {
            # inconsistant md5
            'skip_download': True,
        },
    }, {
        'url': 'https://radiocomercial.pt/podcasts/tnt-todos-no-top/2023/t-n-t-29-de-outubro',
        'md5': '91d32d4d4b1407272068b102730fc9fa',
        'info_dict': {
            'id': 't-n-t-29-de-outubro',
            'ext': 'mp3',
            'title': 'T.N.T 29 de outubro',
            'release_date': '20231029',
            'thumbnail': r're:https://radiocomercial.pt/upload/[^.]+.jpg',
            'season': 2023
        }
    }]

    def _real_extract(self, url):
        video_id, season = self._match_valid_url(url).group('id', 'season')
        webpage = self._download_webpage(url, video_id)
        return {
            'id': video_id,
            'title': self._html_extract_title(webpage),
            'description': self._og_search_description(webpage, default=None),
            'release_date': unified_strdate(get_element_by_class(
                'date', get_element_html_by_class('descriptions', webpage) or '')),
            'thumbnail': self._og_search_thumbnail(webpage),
            'season': int_or_none(season),
            'url': extract_attributes(get_element_html_by_class('audiofile', webpage) or '').get('href'),
        }


class RadioComercialPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?radiocomercial\.pt/podcasts/(?P<id>[\w-]+)(?:/t?(?P<season>\d+))?/?(?:$|[?#])'
    _TESTS = [{
        'url': 'https://radiocomercial.pt/podcasts/convenca-me-num-minuto/t3',
        'info_dict': {
            'id': 'convenca-me-num-minuto_t3',
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
    }, {
        'url': 'https://radiocomercial.pt/podcasts/tnt-todos-no-top/t2023',
        'info_dict': {
            'id': 'tnt-todos-no-top_t2023',
            'title': 'TNT - Todos No Top - Temporada 2023',
        },
        'playlist_mincount': 39
    }]

    def _entries(self, url, playlist_id):
        for page in itertools.count(1):
            try:
                webpage = self._download_webpage(
                    f'{url}/{page}', playlist_id, f'Downloading page {page}')
            except ExtractorError as e:
                if isinstance(e.cause, HTTPError) and e.cause.status == 404:
                    break
                raise

            episodes = get_elements_html_by_class('tm-ouvir-podcast', webpage)
            if not episodes:
                break
            for url_path in traverse_obj(episodes, (..., {extract_attributes}, 'href')):
                episode_url = urljoin(url, url_path)
                if RadioComercialIE.suitable(episode_url):
                    yield episode_url

    def _real_extract(self, url):
        podcast, season = self._match_valid_url(url).group('id', 'season')
        playlist_id = join_nonempty(podcast, season, delim='_t')
        url = update_url(url, query=None, fragment=None)
        webpage = self._download_webpage(url, playlist_id)

        name = try_call(lambda: get_element_text_and_html_by_tag('h1', webpage)[0])
        title = name if name == season else join_nonempty(name, season, delim=' - Temporada ')

        return self.playlist_from_matches(
            self._entries(url, playlist_id), playlist_id, title, ie=RadioComercialIE)
