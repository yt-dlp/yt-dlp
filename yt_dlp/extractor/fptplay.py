# coding: utf-8
from __future__ import unicode_literals

import hashlib
import time
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    join_nonempty,
)


class FptplayIE(InfoExtractor):
    _VALID_URL = r'https?://fptplay\.vn/(?P<type>xem-video)/[^/]+\-(?P<id>\w+)(?:/tap-(?P<episode>[^/]+)?/?(?:[?#]|$)|)'
    _GEO_COUNTRIES = ['VN']
    IE_NAME = 'fptplay'
    IE_DESC = 'fptplay.vn'
    _TESTS = [{
        'url': 'https://fptplay.vn/xem-video/nhan-duyen-dai-nhan-xin-dung-buoc-621a123016f369ebbde55945',
        'md5': 'ca0ee9bc63446c0c3e9a90186f7d6b33',
        'info_dict': {
            'id': '621a123016f369ebbde55945',
            'ext': 'mp4',
            'title': 'Nhân Duyên Đại Nhân Xin Dừng Bước - Ms. Cupid In Love',
            'description': 'md5:23cf7d1ce0ade8e21e76ae482e6a8c6c',
        },
    }, {
        'url': 'https://fptplay.vn/xem-video/ma-toi-la-dai-gia-61f3aa8a6b3b1d2e73c60eb5/tap-3',
        'md5': 'b35be968c909b3e4e1e20ca45dd261b1',
        'info_dict': {
            'id': '61f3aa8a6b3b1d2e73c60eb5',
            'ext': 'mp4',
            'title': 'Má Tôi Là Đại Gia - 3',
            'description': 'md5:ff8ba62fb6e98ef8875c42edff641d1c',
        },
    }, {
        'url': 'https://fptplay.vn/xem-video/nha-co-chuyen-hi-alls-well-ends-well-1997-6218995f6af792ee370459f0',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        type_url, video_id, episode = self._match_valid_url(url).group('type', 'id', 'episode')
        webpage = self._download_webpage(url, video_id=video_id, fatal=False)
        info = self._download_json(self.get_api_with_st_token(video_id, episode or 0), video_id)
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(info['data']['url'], video_id, 'mp4')
        self._sort_formats(formats)
        return {
            'id': video_id,
            'title': join_nonempty(
                self._html_search_meta(('og:title', 'twitter:title'), webpage), episode, delim=' - '),
            'description': self._html_search_meta(['og:description', 'twitter:description'], webpage),
            'formats': formats,
            'subtitles': subtitles,
        }

    def get_api_with_st_token(self, video_id, episode):
        path = f'/api/v6.2_w/stream/vod/{video_id}/{episode}/auto_vip'
        timestamp = int(time.time()) + 10800

        t = hashlib.md5(f'WEBv6Dkdsad90dasdjlALDDDS{timestamp}{path}'.encode()).hexdigest().upper()
        r = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
        n = [int(f'0x{t[2 * o: 2 * o + 2]}', 16) for o in range(len(t) // 2)]

        def convert(e):
            t = ''
            n = 0
            i = [0, 0, 0]
            a = [0, 0, 0, 0]
            s = len(e)
            c = 0
            for z in range(s, 0, -1):
                if n <= 3:
                    i[n] = e[c]
                n += 1
                c += 1
                if 3 == n:
                    a[0] = (252 & i[0]) >> 2
                    a[1] = ((3 & i[0]) << 4) + ((240 & i[1]) >> 4)
                    a[2] = ((15 & i[1]) << 2) + ((192 & i[2]) >> 6)
                    a[3] = (63 & i[2])
                    for v in range(4):
                        t += r[a[v]]
                    n = 0
            if n:
                for o in range(n, 3):
                    i[o] = 0

                for o in range(n + 1):
                    a[0] = (252 & i[0]) >> 2
                    a[1] = ((3 & i[0]) << 4) + ((240 & i[1]) >> 4)
                    a[2] = ((15 & i[1]) << 2) + ((192 & i[2]) >> 6)
                    a[3] = (63 & i[2])
                    t += r[a[o]]
                n += 1
                while n < 3:
                    t += ''
                    n += 1
            return t

        st_token = convert(n).replace('+', '-').replace('/', '_').replace('=', '')
        return f'https://api.fptplay.net{path}?{urllib.parse.urlencode({"st": st_token, "e": timestamp})}'
