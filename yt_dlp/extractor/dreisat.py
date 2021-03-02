from __future__ import unicode_literals

from .zdf import ZDFIE


class DreiSatIE(ZDFIE):
    IE_NAME = '3sat'
    _VALID_URL = r'https?://(?:www\.)?3sat\.de/(?:[^/]+/)*(?P<id>[^/?#&]+)\.html'
    _TESTS = [{
        # Same as https://www.zdf.de/dokumentation/ab-18/10-wochen-sommer-102.html
        'url': 'https://www.3sat.de/film/ab-18/10-wochen-sommer-108.html',
        'md5': '0aff3e7bc72c8813f5e0fae333316a1d',
        'info_dict': {
            'id': '141007_ab18_10wochensommer_film',
            'ext': 'mp4',
            'title': 'Ab 18! - 10 Wochen Sommer',
            'description': 'md5:8253f41dc99ce2c3ff892dac2d65fe26',
            'duration': 2660,
            'timestamp': 1608604200,
            'upload_date': '20201222',
        },
    }, {
        'url': 'https://www.3sat.de/gesellschaft/schweizweit/waidmannsheil-100.html',
        'info_dict': {
            'id': '140913_sendung_schweizweit',
            'ext': 'mp4',
            'title': 'Waidmannsheil',
            'description': 'md5:cce00ca1d70e21425e72c86a98a56817',
            'timestamp': 1410623100,
            'upload_date': '20140913'
        },
        'params': {
            'skip_download': True,
        }
    }, {
        # Same as https://www.zdf.de/filme/filme-sonstige/der-hauptmann-112.html
        'url': 'https://www.3sat.de/film/spielfilm/der-hauptmann-100.html',
        'only_matching': True,
    }, {
        # Same as https://www.zdf.de/wissen/nano/nano-21-mai-2019-102.html, equal media ids
        'url': 'https://www.3sat.de/wissen/nano/nano-21-mai-2019-102.html',
        'only_matching': True,
    }]
