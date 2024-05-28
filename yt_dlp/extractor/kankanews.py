import hashlib
import random
import string
import time
import urllib.parse

from .common import InfoExtractor


class KankaNewsIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'https?://(?:www\.)?kankanews\.com/a/\d+\-\d+\-\d+/(?P<id>\d+)\.shtml'
    _TESTS = [{
        'url': 'https://www.kankanews.com/a/2022-11-08/00310276054.shtml?appid=1088227',
        'md5': '05e126513c74b1258d657452a6f4eef9',
        'info_dict': {
            'id': '4485057',
            'url': 'http://mediaplay.kksmg.com/2022/11/08/h264_450k_mp4_1a388ad771e0e4cc28b0da44d245054e_ncm.mp4',
            'ext': 'mp4',
            'title': '视频｜第23个中国记者节，我们在进博切蛋糕',
            'thumbnail': r're:^https?://.*\.jpg*',
        }
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        video_id = self._search_regex(r'omsid\s*=\s*"(\d+)"', webpage, 'video id')

        params = {
            'nonce': ''.join(random.choices(string.ascii_lowercase + string.digits, k=8)),
            'omsid': video_id,
            'platform': 'pc',
            'timestamp': int(time.time()),
            'version': '1.0',
        }
        params['sign'] = hashlib.md5((hashlib.md5((
            urllib.parse.urlencode(params) + '&28c8edde3d61a0411511d3b1866f0636'
        ).encode()).hexdigest()).encode()).hexdigest()

        meta = self._download_json('https://api-app.kankanews.com/kankan/pc/getvideo',
                                   video_id, query=params)['result']['video']

        return {
            'id': video_id,
            'url': meta['videourl'],
            'title': self._search_regex(r'g\.title\s*=\s*"([^"]+)"', webpage, 'title'),
            'thumbnail': meta.get('titlepic'),
        }
