import re

from .common import InfoExtractor
from ..utils import urlhandle_detect_ext
from ..networking import HEADRequest


class Mx3BaseIE(InfoExtractor):
    _MX3_DOMAIN = None

    def _real_extract(self, url):
        track_id = self._match_id(url)
        webpage = self._download_webpage(url, track_id)
        json = self._download_json(f'https://{self._MX3_DOMAIN}/t/{track_id}.json', track_id)

        artists = []
        if json.get('artist'):
            artists.append(json['artist'])
        performer = json.get('performer_name')
        if performer and performer not in artists:
            artists.append(performer)

        title = json['title']

        genre = self._html_search_regex(r'<div\b[^>]+class="single-band-genre"[^>]*>([^<]+)</div>',
                                        webpage, 'genre', fatal=False, flags=re.DOTALL)

        formats = []

        def add_format(fmt):
            urlh = self._request_webpage(HEADRequest(fmt['url']), track_id, note='Fetching media headers', fatal=False)
            if urlh:
                fmt['ext'] = urlhandle_detect_ext(urlh)
                formats.append(fmt)

        base_url = 'https://' + self._MX3_DOMAIN + '/'
        add_format({
            'url': base_url + json["url"],
            'format_id': 'default',
            'quality': 1,
        })

        if 'hd_url' in json:
            add_format({
                'url': base_url + json['hd_url'],
                'format_id': 'hd',
                'quality': 10,
            })

        # the "download" feature is not available everywhere
        if f'/tracks/{track_id}/download' in webpage:
            add_format({
                'url': f'{base_url}tracks/{track_id}/download',
                'format_id': 'download',
                'quality': 11,
                'format_note': 'usually uncompressed WAV',
            })

        return {
            'id': track_id,
            'formats': formats,
            'title': title,
            'artist': ', '.join(artists),
            'composer': json.get('composer_name', None),
            'genre': genre,
            'thumbnail': json.get('picture_url_xlarge') or json.get('picture_url'),
        }


class Mx3IE(Mx3BaseIE):
    _MX3_DOMAIN = 'mx3.ch'
    _VALID_URL = r'https?://(?:www\.)?mx3\.ch/t/(?P<id>[0-9A-Za-z]+)'
    _TESTS = [{
        'url': 'https://mx3.ch/t/1Cru',
        'md5': '82510bf4c21f17da41bff7e1ffd84e78',
        'info_dict': {
            'id': '1Cru',
            # This one is audio-only. It's a mp3, but we have to make a HEAD request to find out.
            'ext': 'mp3',
            'artist': 'Tortue Tortue, Godina',
            'composer': 'Olivier Godinat',
            'genre': 'Rock',
            'thumbnail': 'https://mx3.ch/pictures/mx3/file/0101/4643/square_xlarge/1-s-envoler-1.jpg?1630272813',
            'title': 'S\'envoler',
        }
    }, {
        'url': 'https://mx3.ch/t/1LIY',
        'md5': '4117489dff8c763ecfbb0b95a67d6c8e',
        'info_dict': {
            'id': '1LIY',
            # This is a music video. 'file' says: ISO Media, MP4 Base Media v1 [ISO 14496-12:2003]
            'ext': 'mp4',
            'artist': 'The Broots, Tania Kimfumu',
            'composer': 'Emmanuel Diserens',
            'genre': 'Electro',
            'thumbnail': 'https://mx3.ch/pictures/mx3/file/0110/0003/video_xlarge/frame_0000.png?1686963670',
            'title': 'The Broots-Larytta remix "Begging For Help"',
        }
    }, {
        'url': 'https://mx3.ch/t/1C6E',
        'md5': '1afcd578493ddb8e5008e94bb6d97e25',
        'info_dict': {
            'id': '1C6E',
            # This one has a download button, yielding a WAV.
            'ext': 'wav',
            'artist': 'Alien Bubblegum',
            'composer': 'Alien Bubblegum',
            'genre': 'Punk',
            'thumbnail': 'https://mx3.ch/pictures/mx3/file/0101/1551/square_xlarge/pandora-s-box-cover-with-title.png?1627054733',
            'title': 'Wide Awake',
        }
    }]


class Mx3NeoIE(Mx3BaseIE):
    _MX3_DOMAIN = 'neo.mx3.ch'
    _VALID_URL = r'https?://(?:www\.)?neo.mx3\.ch/t/(?P<id>[0-9A-Za-z]+)'
    _TESTS = [{
        'url': 'https://neo.mx3.ch/t/1hpd',
        'md5': 'ff0b2b91ce0b8931c0a358715758dc78',
        'info_dict': {
            'id': '1hpd',
            'ext': 'mp3',
            'artist': 'Kammerorchester Basel, Baptiste Lopez',
            'composer': 'Jannik Giger',
            'genre': 'Composition, Orchestra',
            'title': 'Troisième œil. Für Kammerorchester (2023)',
            'thumbnail': 'https://neo.mx3.ch/pictures/neo/file/0000/0241/square_xlarge/kammerorchester-basel-group-photo-2_c_-lukasz-rajchert.jpg?1560341252'
        }
    }]


class Mx3VolksmusikIE(Mx3BaseIE):
    _MX3_DOMAIN = 'volksmusik.mx3.ch'
    _VALID_URL = r'https?://(?:www\.)?volksmusik.mx3\.ch/t/(?P<id>[0-9A-Za-z]+)'
    _TESTS = [{
        'url': 'https://volksmusik.mx3.ch/t/Zx',
        'md5': 'dd967a7b0c1ef898f3e072cf9c2eae3c',
        'info_dict': {
            'id': 'Zx',
            'ext': 'mp3',
            'artist': 'Ländlerkapelle GrischArt',
            'composer': 'Urs Glauser',
            'genre': 'Instrumental, Graubünden',
            'title': 'Chämilouf',
            'thumbnail': 'https://volksmusik.mx3.ch/pictures/vxm/file/0000/3815/square_xlarge/grischart1.jpg?1450530120',
        }
    }]
