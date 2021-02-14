# coding: utf-8
from __future__ import unicode_literals

import re

from .dplay import DPlayIE


class DiscoveryNetworksDeIE(DPlayIE):
    _VALID_URL = r'https?://(?:www\.)?(?P<domain>(?:tlc|dmax)\.de|dplay\.co\.uk)/(?:programme|show|sendungen)/(?P<programme>[^/]+)/(?:video/)?(?P<alternate_id>[^/]+)'

    _TESTS = [{
        'url': 'https://www.tlc.de/programme/breaking-amish/video/die-welt-da-drauen/DCB331270001100',
        'info_dict': {
            'id': '78867',
            'ext': 'mp4',
            'title': 'Die Welt da draußen',
            'description': 'md5:61033c12b73286e409d99a41742ef608',
            'timestamp': 1554069600,
            'upload_date': '20190331',
        },
        'params': {
            'format': 'bestvideo',
            'skip_download': True,
        },
    }, {
        'url': 'https://www.dmax.de/programme/dmax-highlights/video/tuning-star-sidney-hoffmann-exklusiv-bei-dmax/191023082312316',
        'only_matching': True,
    }, {
        'url': 'https://www.dplay.co.uk/show/ghost-adventures/video/hotel-leger-103620/EHD_280313B',
        'only_matching': True,
    }, {
        'url': 'https://tlc.de/sendungen/breaking-amish/die-welt-da-drauen/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        domain, programme, alternate_id = re.match(self._VALID_URL, url).groups()
        country = 'GB' if domain == 'dplay.co.uk' else 'DE'
        realm = 'questuk' if country == 'GB' else domain.replace('.', '')
        return self._get_disco_api_info(
            url, '%s/%s' % (programme, alternate_id),
            'sonic-eu1-prod.disco-api.com', realm, country)
