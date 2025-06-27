import re

from .common import InfoExtractor
from ..networking import HEADRequest
from ..utils import (
    get_element_by_class,
    int_or_none,
    try_call,
    url_or_none,
    urlhandle_detect_ext,
)
from ..utils.traversal import traverse_obj


class Mx3BaseIE(InfoExtractor):
    _VALID_URL_TMPL = r'https?://(?:www\.)?%s/t/(?P<id>\w+)'
    _FORMATS = [{
        'url': 'player_asset',
        'format_id': 'default',
        'quality': 0,
    }, {
        'url': 'player_asset?quality=hd',
        'format_id': 'hd',
        'quality': 1,
    }, {
        'url': 'download',
        'format_id': 'download',
        'quality': 2,
    }, {
        'url': 'player_asset?quality=source',
        'format_id': 'source',
        'quality': 2,
    }]

    def _extract_formats(self, track_id):
        formats = []
        for fmt in self._FORMATS:
            format_url = f'https://{self._DOMAIN}/tracks/{track_id}/{fmt["url"]}'
            urlh = self._request_webpage(
                HEADRequest(format_url), track_id, fatal=False, expected_status=404,
                note=f'Checking for format {fmt["format_id"]}')
            if urlh and urlh.status == 200:
                formats.append({
                    **fmt,
                    'url': format_url,
                    'ext': urlhandle_detect_ext(urlh),
                    'filesize': int_or_none(urlh.headers.get('Content-Length')),
                })
        return formats

    def _real_extract(self, url):
        track_id = self._match_id(url)
        webpage = self._download_webpage(url, track_id)
        more_info = get_element_by_class('single-more-info', webpage)
        data = self._download_json(f'https://{self._DOMAIN}/t/{track_id}.json', track_id, fatal=False)

        def get_info_field(name):
            return self._html_search_regex(
                rf'<dt[^>]*>\s*{name}\s*</dt>\s*<dd[^>]*>(.*?)</dd>',
                more_info, name, default=None, flags=re.DOTALL)

        return {
            'id': track_id,
            'formats': self._extract_formats(track_id),
            'genre': self._html_search_regex(
                r'<div\b[^>]+class="single-band-genre"[^>]*>([^<]+)</div>', webpage, 'genre', default=None),
            'release_year': int_or_none(get_info_field('Year of creation')),
            'description': get_info_field('Description'),
            'tags': try_call(lambda: get_info_field('Tag').split(', '), list),
            **traverse_obj(data, {
                'title': ('title', {str}),
                'artist': (('performer_name', 'artist'), {str}),
                'album_artist': ('artist', {str}),
                'composer': ('composer_name', {str}),
                'thumbnail': (('picture_url_xlarge', 'picture_url'), {url_or_none}),
            }, get_all=False),
        }


class Mx3IE(Mx3BaseIE):
    _DOMAIN = 'mx3.ch'
    _VALID_URL = Mx3BaseIE._VALID_URL_TMPL % re.escape(_DOMAIN)
    _TESTS = [{
        'url': 'https://mx3.ch/t/1Cru',
        'md5': '7ba09e9826b4447d4e1ce9d69e0e295f',
        'info_dict': {
            'id': '1Cru',
            'ext': 'wav',
            'artist': 'Godina',
            'album_artist': 'Tortue Tortue',
            'composer': 'Olivier Godinat',
            'genre': 'Rock',
            'thumbnail': 'https://mx3.ch/pictures/mx3/file/0101/4643/square_xlarge/1-s-envoler-1.jpg?1630272813',
            'title': "S'envoler",
            'release_year': 2021,
            'tags': [],
        },
    }, {
        'url': 'https://mx3.ch/t/1LIY',
        'md5': '48293cb908342547827f963a5a2e9118',
        'info_dict': {
            'id': '1LIY',
            'ext': 'mov',
            'artist': 'Tania Kimfumu',
            'album_artist': 'The Broots',
            'composer': 'Emmanuel Diserens',
            'genre': 'Electro',
            'thumbnail': 'https://mx3.ch/pictures/mx3/file/0110/0003/video_xlarge/frame_0000.png?1686963670',
            'title': 'The Broots-Larytta remix "Begging For Help"',
            'release_year': 2023,
            'tags': ['the broots', 'cassata records', 'larytta'],
            'description': '"Begging for Help" Larytta Remix Official Video\nRealized By Kali Donkilie in 2023',
        },
    }, {
        'url': 'https://mx3.ch/t/1C6E',
        'md5': '1afcd578493ddb8e5008e94bb6d97e25',
        'info_dict': {
            'id': '1C6E',
            'ext': 'wav',
            'artist': 'Alien Bubblegum',
            'album_artist': 'Alien Bubblegum',
            'composer': 'Alien Bubblegum',
            'genre': 'Punk',
            'thumbnail': 'https://mx3.ch/pictures/mx3/file/0101/1551/square_xlarge/pandora-s-box-cover-with-title.png?1627054733',
            'title': 'Wide Awake',
            'release_year': 2021,
            'tags': ['alien bubblegum', 'bubblegum', 'alien', 'pop punk', 'poppunk'],
        },
    }]


class Mx3NeoIE(Mx3BaseIE):
    _DOMAIN = 'neo.mx3.ch'
    _VALID_URL = Mx3BaseIE._VALID_URL_TMPL % re.escape(_DOMAIN)
    _TESTS = [{
        'url': 'https://neo.mx3.ch/t/1hpd',
        'md5': '6d9986bbae5cac3296ec8813bf965eb2',
        'info_dict': {
            'id': '1hpd',
            'ext': 'wav',
            'artist': 'Baptiste Lopez',
            'album_artist': 'Kammerorchester Basel',
            'composer': 'Jannik Giger',
            'genre': 'Composition, Orchestra',
            'title': 'Troisième œil. Für Kammerorchester (2023)',
            'thumbnail': 'https://neo.mx3.ch/pictures/neo/file/0000/0241/square_xlarge/kammerorchester-basel-group-photo-2_c_-lukasz-rajchert.jpg?1560341252',
            'release_year': 2023,
            'tags': [],
        },
    }]


class Mx3VolksmusikIE(Mx3BaseIE):
    _DOMAIN = 'volksmusik.mx3.ch'
    _VALID_URL = Mx3BaseIE._VALID_URL_TMPL % re.escape(_DOMAIN)
    _TESTS = [{
        'url': 'https://volksmusik.mx3.ch/t/Zx',
        'md5': 'dd967a7b0c1ef898f3e072cf9c2eae3c',
        'info_dict': {
            'id': 'Zx',
            'ext': 'mp3',
            'artist': 'Ländlerkapelle GrischArt',
            'album_artist': 'Ländlerkapelle GrischArt',
            'composer': 'Urs Glauser',
            'genre': 'Instrumental, Graubünden',
            'title': 'Chämilouf',
            'thumbnail': 'https://volksmusik.mx3.ch/pictures/vxm/file/0000/3815/square_xlarge/grischart1.jpg?1450530120',
            'release_year': 2012,
            'tags': [],
        },
    }]
