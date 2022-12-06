import time
import random
import string
import hashlib

from .common import InfoExtractor
from ..utils import traverse_obj


class KankaNewsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?kankanews\.com/a/[0-9]+\-[0-9]+\-[0-9]+/[0-9]+\.shtml.*'
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
        webpage = self._download_webpage(url, None)
        video_id = self._search_regex(r'omsid="(\d+)"', webpage, 'video_id')

        params = [
            'nonce=' + str(''.join(random.choices(string.ascii_letters + string.digits, k=8)).lower()),
            'omsid=' + str(video_id),
            'platform=pc',
            'timestamp=' + str(int(time.time())),
            'version=1.0'
        ]
        tmp = '&'.join(params) + '&28c8edde3d61a0411511d3b1866f0636'
        tmp = hashlib.md5(tmp.encode()).hexdigest()
        sign = hashlib.md5(tmp.encode()).hexdigest()
        params.append(('sign' + '=' + sign))
        meta = self._download_json('https://api-app.kankanews.com/kankan/pc/getvideo?' + '&'.join(params), video_id)
        meta = traverse_obj(meta, ('result', 'video'))

        return {
            'id': video_id,
            'url': meta.get('videourl'),
            'title': self._search_regex(r'g\.title="(.+?)"', webpage, 'title'),
            'thumbnail': meta.get('titlepic'),
        }
