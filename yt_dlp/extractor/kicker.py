from .common import InfoExtractor
from .dailymotion import DailymotionIE
from ..utils import (
    extract_attributes,
    get_element_html_by_class,
    get_element_by_id,
    get_elements_html_by_attribute,
    get_elements_by_attribute,
    get_element_html_by_attribute
)


class KickerIE(InfoExtractor):
    _VALID_URL = r'https://www.kicker.de/(?P<video_slug>[\w-]+)/video'
    _TESTS = {
        'url': 'https://www.kicker.de/pogba-dembel-co-die-top-11-der-abloesefreien-spieler-905049/video',
        # 'info_dict': {
            # 'id': '',
            # 'title': '',
        # }
    }
    
    def _real_extract(self, url):
        video_slug = self._match_valid_url(url).group('video_slug')
        
        webpage = self._download_webpage(url, video_slug)
        dailymotion_video_id = self._search_regex(
            r'data-dmprivateid=\"(?P<video_id>\w+)\"', webpage, 
            'video_id', group = 'video_id')
        
        return {
            '_type': 'url_transparent',
            'ie': DailymotionIE.ie_key(),
            'url': f'https://www.dailymotion.com/video/{dailymotion_video_id}'
        }