from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import (
    compat_urlparse,
)


class RtmpIE(InfoExtractor):
    IE_DESC = False  # Do not list
    _VALID_URL = r'(?i)rtmp[est]?://.+'

    _TESTS = [{
        'url': 'rtmp://cp44293.edgefcs.net/ondemand?auth=daEcTdydfdqcsb8cZcDbAaCbhamacbbawaS-bw7dBb-bWG-GqpGFqCpNCnGoyL&aifp=v001&slist=public/unsecure/audio/2c97899446428e4301471a8cb72b4b97--audio--pmg-20110908-0900a_flv_aac_med_int.mp4',
        'only_matching': True,
    }, {
        'url': 'rtmp://edge.live.hitbox.tv/live/dimak',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._generic_id(url)
        title = self._generic_title(url)
        return {
            'id': video_id,
            'title': title,
            'formats': [{
                'url': url,
                'ext': 'flv',
                'format_id': compat_urlparse.urlparse(url).scheme,
            }],
        }


class MmsIE(InfoExtractor):
    IE_DESC = False  # Do not list
    _VALID_URL = r'(?i)mms://.+'

    _TEST = {
        # Direct MMS link
        'url': 'mms://kentro.kaist.ac.kr/200907/MilesReid(0709).wmv',
        'info_dict': {
            'id': 'MilesReid(0709)',
            'ext': 'wmv',
            'title': 'MilesReid(0709)',
        },
        'params': {
            'skip_download': True,  # rtsp downloads, requiring mplayer or mpv
        },
    }

    def _real_extract(self, url):
        video_id = self._generic_id(url)
        title = self._generic_title(url)

        return {
            'id': video_id,
            'title': title,
            'url': url,
        }
