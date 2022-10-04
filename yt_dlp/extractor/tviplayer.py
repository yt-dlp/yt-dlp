from .common import InfoExtractor
from ..utils import traverse_obj


class TVIPlayerIE(InfoExtractor):
    _VALID_URL = r'https?://tviplayer\.iol\.pt(/programa/[\w-]+/[a-f0-9]+)?/\w+/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://tviplayer.iol.pt/programa/jornal-das-8/53c6b3903004dc006243d0cf/video/61c8e8b90cf2c7ea0f0f71a9',
        'info_dict': {
            'id': '61c8e8b90cf2c7ea0f0f71a9',
            'ext': 'mp4',
            'duration': 4167,
            'title': 'Jornal das 8 - 26 de dezembro de 2021',
            'thumbnail': 'https://www.iol.pt/multimedia/oratvi/multimedia/imagem/id/61c8ee630cf2cc58e7d98d9f/',
            'season_number': 8,
            'season': 'Season 8',
        }
    }, {
        'url': 'https://tviplayer.iol.pt/programa/isabel/62b471090cf26256cd2a8594/video/62be445f0cf2ea4f0a5218e5',
        'info_dict': {
            'id': '62be445f0cf2ea4f0a5218e5',
            'ext': 'mp4',
            'duration': 3255,
            'season': 'Season 1',
            'title': 'Isabel - Episódio 1',
            'thumbnail': 'https://www.iol.pt/multimedia/oratvi/multimedia/imagem/id/62beac200cf2f9a86eab856b/',
            'season_number': 1,
        }
    }, {
        # no /programa/
        'url': 'https://tviplayer.iol.pt/video/62c4131c0cf2f9a86eac06bb',
        'info_dict': {
            'id': '62c4131c0cf2f9a86eac06bb',
            'ext': 'mp4',
            'title': 'David e Mickael Carreira respondem: «Qual é o próximo a ser pai?»',
            'thumbnail': 'https://www.iol.pt/multimedia/oratvi/multimedia/imagem/id/62c416490cf2ea367d4433fd/',
            'season': 'Season 2',
            'duration': 148,
            'season_number': 2,
        }
    }, {
        # episodio url
        'url': 'https://tviplayer.iol.pt/programa/para-sempre/61716c360cf2365a5ed894c4/episodio/t1e187',
        'info_dict': {
            'id': 't1e187',
            'ext': 'mp4',
            'season': 'Season 1',
            'title': 'Quem denunciou Pedro?',
            'thumbnail': 'https://www.iol.pt/multimedia/oratvi/multimedia/imagem/id/62eda30b0cf2ea367d48973b/',
            'duration': 1250,
            'season_number': 1,
        }
    }]

    def _real_initialize(self):
        self.wms_auth_sign_token = self._download_webpage(
            'https://services.iol.pt/matrix?userId=', 'wmsAuthSign',
            note='Trying to get wmsAuthSign token')

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        json_data = self._search_json(
            r'<script>\s*jsonData\s*=\s*', webpage, 'json_data', video_id)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            f'{json_data["videoUrl"]}?wmsAuthSign={self.wms_auth_sign_token}',
            video_id, ext='mp4')
        return {
            'id': video_id,
            'title': json_data.get('title') or self._og_search_title(webpage),
            'thumbnail': json_data.get('cover') or self._og_search_thumbnail(webpage),
            'duration': json_data.get('duration'),
            'formats': formats,
            'subtitles': subtitles,
            'season_number': traverse_obj(json_data, ('program', 'seasonNum')),
        }
