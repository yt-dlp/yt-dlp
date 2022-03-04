# coding: utf-8
from __future__ import unicode_literals

import hashlib
import time
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    traverse_obj,
    ExtractorError,
    int_or_none,
)


class FptplayIE(InfoExtractor):
    _VALID_URL = r'https?://fptplay\.vn/(?P<type>(?:xem-video))/(?P<slug>.*?)(?:\/(?P<episode>.*?)(?:\/|$)|$)'
    _TESTS = [{
        'url': 'https://fptplay.vn/xem-video/nhan-duyen-dai-nhan-xin-dung-buoc-621a123016f369ebbde55945',
        'info_dict': {
            'id': '621a123016f369ebbde55945',
            'ext': 'mp4',
            'title': 'Nhân Duyên Đại Nhân Xin Dừng Bước - Ms. Cupid In Love - tap-1',
            'description': '23cf7d1ce0ade8e21e76ae482e6a8c6c',
        },
    }, {
        'url': 'https://fptplay.vn/xem-video/ma-toi-la-dai-gia-61f3aa8a6b3b1d2e73c60eb5/tap-3',
        'only_matching': True,
    }, {
        'url': 'https://fptplay.vn/xem-video/nha-co-chuyen-hi-alls-well-ends-well-1997-6218995f6af792ee370459f0',
        'only_matching': True,
    }]
    _GEO_COUNTRIES = ['VN']
    IE_NAME = 'fptplay'
    IE_DESC = 'fptplay.vn'

    def _real_extract(self, url):
        type_url, slug, episode = self._match_valid_url(url).group('type', 'slug', 'episode')
        if episode and int_or_none(episode.split('-')[-1]):
            ep = int(int_or_none(episode.split('-')[-1]))
        else:
            ep = 0

        video_id = slug.split('-')[-1]

        webpage = self._download_webpage(url, video_id=video_id)

        api = self.get_api_with_st_token(video_id, ep)

        info = self._download_json(api, video_id=video_id)

        url_m3u8 = traverse_obj(info, ('data', 'url'))

        if not url_m3u8:
            raise ExtractorError('Can not extract data.')

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(url_m3u8, video_id, 'mp4', fatal=False)

        return {
            'id': video_id,
            'title': f"{self._html_search_meta(['og:title', 'twitter:title'], webpage, fatal=True)}{f' - {episode}' if episode else ''}",
            'description': self._html_search_meta(['og:description', 'twitter:description'], webpage, fatal=True),
            'formats': formats,
            'subtitles': subtitles,
        }

    def get_api_with_st_token(self, video_id, ep):
        path = f'stream/vod/{video_id}/{ep}/auto_vip'
        suffix = '/api/v6.2_w/'

        timestamp = int(time.time()) + 10800
        token = f'WEBv6Dkdsad90dasdjlALDDDS{timestamp}{suffix}{path}'

        m = hashlib.md5()
        m.update(token.encode())

        st_token = self.encrypt(m.hexdigest())

        return f"https://api.fptplay.net{suffix}{path}?{urllib.parse.urlencode({'st': st_token, 'e': timestamp})}"

    def encrypt(self, string):
        n = []
        t = string.upper()
        r = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
        for o in range(int(len(t) / 2)):
            i = t[2 * o:2 * o + 2]
            num = '0x%s' % i
            n.append(int(num, 16))

        def convert(e):
            t = ""
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
                for o in range(n, 3, 1):
                    i[o] = 0

                for o in range(n + 1):
                    a[0] = (252 & i[0]) >> 2
                    a[1] = ((3 & i[0]) << 4) + ((240 & i[1]) >> 4)
                    a[2] = ((15 & i[1]) << 2) + ((192 & i[2]) >> 6)
                    a[3] = (63 & i[2])
                    t += r[a[o]]
                n += 1
                while n < 3:
                    t += "="
                    n += 1
            return t

        return convert(n).replace('+', '-').replace('/', '_').replace('=', '')
