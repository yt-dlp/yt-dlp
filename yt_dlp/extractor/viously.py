from .common import InfoExtractor
from ..utils import (
    get_element_html_by_class,
    get_elements_html_by_class,
)


class ViouslyIE(InfoExtractor):
    _VALID_URL = False
    _API_URL = 'https://www.viously.com/video/hls/{0:}/index.m3u8'
    _WEBPAGE_TESTS = [{
        'url': 'http://www.turbo.fr/videos-voiture/454443-turbo-du-07-09-2014-renault-twingo-3-bentley-continental-gt-speed-ces-guide-achat-dacia.html',
        'md5': '37a6c3381599381ff53a7e1e0575c0bc',
        'info_dict': {
            'id': 'F_xQzS2jwb3',
            'ext': 'mp4',
            'title': 'Turbo du 07/09/2014 : Renault Twingo 3, Bentley Continental GT Speed, CES, Guide Achat Dacia...',
            'description': 'Turbo du 07/09/2014 : Renault Twingo 3, Bentley Continental GT Speed, CES, Guide Achat Dacia...',
            'age_limit': 0,
            'upload_date': str,
            'timestamp': float,
        }
    }]

    def _extract_from_webpage(self, url, webpage):
        has_vously_player = get_element_html_by_class('viously-player', webpage) or get_element_html_by_class('vsly-player', webpage)
        if not has_vously_player:
            return
        viously_players = get_elements_html_by_class('viously-player', webpage) + get_elements_html_by_class('vsly-player', webpage)
        for viously_player in viously_players:
            video_id = self._html_search_regex(r'id="([-_\w]+)"', viously_player, 'video_id')
            title = self._html_extract_title(webpage)
            yield {
                'id': video_id,
                'title': title,
                'description': title,
                'formats': self._extract_m3u8_formats(self._API_URL.format(video_id), video_id),
            }
