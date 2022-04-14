from .telecinco import TelecincoIE
from ..utils import (
    int_or_none,
    parse_iso8601,
)


class MiTeleIE(TelecincoIE):
    IE_DESC = 'mitele.es'
    _VALID_URL = r'https?://(?:www\.)?mitele\.es/(?:[^/]+/)+(?P<id>[^/]+)/player'

    _TESTS = [{
        'url': 'http://www.mitele.es/programas-tv/diario-de/57b0dfb9c715da65618b4afa/player',
        'info_dict': {
            'id': 'FhYW1iNTE6J6H7NkQRIEzfne6t2quqPg',
            'ext': 'mp4',
            'title': 'Diario de La redacción Programa 144',
            'description': 'md5:07c35a7b11abb05876a6a79185b58d27',
            'series': 'Diario de',
            'season': 'Season 14',
            'season_number': 14,
            'episode': 'Tor, la web invisible',
            'episode_number': 3,
            'thumbnail': r're:(?i)^https?://.*\.jpg$',
            'duration': 2913,
            'age_limit': 16,
            'timestamp': 1471209401,
            'upload_date': '20160814',
        },
    }, {
        # no explicit title
        'url': 'http://www.mitele.es/programas-tv/cuarto-milenio/57b0de3dc915da14058b4876/player',
        'info_dict': {
            'id': 'oyNG1iNTE6TAPP-JmCjbwfwJqqMMX3Vq',
            'ext': 'mp4',
            'title': 'Cuarto Milenio Temporada 6 Programa 226',
            'description': 'md5:5ff132013f0cd968ffbf1f5f3538a65f',
            'series': 'Cuarto Milenio',
            'season': 'Season 6',
            'season_number': 6,
            'episode': 'Episode 24',
            'episode_number': 24,
            'thumbnail': r're:(?i)^https?://.*\.jpg$',
            'duration': 7313,
            'age_limit': 12,
            'timestamp': 1471209021,
            'upload_date': '20160814',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.mitele.es/series-online/la-que-se-avecina/57aac5c1c915da951a8b45ed/player',
        'only_matching': True,
    }, {
        'url': 'https://www.mitele.es/programas-tv/diario-de/la-redaccion/programa-144-40_1006364575251/player/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        pre_player = self._parse_json(self._search_regex(
            r'window\.\$REACTBASE_STATE\.prePlayer_mtweb\s*=\s*({.+})',
            webpage, 'Pre Player'), display_id)['prePlayer']
        title = pre_player['title']
        video_info = self._parse_content(pre_player['video'], url)
        content = pre_player.get('content') or {}
        info = content.get('info') or {}

        video_info.update({
            'title': title,
            'description': info.get('synopsis'),
            'series': content.get('title'),
            'season_number': int_or_none(info.get('season_number')),
            'episode': content.get('subtitle'),
            'episode_number': int_or_none(info.get('episode_number')),
            'duration': int_or_none(info.get('duration')),
            'age_limit': int_or_none(info.get('rating')),
            'timestamp': parse_iso8601(pre_player.get('publishedTime')),
        })
        return video_info
