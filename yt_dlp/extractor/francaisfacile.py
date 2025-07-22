import urllib.parse

from .common import InfoExtractor
from ..utils import (
    float_or_none,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class FrancaisFacileIE(InfoExtractor):
    _VALID_URL = r'https?://francaisfacile\.rfi\.fr/[a-z]{2}/(?:actualit%C3%A9|podcasts/[^/#?]+)/(?P<id>[^/#?]+)'
    _TESTS = [{
        'url': 'https://francaisfacile.rfi.fr/fr/actualit%C3%A9/20250305-r%C3%A9concilier-les-jeunes-avec-la-lecture-gr%C3%A2ce-aux-r%C3%A9seaux-sociaux',
        'md5': '4f33674cb205744345cc835991100afa',
        'info_dict': {
            'id': 'WBMZ58952-FLE-FR-20250305',
            'display_id': '20250305-réconcilier-les-jeunes-avec-la-lecture-grâce-aux-réseaux-sociaux',
            'title': 'Réconcilier les jeunes avec la lecture grâce aux réseaux sociaux',
            'url': 'https://aod-fle.akamaized.net/fle/sounds/fr/2025/03/05/6b6af52a-f9ba-11ef-a1f8-005056a97652.mp3',
            'ext': 'mp3',
            'description': 'md5:b903c63d8585bd59e8cc4d5f80c4272d',
            'duration': 103.15,
            'timestamp': 1741177984,
            'upload_date': '20250305',
        },
    }, {
        'url': 'https://francaisfacile.rfi.fr/fr/actualit%C3%A9/20250307-argentine-le-sac-d-un-alpiniste-retrouv%C3%A9-40-ans-apr%C3%A8s-sa-mort',
        'md5': 'b8c3a63652d4ae8e8092dda5700c1cd9',
        'info_dict': {
            'id': 'WBMZ59102-FLE-FR-20250307',
            'display_id': '20250307-argentine-le-sac-d-un-alpiniste-retrouvé-40-ans-après-sa-mort',
            'title': 'Argentine: le sac d\'un alpiniste retrouvé 40 ans après sa mort',
            'url': 'https://aod-fle.akamaized.net/fle/sounds/fr/2025/03/07/8edf4082-fb46-11ef-8a37-005056bf762b.mp3',
            'ext': 'mp3',
            'description': 'md5:7fd088fbdf4a943bb68cf82462160dca',
            'duration': 117.74,
            'timestamp': 1741352789,
            'upload_date': '20250307',
        },
    }, {
        'url': 'https://francaisfacile.rfi.fr/fr/podcasts/un-mot-une-histoire/20250317-le-mot-de-david-foenkinos-peut-%C3%AAtre',
        'md5': 'db83c2cc2589b4c24571c6b6cf14f5f1',
        'info_dict': {
            'id': 'WBMZ59441-FLE-FR-20250317',
            'display_id': '20250317-le-mot-de-david-foenkinos-peut-être',
            'title': 'Le mot de David Foenkinos: «peut-être» - Un mot, une histoire',
            'url': 'https://aod-fle.akamaized.net/fle/sounds/fr/2025/03/17/4ca6cbbe-0315-11f0-a85b-005056a97652.mp3',
            'ext': 'mp3',
            'description': 'md5:3fe35fae035803df696bfa7af2496e49',
            'duration': 198.96,
            'timestamp': 1742210897,
            'upload_date': '20250317',
        },
    }]

    def _real_extract(self, url):
        display_id = urllib.parse.unquote(self._match_id(url))
        webpage = self._download_webpage(url, display_id)

        data = self._search_json(
            r'<script[^>]+\bdata-media-id=[^>]+\btype="application/json"[^>]*>',
            webpage, 'audio data', display_id)

        return {
            'id': data['mediaId'],
            'display_id': display_id,
            'vcodec': 'none',
            'title': self._html_extract_title(webpage),
            **self._search_json_ld(webpage, display_id, fatal=False),
            **traverse_obj(data, {
                'title': ('title', {str}),
                'url': ('sources', ..., 'url', {url_or_none}, any),
                'duration': ('sources', ..., 'duration', {float_or_none}, any),
            }),
        }
