from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import int_or_none


class StretchInternetIE(InfoExtractor):
    _VALID_URL = r'https?://portal\.stretchinternet\.com/[^/]+/(?:portal|full)\.htm\?.*?\beventId=(?P<id>\d+)'
    _TEST = {
        'url': 'https://portal.stretchinternet.com/umary/portal.htm?eventId=573272&streamType=video',
        'info_dict': {
            'id': '573272',
            'ext': 'mp4',
            'title': 'University of Mary Wrestling vs. Upper Iowa',
            'timestamp': 1575668361,
            'upload_date': '20191206',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        event = self._download_json(
            'https://api.stretchinternet.com/trinity/event/tcg/' + video_id,
            video_id)[0]

        return {
            'id': video_id,
            'title': event['title'],
            'timestamp': int_or_none(event.get('dateCreated'), 1000),
            'url': 'https://' + event['media'][0]['url'],
        }
