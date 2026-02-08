from .zdf import ZDFBaseIE


class DreiSatIE(ZDFBaseIE):
    IE_NAME = '3sat'
    _VALID_URL = r'https?://(?:www\.)?3sat\.de/(?:[^/]+/)*(?P<id>[^/?#&]+)\.html'
    _TESTS = [{
        'url': 'https://www.3sat.de/dokumentation/reise/traumziele-suedostasiens-die-philippinen-und-vietnam-102.html',
        'info_dict': {
            'id': '231124_traumziele_philippinen_und_vietnam_dokreise',
            'ext': 'mp4',
            'title': 'Traumziele Südostasiens (1/2): Die Philippinen und Vietnam',
            'description': 'md5:26329ce5197775b596773b939354079d',
            'duration': 2625.0,
            'thumbnail': 'https://www.3sat.de/assets/traumziele-suedostasiens-die-philippinen-und-vietnam-100~2400x1350?cb=1699870351148',
            'episode': 'Traumziele Südostasiens (1/2): Die Philippinen und Vietnam',
            'episode_id': 'POS_cc7ff51c-98cf-4d12-b99d-f7a551de1c95',
            'timestamp': 1738593000,
            'upload_date': '20250203',
        },
    }, {
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
        'skip': '410 Gone',
    }, {
        'url': 'https://www.3sat.de/gesellschaft/schweizweit/waidmannsheil-100.html',
        'info_dict': {
            'id': '140913_sendung_schweizweit',
            'ext': 'mp4',
            'title': 'Waidmannsheil',
            'description': 'md5:cce00ca1d70e21425e72c86a98a56817',
            'timestamp': 1410623100,
            'upload_date': '20140913',
        },
        'params': {
            'skip_download': True,
        },
        'skip': '404 Not Found',
    }, {
        # Same as https://www.zdf.de/filme/filme-sonstige/der-hauptmann-112.html
        'url': 'https://www.3sat.de/film/spielfilm/der-hauptmann-100.html',
        'only_matching': True,
    }, {
        # Same as https://www.zdf.de/wissen/nano/nano-21-mai-2019-102.html, equal media ids
        'url': 'https://www.3sat.de/wissen/nano/nano-21-mai-2019-102.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id, fatal=False)
        if webpage:
            player = self._extract_player(webpage, url, fatal=False)
            if player:
                return self._extract_regular(url, player, video_id)

        return self._extract_mobile(video_id)
