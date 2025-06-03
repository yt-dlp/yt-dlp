from .common import InfoExtractor
from ..utils import js_to_json, traverse_obj


class MonsterSirenHypergryphMusicIE(InfoExtractor):
    _VALID_URL = r'https?://monster-siren\.hypergryph\.com/music/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://monster-siren.hypergryph.com/music/779464',
        'info_dict': {
            'id': '779464',
            'ext': 'wav',
            'artists': ['塞壬唱片-MSR'],
            'title': '无机物',
        },
    }]

    def _real_extract(self, url):
        audio_id = self._match_id(url)
        json_data = self._download_json(f'https://monster-siren.hypergryph.com/api/song/{audio_id}', audio_id)

        return {
            'id': audio_id,
            'title': json_data['data']['name'],
            'url': json_data['data']['sourceUrl'],
            'ext': 'wav',
            'vcodec': 'none',
            'artists': json_data['data']['artists'],
        }
