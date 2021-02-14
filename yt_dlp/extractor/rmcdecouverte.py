# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from .brightcove import BrightcoveLegacyIE
from ..compat import (
    compat_parse_qs,
    compat_urlparse,
)
from ..utils import smuggle_url


class RMCDecouverteIE(InfoExtractor):
    _VALID_URL = r'https?://rmcdecouverte\.bfmtv\.com/(?:(?:[^/]+/)*program_(?P<id>\d+)|(?P<live_id>mediaplayer-direct))'

    _TESTS = [{
        'url': 'https://rmcdecouverte.bfmtv.com/wheeler-dealers-occasions-a-saisir/program_2566/',
        'info_dict': {
            'id': '5983675500001',
            'ext': 'mp4',
            'title': 'CORVETTE',
            'description': 'md5:c1e8295521e45ffebf635d6a7658f506',
            'uploader_id': '1969646226001',
            'upload_date': '20181226',
            'timestamp': 1545861635,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'only available for a week',
    }, {
        # live, geo restricted, bypassable
        'url': 'https://rmcdecouverte.bfmtv.com/mediaplayer-direct/',
        'only_matching': True,
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/1969646226001/default_default/index.html?videoId=%s'

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        display_id = mobj.group('id') or mobj.group('live_id')
        webpage = self._download_webpage(url, display_id)
        brightcove_legacy_url = BrightcoveLegacyIE._extract_brightcove_url(webpage)
        if brightcove_legacy_url:
            brightcove_id = compat_parse_qs(compat_urlparse.urlparse(
                brightcove_legacy_url).query)['@videoPlayer'][0]
        else:
            brightcove_id = self._search_regex(
                r'data-video-id=["\'](\d+)', webpage, 'brightcove id')
        return self.url_result(
            smuggle_url(
                self.BRIGHTCOVE_URL_TEMPLATE % brightcove_id,
                {'geo_countries': ['FR']}),
            'BrightcoveNew', brightcove_id)
