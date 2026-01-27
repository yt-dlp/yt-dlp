import base64
import binascii
import functools
import re
import urllib.parse

from .common import InfoExtractor
from ..dependencies import Cryptodome
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    clean_html,
    extract_attributes,
    urljoin,
)
from ..utils.traversal import (
    find_element,
    find_elements,
    require,
    traverse_obj,
)


class TarangPlusBaseIE(InfoExtractor):
    _BASE_URL = 'https://tarangplus.in'


class TarangPlusVideoIE(TarangPlusBaseIE):
    IE_NAME = 'tarangplus:video'
    _VALID_URL = r'https?://(?:www\.)?tarangplus\.in/(?:movies|[^#?/]+/[^#?/]+)/(?!episodes)(?P<id>[^#?/]+)'
    _TESTS = [{
        'url': 'https://tarangplus.in/tarangaplus-originals/khitpit/khitpit-ep-10',
        'md5': '78ce056cee755687b8a48199909ecf53',
        'info_dict': {
            'id': '67b8206719521d054c0059b7',
            'display_id': 'khitpit-ep-10',
            'ext': 'mp4',
            'title': 'Khitpit Ep-10',
            'description': 'md5:a45b805cb628e15c853d78b0406eab48',
            'thumbnail': r're:https?://.+/.+\.jpg',
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
            'thumbnail': r're:https?://.+/.+\.jpg',
            'duration': 1392.0,
            'timestamp': 1745539200,
            'upload_date': '20250425',
            'media_type': 'episode',
            'categories': ['Prime'],
        },
    }, {
        # Decrypted m3u8 URL has trailing control characters that need to be stripped
        'url': 'https://tarangplus.in/tarangaplus-originals/ichha/ichha-teaser-1',
        'md5': '16ee43fe21ad8b6e652ec65eba38a64e',
        'info_dict': {
            'id': '5f0f252d3326af0720000342',
            'ext': 'mp4',
            'display_id': 'ichha-teaser-1',
            'title': 'Ichha Teaser',
            'description': 'md5:c724b0b0669a2cefdada3711cec792e6',
            'media_type': 'episode',
            'duration': 21.0,
            'thumbnail': r're:https?://.+/.+\.jpg',
            'categories': ['Originals'],
            'timestamp': 1758153600,
            'upload_date': '20250918',
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
        json_ld_data.pop('url', None)

        iframe_url = traverse_obj(webpage, (
            {find_element(tag='iframe', attr='src', value=r'.+[?&]contenturl=.+', html=True, regex=True)},
            {extract_attributes}, 'src', {require('iframe URL')}))
        # Can't use parse_qs here since it would decode the encrypted base64 `+` chars to spaces
        content = self._search_regex(r'[?&]contenturl=(.+)', iframe_url, 'content')
        encrypted_data, _, attrs = content.partition('|')
        metadata = {
            m.group('k'): m.group('v')
            for m in re.finditer(r'(?:^|\|)(?P<k>[a-z_]+)=(?P<v>(?:(?!\|[a-z_]+=).)+)', attrs)
        }
        m3u8_url = urllib.parse.unquote(
            self.decrypt(encrypted_data, metadata['key'])).rstrip('\x0e\x0f')

        return {
            'id': display_id,  # Fallback
            'display_id': display_id,
            **json_ld_data,
            **traverse_obj(metadata, {
                'id': ('content_id', {str}),
                'title': ('title', {str}),
                'thumbnail': ('image', {str}),
            }),
            **traverse_obj(hidden_inputs_data, {
                'id': ('content_id', {str}),
                'media_type': ('theme_type', {str}),
                'categories': ('genre', {str}, filter, all, filter),
            }),
            'formats': self._extract_m3u8_formats(m3u8_url, display_id),
        }


class TarangPlusEpisodesIE(TarangPlusBaseIE):
    IE_NAME = 'tarangplus:episodes'
    _VALID_URL = r'https?://(?:www\.)?tarangplus\.in/(?P<type>[^#?/]+)/(?P<id>[^#?/]+)/episodes/?(?:$|[?#])'
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
        data = self._download_json(
            playlist_url, playlist_id, f'Downloading playlist JSON page {page + 1}',
            query={'page_no': page})
        for item in traverse_obj(data, ('items', ..., {str})):
            yield self.url_result(
                urljoin(self._BASE_URL, item.split('$')[3]), TarangPlusVideoIE)

    def _real_extract(self, url):
        url_type, display_id = self._match_valid_url(url).group('type', 'id')
        series_url = f'{self._BASE_URL}/{url_type}/{display_id}'
        webpage = self._download_webpage(series_url, display_id)

        entries = OnDemandPagedList(
            functools.partial(self._entries, f'{series_url}/episodes', display_id),
            self._PAGE_SIZE)
        return self.playlist_result(
            entries, display_id, self._hidden_inputs(webpage).get('title'))


class TarangPlusPlaylistIE(TarangPlusBaseIE):
    IE_NAME = 'tarangplus:playlist'
    _VALID_URL = r'https?://(?:www\.)?tarangplus\.in/(?P<id>[^#?/]+)/all/?(?:$|[?#])'
    _TESTS = [{
        'url': 'https://tarangplus.in/chhota-jaga/all',
        'info_dict': {
            'id': 'chhota-jaga',
            'title': 'Chhota Jaga',
        },
        'playlist_mincount': 33,
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
        for url_path in traverse_obj(webpage, (
            {find_elements(cls='item')}, ...,
            {find_elements(tag='a', attr='href', value='/.+', html=True, regex=True)},
            ..., {extract_attributes}, 'href',
        )):
            yield self.url_result(urljoin(self._BASE_URL, url_path), TarangPlusVideoIE)

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        return self.playlist_result(
            self._entries(webpage), display_id,
            traverse_obj(webpage, ({find_element(id='al_title')}, {clean_html})))
