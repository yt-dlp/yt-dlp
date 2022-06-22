from .dplay import DPlayIE
from ..compat import compat_urlparse
from ..utils import (
    ExtractorError,
    extract_attributes,
)


class Tele5IE(DPlayIE):
    _VALID_URL = r'https?://(?:www\.)?tele5\.de/(?:[^/]+/)*(?P<id>[^/?#&]+)'
    _GEO_COUNTRIES = ['DE']
    _TESTS = [{
        'url': 'https://www.tele5.de/mediathek/filme-online/videos?vid=1549416',
        'info_dict': {
            'id': '1549416',
            'ext': 'mp4',
            'upload_date': '20180814',
            'timestamp': 1534290623,
            'title': 'Pandorum',
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'No longer available: "404 Seite nicht gefunden"',
    }, {
        # jwplatform, nexx unavailable
        'url': 'https://www.tele5.de/filme/ghoul-das-geheimnis-des-friedhofmonsters/',
        'info_dict': {
            'id': 'WJuiOlUp',
            'ext': 'mp4',
            'upload_date': '20200603',
            'timestamp': 1591214400,
            'title': 'Ghoul - Das Geheimnis des Friedhofmonsters',
            'description': 'md5:42002af1d887ff3d5b2b3ca1f8137d97',
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'No longer available, redirects to Filme page',
    }, {
        'url': 'https://tele5.de/mediathek/angel-of-mine/',
        'info_dict': {
            'id': '1252360',
            'ext': 'mp4',
            'upload_date': '20220109',
            'timestamp': 1641762000,
            'title': 'Angel of Mine',
            'description': 'md5:a72546a175e1286eb3251843a52d1ad7',
        },
        'params': {
            'format': 'bestvideo',
        },
    }, {
        'url': 'https://www.tele5.de/kalkofes-mattscheibe/video-clips/politik-und-gesellschaft?ve_id=1551191',
        'only_matching': True,
    }, {
        'url': 'https://www.tele5.de/video-clip/?ve_id=1609440',
        'only_matching': True,
    }, {
        'url': 'https://www.tele5.de/filme/schlefaz-dragon-crusaders/',
        'only_matching': True,
    }, {
        'url': 'https://www.tele5.de/filme/making-of/avengers-endgame/',
        'only_matching': True,
    }, {
        'url': 'https://www.tele5.de/star-trek/raumschiff-voyager/ganze-folge/das-vinculum/',
        'only_matching': True,
    }, {
        'url': 'https://www.tele5.de/anders-ist-sevda/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        player_element = self._search_regex(r'(<hyoga-player\b[^>]+?>)', webpage, 'video player')
        player_info = extract_attributes(player_element)
        asset_id, country, realm = (player_info[x] for x in ('assetid', 'locale', 'realm', ))
        endpoint = compat_urlparse.urlparse(player_info['endpoint']).hostname
        source_type = player_info.get('sourcetype')
        if source_type:
            endpoint = '%s-%s' % (source_type, endpoint)
        try:
            return self._get_disco_api_info(url, asset_id, endpoint, realm, country)
        except ExtractorError as e:
            if getattr(e, 'message', '') == 'Missing deviceId in context':
                self.report_drm(video_id)
            raise
