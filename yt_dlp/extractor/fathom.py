import json

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    float_or_none,
    get_element_html_by_id,
    parse_iso8601,
)
from ..utils.traversal import traverse_obj


class FathomIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?fathom\.video/share/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://fathom.video/share/G9mkjkspnohVVZ_L5nrsoPycyWcB8y7s',
        'md5': '0decd5343b8f30ae268625e79a02b60f',
        'info_dict': {
            'id': '47200596',
            'ext': 'mp4',
            'title': 'eCom Inucbator - Coaching Session',
            'duration': 8125.380507,
            'timestamp': 1699048914,
            'upload_date': '20231103',
        },
    }, {
        'url': 'https://fathom.video/share/mEws3bybftHL2QLymxYEDeE21vtLxGVm',
        'md5': '4f5cb382126c22d1aba8a939f9c49690',
        'info_dict': {
            'id': '46812957',
            'ext': 'mp4',
            'title': 'Jon, Lawrence, Neman chat about practice',
            'duration': 3571.517847,
            'timestamp': 1698933600,
            'upload_date': '20231102',
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        props = traverse_obj(
            get_element_html_by_id('app', webpage), ({extract_attributes}, 'data-page', {json.loads}, 'props'))
        video_id = str(props['call']['id'])

        return {
            'id': video_id,
            'formats': self._extract_m3u8_formats(props['call']['video_url'], video_id, 'mp4'),
            **traverse_obj(props, {
                'title': ('head', 'title', {str}),
                'duration': ('duration', {float_or_none}),
                'timestamp': ('call', 'started_at', {parse_iso8601}),
            }),
        }
