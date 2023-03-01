from .common import InfoExtractor
from .jwplatform import JWPlatformIE


class ElEspectadorIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?elespectador\.com/(?P<id>(?:[^/]+/)?[^?#/&]+)'
    _TESTS = [{
        'url': 'https://www.elespectador.com/colombia/video-asi-se-evito-la-fuga-de-john-poulos-presunto-feminicida-de-valentina-trespalacios-explicacion/',
        'md5': '8bfd19412a2ef99beda12a3139689f87',
        'info_dict': {
            'id': 'QD3gsexj',
            'ext': 'mp4',
            'title': 'Así se evitó la fuga de John Poulos, presunto feminicida de Valentina Trespalacios',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/QD3gsexj/poster.jpg?width=720',
            'timestamp': 1674862986,
            'duration': 263.0,
            'description': 'md5:128fd74591c4e1fc2da598c5cb6f5ce4',
            'upload_date': '20230127',
        }
    }, {
        'url': 'https://www.elespectador.com/entretenimiento/musica/cony-camelo-llega-con-su-sonido-electroacustico-a-sessions/',
        'md5': '0a5f5e9f5fd47b52f89d038607cbb79d',
        'info_dict': {
            'id': 'PiB3ehkT',
            'ext': 'mp4',
            'title': 'Cony Camelo llega con su sonido electroacústico a Sessions | El Espectador',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/PiB3ehkT/poster.jpg?width=720',
            'timestamp': 1649376000,
            'duration': 1181.0,
            'description': 'md5:349e87960986d9086a6d5aeb345061cf',
            'upload_date': '20220408',
        }
    }]

    def _real_extract(self, url):
        display_id = self._match_valid_url(url)
        webpage = self._download_webpage(url, display_id)
        video_id = self._html_search_regex(r'<iframe[^>]+src\s*=\s*\\["\']https?://(?:content\.jwplatform|cdn\.jwplayer)\.com/players/(?P<id>([a-zA-Z0-9]{8}))', webpage, 'video_id')
        return self.url_result(f'jwplatform:{video_id}', JWPlatformIE, video_id)
