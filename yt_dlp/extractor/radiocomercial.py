import re
from collections import namedtuple

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    int_or_none,
    traverse_obj,
)


class RadioComercialBaseExtractor(InfoExtractor):
    def _extract_page_content(self, url):
        print(f'processing: {url}')
        video_id = self._match_id(url)
        print(video_id)
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
        'md5': '5f4fe8e485b29d2e8fd495605bc2c7e4',
        'info_dict': {
            'id': 'taylor-swift-entranhando-se-que-nem-uma-espada-no-ventre-dos-fas',
            'ext': 'mp3',
            'title': 'Taylor Swift entranhando-se que nem uma espada no ventre dos fãs.',
            'date': '2023-10-25',
            'thumbnail': r're:/upload/[^.]+.jpg',

        }
    },
        {
        'url': 'https://radiocomercial.pt/podcasts/o-homem-que-mordeu-o-cao',
        'md5': '47e96c273aef96a8eb160cd6cf46d782',
        'info_dict': {
            'id': 'convenca-me-num-minuto-que-os-lobisomens-existem',
            'ext': 'mp3',
            'title': 'Convença-me num minuto que os lobisomens existem',
            'date': '2023-10-26',
            'thumbnail': r're:/upload/[^.]+.jpg',
        }
    },
    ]

    # Get all the podcasts in the page
    # <div class="info rounded-site-bottom"><a class="tm-ouvir-podcast" href="/podcasts/o-homem-que-mordeu-o-cao/t6/o-senhor-naturista-pague-se-deite-se-aqui-aqueca-me-os-pes-durma" id="o-senhor-naturista-pague-se-deite-se-aqui-aqueca-me-os-pes-durma"><div class="dateAndTime">
    #entry_url = self._html_search_regex(r'<title>(.+?)</title>', webpage, 'title')

    # Check if there is a next page to call
    # </div><a class="pagination__next" href="/podcasts/o-homem-que-mordeu-o-cao/t6/2"></a></div>
    # the url can have more /s. only the first number should be passed
    # the request needs to include X-Requested-With:XMLHttpRequest

    def _extract_next_url_details(self, source):
        next_page = namedtuple('next_page', ['path', 'page', 'add_one'])
        regex = re.compile(
            r'\sclass="pagination__next"\shref="(?P<path>/podcasts/[^/]+/\w+/)(?P<page>\d+)/*(?P<add_one>\d*)')
        match = regex.search(source)
        if match:
            return next_page(match.group('path'), int_or_none(match.group('page')), int_or_none(match.group('add_one')))
        else:
            return next_page(None, None, None)

    def _get_next_page(self, webpage):
        next_page = self._extract_next_url_details(webpage)
        if not next_page.path or not next_page.page:
            return None
        next_page = f'https://radiocomercial.pt{next_page.path}{next_page.page if not next_page.add_one else next_page.page + 1}'
        print(f'<<<<Next page: {next_page}')
        video_id = self._match_id(next_page)
        return self._download_webpage(next_page, video_id, headers={'X-Requested-With': 'XMLHttpRequest'})

    def _collect_hrefs(self, webpage):
        regex = re.compile(r'rounded-site-bottom"><a class="tm-ouvir-podcast" href="([^"]+)"')
        matches = regex.finditer(webpage)
        hrefs = []
        for match in matches:
            hrefs.append(f'https://radiocomercial.pt{match.group(1)}')
        #for index, item in enumerate(hrefs):
        #    print(index, " - ", item)
        return hrefs

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        list_of_podcasts = set()
        get_entries = self._collect_hrefs(webpage)
        if get_entries:
            list_of_podcasts.update(get_entries)
        while True:
            webpage = self._get_next_page(webpage)
            if not webpage:
                break
            get_entries = self._collect_hrefs(webpage)
            if get_entries:
                list_of_podcasts.update(get_entries)

        if list_of_podcasts:
            print(f'<<< Processing #{len(list_of_podcasts)} items.')
            for index, url in enumerate(list_of_podcasts):
                print(f'Processing item #{index + 1} - {url}')
                yield self._extract_page_content(url)
