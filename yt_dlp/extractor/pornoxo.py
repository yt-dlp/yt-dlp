from .common import InfoExtractor
from ..utils import (
    str_to_int,
)


class PornoXOIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'https?://(?:www\.)?pornoxo\.com/videos/(?P<id>\d+)/(?P<display_id>[^/]+)\.html'
    _TEST = {
        'url': 'http://www.pornoxo.com/videos/7564/striptease-from-sexy-secretary.html',
        'md5': '582f28ecbaa9e6e24cb90f50f524ce87',
        'info_dict': {
            'id': '7564',
            'ext': 'flv',
            'title': 'Striptease From Sexy Secretary!',
            'display_id': 'striptease-from-sexy-secretary',
            'description': 'md5:0ee35252b685b3883f4a1d38332f9980',
            'categories': list,  # NSFW
            'thumbnail': r're:https?://.*\.jpg$',
            'age_limit': 18,
        }
    }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id, display_id = mobj.groups()

        webpage = self._download_webpage(url, video_id)
        video_data = self._extract_jwplayer_data(webpage, video_id, require_title=False)

        title = self._html_search_regex(
            r'<title>([^<]+)\s*-\s*PornoXO', webpage, 'title')

        view_count = str_to_int(self._html_search_regex(
            r'[vV]iews:\s*([0-9,]+)', webpage, 'view count', fatal=False))

        categories_str = self._html_search_regex(
            r'<meta name="description" content=".*featuring\s*([^"]+)"',
            webpage, 'categories', fatal=False)
        categories = (
            None if categories_str is None
            else categories_str.split(','))

        video_data.update({
            'id': video_id,
            'title': title,
            'display_id': display_id,
            'description': self._html_search_meta('description', webpage),
            'categories': categories,
            'view_count': view_count,
            'age_limit': 18,
        })

        return video_data
