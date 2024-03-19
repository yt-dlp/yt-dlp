from datetime import datetime
import time
import json

from .common import InfoExtractor
from ..utils import (
    get_element_html_by_id,
    extract_attributes,
)


class FathomIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?fathom\.video/share/(?P<id>[^/?#&]+?)'
    _TESTS = [{
        'url': 'https://fathom.video/share/G9mkjkspnohVVZ_L5nrsoPycyWcB8y7s',
        'md5': '0decd5343b8f30ae268625e79a02b60f',
        'info_dict': {
            'id': '47200596',
            'ext': 'mp4',
            'title': 'eCom Inucbator - Coaching Session',
            'duration': 8125.380507,
            'timestamp': 1699036314.0,
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
            'timestamp': 1698921000.0,
            'upload_date': '20231102',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        div_app = get_element_html_by_id('app', webpage)
        attrs = extract_attributes(div_app)
        data = json.loads(attrs["data-page"])

        video_id = str(data['props']['call']['id'])
        title = data['props']['head']['title']
        duration = data['props']['duration']
        upload_date = datetime.fromisoformat(data['props']['call']['started_at'])
        timestamp = time.mktime(upload_date.timetuple())

        source_url = data['props']['call']['video_url']

        formats = self._extract_m3u8_formats(
            source_url, video_id, 'mp4', entry_protocol='m3u8_native', fatal=False)

        return {
            'id': video_id,
            'title': title,
            'duration': duration,
            'timestamp': timestamp,
            'formats': formats,
        }
