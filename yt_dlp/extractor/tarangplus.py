import base64
import binascii
import functools
import re

from .common import InfoExtractor
from ..dependencies import Cryptodome
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    extract_attributes,
    get_element_by_id,
    get_element_html_by_class,
    get_element_text_and_html_by_tag,
    get_elements_html_by_class,
    traverse_obj,
    urljoin,
)


class TarangPlusBaseIE(InfoExtractor):
    _BASE_URL = 'https://tarangplus.in'


class TarangPlusVideoIE(TarangPlusBaseIE):
    IE_NAME = 'tarangplus:video'
    _VALID_URL = r'https?://(?:www\.)?tarangplus\.in/(?:movies|[^#?/]+/[^#?/]+)/(?!episodes$)(?P<id>[^#?/]+)'
    _TESTS = [{
        'url': 'https://tarangplus.in/tarangaplus-originals/khitpit/khitpit-ep-10',
        'md5': '78ce056cee755687b8a48199909ecf53',
        'info_dict': {
            'id': '67b8206719521d054c0059b7',
            'display_id': 'khitpit-ep-10',
            'ext': 'mp4',
            'title': 'Khitpit Ep-10',
            'description': 'md5:a45b805cb628e15c853d78b0406eab48',
            'thumbnail': r're:https?://.*\.jpg',
            'duration': 756.0,
            'timestamp': 1740355200,
            'upload_date': '20250224',
            'media_type': 'episode',
            'categories': ['Originals'],
        },
    }, {
        'url': 'https://tarangplus.in/tarang-serials/bada-bohu/bada-bohu-ep-233',
        'md5': 'b4f9beb15172559bb362203b4f48382e',
        'info_dict': {
            'id': '680b9d6c19521d054c007782',
            'display_id': 'bada-bohu-ep-233',
            'ext': 'mp4',
            'title': 'Bada Bohu  | Ep -233',
            'description': 'md5:e6b8e7edc9e60b92c1b390f8789ecd69',
            'thumbnail': r're:https?://.*\.jpg',
            'duration': 1392.0,
            'timestamp': 1745539200,
            'upload_date': '20250425',
            'media_type': 'episode',
            'categories': ['Prime'],
        },
    }, {
        'url': 'https://tarangplus.in/short/ai-maa/ai-maa',
        'only_matching': True,
    }, {
        'url': 'https://tarangplus.in/shows/tarang-cine-utsav-2024/tarang-cine-utsav-2024-seg-1',
        'only_matching': True,
    }, {
        'url': 'https://tarangplus.in/music-videos/chori-chori-bohu-chori-songs/nijara-laguchu-dhire-dhire',
        'only_matching': True,
    }, {
        'url': 'https://tarangplus.in/kids-shows/chhota-jaga/chhota-jaga-ep-33-jamidar-ra-khajana-adaya',
        'only_matching': True,
    }, {
        'url': 'https://tarangplus.in/movies/swayambara',
        'only_matching': True,
    }]

    def decrypt(self, data, key):
        if not Cryptodome.AES:
            raise ExtractorError('pycryptodomex not found. Please install', expected=True)
        iv = binascii.unhexlify('00000000000000000000000000000000')
        cipher = Cryptodome.AES.new(base64.b64decode(key), Cryptodome.AES.MODE_CBC, iv)
        return cipher.decrypt(base64.b64decode(data)).decode('utf-8')

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        hidden_inputs_data = self._hidden_inputs(webpage)
        json_ld_data = self._search_json_ld(webpage, display_id)
        del json_ld_data['url']
        iframe_div = get_element_html_by_class('item_details_page', webpage)
        iframe_elem = get_element_text_and_html_by_tag('iframe', iframe_div)[1]
        iframe_src = extract_attributes(iframe_elem)['src']
        url_data = re.search(r'contenturl=(?P<data>[^|]+).*key=(?P<key>[^|]+)', iframe_src)
        m3u8_url = self.decrypt(url_data.group('data'), url_data.group('key'))
        return {
            'display_id': display_id,
            **json_ld_data,
            **traverse_obj(hidden_inputs_data, {
                'id': ('content_id', {str}),
                'media_type': ('theme_type', {str}),
                'categories': ('genre', {str}, filter, all, filter),
            }),
            'formats': self._extract_m3u8_formats(m3u8_url, display_id),
        }


