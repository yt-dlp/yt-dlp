import hashlib

from .common import InfoExtractor


class MuseScoreIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?musescore\.com/(?:user/\d+|[^/]+)(?:/scores)?/(?P<id>[^#&?]+)'
    _TESTS = [{
        'url': 'https://musescore.com/user/73797/scores/142975',
        'info_dict': {
            'id': '142975',
            'ext': 'mp3',
            'title': 'WA Mozart Marche Turque (Turkish March fingered)',
            'description': 'md5:0ca4cf6b79d7f5868a1fee74097394ab',
            'thumbnail': r're:https?://cdn\.ustatik\.com/musescore/.*\.jpg',
            'uploader': 'PapyPiano',
            'creators': ['Wolfgang Amadeus Mozart'],
        },
    }, {
        'url': 'https://musescore.com/user/36164500/scores/6837638',
        'info_dict': {
            'id': '6837638',
            'ext': 'mp3',
            'title': 'Sweet Child O\' Mine  – Guns N\' Roses sweet child',
            'description': 'md5:2cd49bd6b4e48a75a3c469d4775d5079',
            'thumbnail': r're:https?://cdn\.ustatik\.com/musescore/.*\.png',
            'uploader': 'roxbelviolin',
            'creators': ['Guns N´Roses Arr. Roxbel Violin'],
        },
    }, {
        'url': 'https://musescore.com/classicman/fur-elise',
        'info_dict': {
            'id': '33816',
            'ext': 'mp3',
            'title': 'Für Elise – Beethoven',
            'description': 'md5:e37b241c0280b33e9ac25651b815d06e',
            'thumbnail': r're:https?://cdn\.ustatik\.com/musescore/.*\.jpg',
            'uploader': 'ClassicMan',
            'creators': ['Ludwig van Beethoven (1770–1827)'],
        },
    }, {
        'url': 'https://musescore.com/minh_cuteee/scores/6555384',
        'only_matching': True,
    }]

    @staticmethod
    def _generate_auth_token(video_id):
        return hashlib.md5((video_id + 'mp30gs').encode()).hexdigest()[:4]

    def _real_extract(self, url):
        webpage = self._download_webpage(url, None)
        url = self._og_search_url(webpage) or url
        video_id = self._match_id(url)
        mp3_url = self._download_json(
            'https://musescore.com/api/jmuse', video_id,
            headers={'authorization': self._generate_auth_token(video_id)},
            query={'id': video_id, 'index': '0', 'type': 'mp3'})['info']['url']
        formats = [{
            'url': mp3_url,
            'ext': 'mp3',
            'vcodec': 'none',
        }]

        return {
            'id': video_id,
            'formats': formats,
            'title': self._og_search_title(webpage),
            'description': self._html_search_meta('description', webpage, 'description'),
            'thumbnail': self._og_search_thumbnail(webpage),
            'uploader': self._html_search_meta('musescore:author', webpage, 'uploader'),
            'creator': self._html_search_meta('musescore:composer', webpage, 'composer'),
        }
