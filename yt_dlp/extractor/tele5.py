from .dplay import DPlayIE
from ..compat import compat_urlparse
from ..utils import (
    ExtractorError,
    extract_attributes,
    try_get,
    RegexNotFoundError
)


class Tele5IE(DPlayIE):  # XXX: Do not subclass from concrete IE
    _WORKING = False
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
    
        # Improved regex to handle different variations of <hyoga-player> tag
        player_element_regex = r'(<hyoga-player\b[^>]*?>)'
        player_element = self._search_regex(player_element_regex, webpage, 'video player', default=None)
    
        if not player_element:
            raise RegexNotFoundError('Could not find <hyoga-player> element. The page layout might have changed.')
    
        player_info = extract_attributes(player_element)
        asset_id = player_info.get('assetid')
        country = player_info.get('locale', 'DE')
        realm = player_info.get('realm')
        endpoint = try_get(player_info, lambda x: compat_urlparse.urlparse(x['endpoint']).hostname, str)
    
        # Adjust source type handling if available
        source_type = player_info.get('sourcetype')
        if source_type:
            endpoint = f'{source_type}-{endpoint}'
    
        if not all([asset_id, endpoint, realm]):
            raise ExtractorError('Necessary information missing from <hyoga-player> attributes')

        try:
            return self._get_disco_api_info(url, asset_id, endpoint, realm, country)
        except ExtractorError as e:
            if 'Missing deviceId in context' in getattr(e, 'message', ''):
                self.report_drm(video_id)
            raise