class TarangPlusPlaylistIE(TarangPlusBaseIE):
    IE_NAME = 'tarangplus:playlist'
    _VALID_URL = r'https?://(?:www\.)?tarangplus\.in/[^#?/]+/(?P<id>[^#?/]+)/episodes$'
    _TESTS = [{
        'url': 'https://tarangplus.in/tarangaplus-originals/balijatra/episodes',
        'info_dict': {
            'id': 'balijatra',
            'title': 'Balijatra',
        },
        'playlist_mincount': 7,
    }, {
        'url': 'https://tarangplus.in/tarang-serials/bada-bohu/episodes',
        'info_dict': {
            'id': 'bada-bohu',
            'title': 'Bada Bohu',
        },
        'playlist_mincount': 236,
    }, {
        'url': 'https://tarangplus.in/shows/dr-nonsense/episodes',
        'info_dict': {
            'id': 'dr-nonsense',
            'title': 'Dr. Nonsense',
        },
        'playlist_mincount': 15,
    }]
    _PAGE_SIZE = 20

    def _entries(self, playlist_url, playlist_id, page):
        data = self._download_json(playlist_url, f'{playlist_id}-{page + 1}',
                                   'Downloading JSON', 'Unable to download JSON', query={'page_no': page})
        for item in data['items']:
            url = urljoin(self._BASE_URL, item.split('$')[3])
            yield self.url_result(url, TarangPlusVideoIE)

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage('/'.join(url.split('/')[:-1]), display_id)
        title = self._hidden_inputs(webpage).get('title')
        return self.playlist_result(
            OnDemandPagedList(functools.partial(self._entries, url, display_id), self._PAGE_SIZE),
            display_id, title)


class TarangPlusSecondaryPlaylistIE(TarangPlusBaseIE):
    IE_NAME = 'tarangplus:secondaryplaylist'
    _VALID_URL = r'https?://(?:www\.)?tarangplus\.in/(?P<id>[^#?/]+)/all$'
    _TESTS = [{
        'url': 'https://tarangplus.in/chhota-jaga/all',
        'info_dict': {
            'id': 'chhota-jaga',
            'title': 'Chhota Jaga',
        },
        'playlist_mincount': 34,
    }, {
        'url': 'https://tarangplus.in/kids-yali-show/all',
        'info_dict': {
            'id': 'kids-yali-show',
            'title': 'Yali',
        },
        'playlist_mincount': 10,
    }, {
        'url': 'https://tarangplus.in/trailer/all',
        'info_dict': {
            'id': 'trailer',
            'title': 'Trailer',
        },
        'playlist_mincount': 57,
    }, {
        'url': 'https://tarangplus.in/latest-songs/all',
        'info_dict': {
            'id': 'latest-songs',
            'title': 'Latest Songs',
        },
        'playlist_mincount': 46,
    }, {
        'url': 'https://tarangplus.in/premium-serials-episodes/all',
        'info_dict': {
            'id': 'premium-serials-episodes',
            'title': 'Primetime Latest Episodes',
        },
        'playlist_mincount': 100,
    }]

    def _entries(self, webpage):
        items = get_elements_html_by_class('item', webpage)
        for item in items:
            a_elem = get_element_text_and_html_by_tag('a', item)[1]
            url = urljoin(self._BASE_URL, extract_attributes(a_elem)['href'])
            yield self.url_result(url, TarangPlusVideoIE)

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        title = get_element_by_id('al_title', webpage)
        entries = self._entries(webpage)
        return self.playlist_result(entries, display_id, title)
