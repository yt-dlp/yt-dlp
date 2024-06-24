from .common import InfoExtractor
from ..utils import js_to_json, traverse_obj


class MonsterSirenHypergryphMusicIE(InfoExtractor):
    _VALID_URL = r'https?://monster-siren\.hypergryph\.com/music/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://monster-siren.hypergryph.com/music/514562',
        'info_dict': {
            'id': '514562',
            'ext': 'wav',
            'artists': ['塞壬唱片-MSR'],
            'album': 'Flame Shadow',
            'title': 'Flame Shadow',
        },
    }]

    def _real_extract(self, url):
        audio_id = self._match_id(url)
        webpage = self._download_webpage(url, audio_id)
        json_data = self._search_json(
            r'window\.g_initialProps\s*=', webpage, 'data', audio_id, transform_source=js_to_json)

        return {
            'id': audio_id,
            'title': traverse_obj(json_data, ('player', 'songDetail', 'name')),
            'url': traverse_obj(json_data, ('player', 'songDetail', 'sourceUrl')),
            'ext': 'wav',
            'vcodec': 'none',
            'artists': traverse_obj(json_data, ('player', 'songDetail', 'artists', ...)),
            'album': traverse_obj(json_data, ('musicPlay', 'albumDetail', 'name')),
        }
