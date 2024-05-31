from .common import InfoExtractor
from ..utils import (
    clean_html,
    get_element_by_class,
    js_to_json,
)


class TVNoeIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'https?://(?:www\.)?tvnoe\.cz/video/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'http://www.tvnoe.cz/video/10362',
        'md5': 'aee983f279aab96ec45ab6e2abb3c2ca',
        'info_dict': {
            'id': '10362',
            'ext': 'mp4',
            'series': 'Noční univerzita',
            'title': 'prof. Tomáš Halík, Th.D. - Návrat náboženství a střet civilizací',
            'description': 'md5:f337bae384e1a531a52c55ebc50fff41',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        iframe_url = self._search_regex(
            r'<iframe[^>]+src="([^"]+)"', webpage, 'iframe URL')

        ifs_page = self._download_webpage(iframe_url, video_id)
        jwplayer_data = self._find_jwplayer_data(
            ifs_page, video_id, transform_source=js_to_json)
        info_dict = self._parse_jwplayer_data(
            jwplayer_data, video_id, require_title=False, base_url=iframe_url)

        info_dict.update({
            'id': video_id,
            'title': clean_html(get_element_by_class(
                'field-name-field-podnazev', webpage)),
            'description': clean_html(get_element_by_class(
                'field-name-body', webpage)),
            'series': clean_html(get_element_by_class('title', webpage))
        })

        return info_dict
