# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class UKTVPlayIE(InfoExtractor):
    _VALID_URL = r'https?://uktvplay\.uktv\.co\.uk/(?:.+?\?.*?\bvideo=|([^/]+/)*watch-online/)(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://uktvplay.uktv.co.uk/shows/world-at-war/c/200/watch-online/?video=2117008346001',
        'info_dict': {
            'id': '2117008346001',
            'ext': 'mp4',
            'title': 'Pincers',
            'description': 'Pincers',
            'uploader_id': '1242911124001',
            'upload_date': '20130124',
            'timestamp': 1359049267,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'expected_warnings': ['Failed to download MPD manifest']
    }, {
        'url': 'https://uktvplay.uktv.co.uk/shows/africa/watch-online/5983349675001',
        'only_matching': True,
    }]
    # BRIGHTCOVE_URL_TEMPLATE = 'https://players.brightcove.net/1242911124001/OrCyvJ2gyL_default/index.html?videoId=%s'
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/1242911124001/H1xnMOqP_default/index.html?videoId=%s'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result(
            self.BRIGHTCOVE_URL_TEMPLATE % video_id,
            'BrightcoveNew', video_id)
