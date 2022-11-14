from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    float_or_none,
    try_get,
)


class AliExpressLiveIE(InfoExtractor):
    _VALID_URL = r'https?://live\.aliexpress\.com/live/(?P<id>\d+)'
    _TEST = {
        'url': 'https://live.aliexpress.com/live/2800002704436634',
        'md5': 'e729e25d47c5e557f2630eaf99b740a5',
        'info_dict': {
            'id': '2800002704436634',
            'ext': 'mp4',
            'title': 'CASIMA7.22',
            'thumbnail': r're:https?://.*\.jpg',
            'uploader': 'CASIMA Official Store',
            'timestamp': 1500717600,
            'upload_date': '20170722',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        data = self._parse_json(
            self._search_regex(
                r'(?s)runParams\s*=\s*({.+?})\s*;?\s*var',
                webpage, 'runParams'),
            video_id)

        title = data['title']

        formats = self._extract_m3u8_formats(
            data['replyStreamUrl'], video_id, 'mp4',
            entry_protocol='m3u8_native', m3u8_id='hls')

        return {
            'id': video_id,
            'title': title,
            'thumbnail': data.get('coverUrl'),
            'uploader': try_get(
                data, lambda x: x['followBar']['name'], compat_str),
            'timestamp': float_or_none(data.get('startTimeLong'), scale=1000),
            'formats': formats,
        }
