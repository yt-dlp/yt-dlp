from .common import InfoExtractor
from ..utils import (
    int_or_none,
    js_to_json,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class TVIPlayerIE(InfoExtractor):
    _VALID_URL = r'https?://tviplayer\.iol\.pt(?:/programa/[\w-]+/[a-f0-9]+)?/\w+/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://tviplayer.iol.pt/programa/jornal-das-8/53c6b3903004dc006243d0cf/video/61c8e8b90cf2c7ea0f0f71a9',
        'info_dict': {
            'id': '61c8e8b90cf2c7ea0f0f71a9',
            'ext': 'mp4',
            'duration': 4167,
            'title': 'Jornal das 8 - 26 de dezembro de 2021',
            'thumbnail': 'https://img.iol.pt/image/id/61c8ee630cf2cc58e7d98d9f/',
        },
    }, {
        'url': 'https://tviplayer.iol.pt/programa/isabel/62b471090cf26256cd2a8594/video/62be445f0cf2ea4f0a5218e5',
        'info_dict': {
            'id': '62be445f0cf2ea4f0a5218e5',
            'ext': 'mp4',
            'duration': 3255,
            'title': 'Isabel - Episódio 1',
            'thumbnail': 'https://www.iol.pt/multimedia/oratvi/multimedia/imagem/id/62beac200cf2f9a86eab856b/',
        },
        'skip': 'URL dead',
    }, {
        # no /programa/
        'url': 'https://tviplayer.iol.pt/video/62c4131c0cf2f9a86eac06bb',
        'info_dict': {
            'id': '62c4131c0cf2f9a86eac06bb',
            'ext': 'mp4',
            'title': 'David e Mickael Carreira respondem: «Qual é o próximo a ser pai?»',
            'thumbnail': 'https://img.iol.pt/image/id/62c416490cf2ea367d4433fd/',
            'duration': 148,
        },
    }, {
        # episodio url
        'url': 'https://tviplayer.iol.pt/programa/para-sempre/61716c360cf2365a5ed894c4/episodio/t1e187',
        'info_dict': {
            'id': 't1e187',
            'ext': 'mp4',
            'title': 'Quem denunciou Pedro?',
            'thumbnail': 'https://img.iol.pt/image/id/62eda30b0cf2ea367d48973b/',
            'duration': 1250,
        },
    }, {
        'url': 'https://tviplayer.iol.pt/programa/a-protegida/67a63479d34ef72ee441fa79/episodio/t1e120',
        'info_dict': {
            'id': 't1e120',
            'ext': 'mp4',
            'duration': 1593,
            'title': 'A Protegida - Clarice descobre o que une Óscar a Gonçalo e Mónica',
            'thumbnail': 'https://img.iol.pt/image/id/68971037d34ef72ee44941a6/',
        },
    }]

    def _real_initialize(self):
        self.wms_auth_sign_token = self._download_webpage(
            'https://services.iol.pt/matrix?userId=', 'wmsAuthSign',
            note='Trying to get wmsAuthSign token')

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        json_data = self._search_json(
            r'(?<!-)\bvideo\s*:\s*\[',
            webpage, 'json_data', video_id, transform_source=js_to_json)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            json_data['videoUrl'], video_id, 'mp4', query={
                'wmsAuthSign': self.wms_auth_sign_token,
            })

        return {
            'id': video_id,
            'title': traverse_obj(json_data, ('title', {str})) or self._og_search_title(webpage),
            'thumbnail': traverse_obj(json_data, (
                ('cover', 'thumbnail'), {url_or_none}, any)) or self._og_search_thumbnail(webpage),
            'duration': traverse_obj(json_data, ('duration', {int_or_none})),
            'formats': formats,
            'subtitles': subtitles,
        }
