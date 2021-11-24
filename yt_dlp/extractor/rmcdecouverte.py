# coding: utf-8
from __future__ import unicode_literals


from .common import InfoExtractor
from .brightcove import BrightcoveLegacyIE
from ..compat import (
    compat_parse_qs,
    compat_urlparse,
)
from ..utils import smuggle_url


class RMCDecouverteIE(InfoExtractor):
    _VALID_URL = r'https?://rmcdecouverte\.bfmtv\.com/(?:[^?#]*_(?P<id>\d+)|mediaplayer-direct)/?(?:[#?]|$)'

    _TESTS = [{
        'url': 'https://rmcdecouverte.bfmtv.com/vestiges-de-guerre_22240/les-bunkers-secrets-domaha-beach_25303/',
        'info_dict': {
            'id': '6250879771001',
            'ext': 'mp4',
            'title': 'LES BUNKERS SECRETS D´OMAHA BEACH',
            'uploader_id': '1969646226001',
            'description': 'md5:aed573ca24abde62a148e0eba909657d',
            'timestamp': 1619622984,
            'upload_date': '20210428',
        },
        'params': {
            'skip_download': True,
        },
    }, {
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
        'url': 'https://rmcdecouverte.bfmtv.com/avions-furtifs-la-technologie-de-lextreme_10598',
        'only_matching': True,
    }, {
        # The website accepts any URL as long as it has _\d+ at the end
        'url': 'https://rmcdecouverte.bfmtv.com/any/thing/can/go/here/_10598',
        'only_matching': True,
    }, {
        # live, geo restricted, bypassable
        'url': 'https://rmcdecouverte.bfmtv.com/mediaplayer-direct/',
        'only_matching': True,
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/1969646226001/default_default/index.html?videoId=%s'

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        display_id = mobj.group('id') or 'direct'
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
