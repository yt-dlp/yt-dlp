import re
from collections import namedtuple

from .common import InfoExtractor
from ..utils import (
    int_or_none,
)


class RadioComercialBaseExtractor(InfoExtractor):
    def _extract_page_content(self, url):
        video_id = RadioComercialIE._match_id(url)
        webpage = self._download_webpage(url, video_id)
        title = self._html_search_regex(r'<title>(.+?)</title>', webpage, 'title')
        url = self._html_search_regex(r'<a.+?isExclusivePlay=.+?href="(.+?)">', webpage, 'url')
        date = self._html_search_regex(r'<div[^"]+"date">(\d{4}-\d{2}-\d{2})</div>', webpage, 'date')
        thumbnail = self._html_search_regex(r'<source[^"]+"image/jpeg[^/]+(.+?)\">', webpage, 'thumbnail')
        season = int_or_none(self._html_search_regex(r'<h2>\w+\s(\d+)</h2>', webpage, 'season'))
        episode_id = int_or_none(self._html_search_regex(r'episodeid=(\d+)&', url, 'episode_id'))

        return {
            'id': video_id,
            'title': title,
            'date': date,
            'thumbnail': thumbnail,
            'season': season,
            'episode_id': episode_id,
            'url': url
        }


class RadioComercialIE(RadioComercialBaseExtractor):
    _VALID_URL = r'https?://(?:www\.)?radiocomercial\.pt/podcasts/[^/]+/\w\d+/(?P<id>[-\w]+)/*$'
    _TESTS = [{
        'url': 'https://radiocomercial.pt/podcasts/o-homem-que-mordeu-o-cao/t6/taylor-swift-entranhando-se-que-nem-uma-espada-no-ventre-dos-fas',
        'md5': '5f4fe8e485b29d2e8fd495605bc2c7e4',
        'info_dict': {
            'id': 'taylor-swift-entranhando-se-que-nem-uma-espada-no-ventre-dos-fas',
            'ext': 'mp3',
            'title': 'Taylor Swift entranhando-se que nem uma espada no ventre dos fãs.',
            'date': '2023-10-25',
            'thumbnail': r're:/upload/[^.]+.jpg',
            'season': 6,
            'episode_id': 220899
        }
    },
        {
        'url': 'https://radiocomercial.pt/podcasts/convenca-me-num-minuto/t3/convenca-me-num-minuto-que-os-lobisomens-existem',
        'md5': '47e96c273aef96a8eb160cd6cf46d782',
        'info_dict': {
            'id': 'convenca-me-num-minuto-que-os-lobisomens-existem',
            'ext': 'mp3',
            'title': 'Convença-me num minuto que os lobisomens existem',
            'date': '2023-10-26',
            'thumbnail': r're:/upload/[^.]+.jpg',
            'season': 3,
            'episode_id': 221210
        }
    },
    ]

    def _real_extract(self, url):
        return self._extract_page_content(url)


class RadioComercialPlaylistIE(RadioComercialBaseExtractor):
    _VALID_URL = r'https?://(?:www\.)?radiocomercial\.pt/podcasts/(?P<id>[-\w]+)[/\w\d+]*$'
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
        'playlist_mincount': 100
    },
    ]

    NextPage = namedtuple('NextPage', ['path', 'page', 'add_one'])

    def _extract_next_url_details(self, source):
        regex = re.compile(
            r'\sclass="pagination__next"\shref="(?P<path>/podcasts/[^/]+?[/\w\d+/]+?/)(?P<page>\d+)/*(?P<add_one>\d*)')
        match = regex.search(source)
        if match:
            return self.NextPage(match.group('path'),
                                 int_or_none(match.group('page')), int_or_none(match.group('add_one')))
        return self.NextPage(None, None, None)

    def _get_next_page(self, webpage):
        next_page = self._extract_next_url_details(webpage)
        if not next_page.path or not next_page.page:
            return None
        number_section = f'{next_page.page if not next_page.add_one else next_page.page + 1}'
        next_page = f'https://radiocomercial.pt{next_page.path}{number_section}'
        video_id = self._match_id(next_page)
        return self._download_webpage(next_page, video_id, headers={'X-Requested-With': 'XMLHttpRequest'})

    def _collect_hrefs(self, webpage):
        regex = re.compile(r'rounded-site-bottom"><a class="tm-ouvir-podcast" href="([^"]+)"')
        matches = regex.finditer(webpage)
        for match in matches:
            yield f'https://radiocomercial.pt{match.group(1)}'

    def _generate_sorted_entries(self, list_of_podcasts):
        entries = [self._extract_page_content(item) for item in list_of_podcasts]
        sorted_entries = sorted(entries, key=lambda x: x['date'], reverse=True)
        for entry in sorted_entries:
            yield entry

    def _real_extract(self, url):
        podcast = self._match_id(url)
        webpage = self._download_webpage(url, podcast)

        podcast_name = self._html_search_regex(r'<h1>(.+?)</h1>', webpage, 'name')
        podcast_season = self._html_search_regex(r'<title>(.+?)</title>', webpage, 'season')
        podcast_title = podcast_name if podcast_name == podcast_season else f'{podcast_name} - {podcast_season}'

        list_of_podcasts = set()
        while True:
            get_entries = self._collect_hrefs(webpage)
            if get_entries:
                list_of_podcasts.update(get_entries)
            webpage = self._get_next_page(webpage)
            if not webpage:
                break

        return self.playlist_result(self._generate_sorted_entries(list_of_podcasts), podcast, podcast_title)
