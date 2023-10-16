from .brightcove import BrightcoveNewIE
from .common import InfoExtractor
from ..utils import (
    clean_html,
    get_element_by_class,
    get_element_by_id,
)


class GameInformerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?gameinformer\.com/(?:[^/]+/)*(?P<id>[^.?&#]+)'
    _TESTS = [{
        # normal Brightcove embed code extracted with BrightcoveNewIE._extract_url
        'url': 'http://www.gameinformer.com/b/features/archive/2015/09/26/replay-animal-crossing.aspx',
        'md5': '292f26da1ab4beb4c9099f1304d2b071',
        'info_dict': {
            'id': '4515472681001',
            'ext': 'mp4',
            'title': 'Replay - Animal Crossing',
            'description': 'md5:2e211891b215c85d061adc7a4dd2d930',
            'timestamp': 1443457610,
            'upload_date': '20150928',
            'uploader_id': '694940074001',
        },
    }, {
        # Brightcove id inside unique element with field--name-field-brightcove-video-id class
        'url': 'https://www.gameinformer.com/video-feature/new-gameplay-today/2019/07/09/new-gameplay-today-streets-of-rogue',
        'info_dict': {
            'id': '6057111913001',
            'ext': 'mp4',
            'title': 'New Gameplay Today – Streets Of Rogue',
            'timestamp': 1562699001,
            'upload_date': '20190709',
            'uploader_id': '694940074001',

        },
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/694940074001/default_default/index.html?videoId=%s'

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(
            url, display_id, headers=self.geo_verification_headers())
        brightcove_id = clean_html(get_element_by_class('field--name-field-brightcove-video-id', webpage) or get_element_by_id('video-source-content', webpage))
        brightcove_url = self.BRIGHTCOVE_URL_TEMPLATE % brightcove_id if brightcove_id else BrightcoveNewIE._extract_url(self, webpage)
        return self.url_result(brightcove_url, 'BrightcoveNew', brightcove_id)
