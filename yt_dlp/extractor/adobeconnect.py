# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import (
    compat_parse_qs,
    compat_urlparse,
)


class AdobeConnectIE(InfoExtractor):
    _VALID_URL = r'https?://\w+\.adobeconnect\.com/(?P<id>[\w-]+)'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        title = self._html_search_regex(r'<title>(.+?)</title>', webpage, 'title')
        qs = compat_parse_qs(self._search_regex(r"swfUrl\s*=\s*'([^']+)'", webpage, 'swf url').split('?')[1])
        is_live = qs.get('isLive', ['false'])[0] == 'true'
        formats = []
        for con_string in qs['conStrings'][0].split(','):
            formats.append({
                'format_id': con_string.split('://')[0],
                'app': compat_urlparse.quote('?' + con_string.split('?')[1] + 'flvplayerapp/' + qs['appInstance'][0]),
                'ext': 'flv',
                'play_path': 'mp4:' + qs['streamName'][0],
                'rtmp_conn': 'S:' + qs['ticket'][0],
                'rtmp_live': is_live,
                'url': con_string,
            })

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'is_live': is_live,
        }
