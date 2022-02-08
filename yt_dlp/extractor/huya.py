import base64
import hashlib
import json
import random
from html import unescape
from urllib.parse import parse_qsl, urlencode

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    try_get
)


class HuyaIE(InfoExtractor):
    _VALID_URL = r'(?x)^((?:http[s]?|fpt):)\/?\/(?:www\.|m\.|)huya\.com\/(?P<id>.*?)(?:\/|$)'
    _TESTS = [{
        'url': 'https://www.huya.com/kaerlol',
        'info_dict': {
            'id': 'kaerlol',
            'ext': 'flv',
            'title': '【1000攻击力】1A流戏命师',
        },
    }, {
        'url': 'https://www.huya.com/573178',
        'info_dict': {
            'id': '573178',
            'ext': 'flv',
            'title': 'S6 全阵容细节教学',
        },
    }]
    IE_NAME = 'huya'
    IE_DESC = 'huya.com'

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id=video_id)

        json_stream = self._search_regex(r'"stream": "([a-zA-Z0-9+=/]+)"', webpage, 'stream', default=None)

        if not json_stream:
            raise ExtractorError('Video is offline')

        stream_data = json.loads(base64.b64decode(json_stream).decode())
        room_info = try_get(stream_data, lambda x: x['data'][0]['gameLiveInfo']) or None

        if not room_info:
            raise ExtractorError('Can not extract the room info')

        title = room_info.get('introduction', None)
        if not title:
            title = self._html_search_regex(r'<title>([^<]+)</title>', webpage, 'title')
        screen_type = room_info.get('screenType')
        live_source_type = room_info.get('liveSourceType')

        stream_info_list = try_get(stream_data, lambda x: x['data'][0]['gameStreamInfoList'])
        random.shuffle(stream_info_list)
        random.shuffle(stream_info_list)
        stream_info = {}
        s_url = ''
        while stream_info_list:
            stream_info = stream_info_list.pop()
            s_url = stream_info.get('sFlvUrl')
            if s_url:
                break

        s_stream_name = stream_info.get('sStreamName')
        s_url_suffix = stream_info.get('sFlvUrlSuffix')
        _url = f'{s_url}/{s_stream_name}.{s_url_suffix}?'

        re_secret = not screen_type and live_source_type in (0, 8, 13)
        params = dict(parse_qsl(unescape(stream_info['sFlvAntiCode'])))

        if re_secret:
            params.setdefault('t', '100')  # 102
            ct = int(params.get('wsTime'), 16) + random.random()
            l_presenter_uid = stream_info['lPresenterUid']
            if not s_stream_name.startswith(str(l_presenter_uid)):
                uid = l_presenter_uid
            else:
                uid = int(ct % 1e7 * 1e6 % 0xffffffff)
            u1 = uid & 0xffffffff00000000
            u2 = uid & 0xffffffff
            u3 = uid & 0xffffff
            u = u1 | u2 >> 24 | u3 << 8
            params.update({
                'u': str(u),
                'seqid': str(int(ct * 1000) + uid),
                'ver': '1',
                'uuid': int(ct % 1e7 * 1e6 % 0xffffffff),
            })
            fm = base64.b64decode(params['fm']).decode().split('_', 1)[0]
            ss = hashlib.md5('|'.join([params.get('seqid'), params.get('ctype'), params.get('t')]))

        formats = []
        for si in stream_data['vMultiStreamInfo']:
            rate = si['iBitRate']
            if rate:
                params['ratio'] = rate
            else:
                params.pop('ratio', None)
            if re_secret:
                params['wsSecret'] = hashlib.md5(
                    '_'.join([fm, params.get('u'), s_stream_name, ss, params.get('wsTime')]))
            url = _url + urlencode(params, safe='*')
            formats.append({
                'ext': 'flv',
                'format_id': si['sDisplayName'],
                'url': url,
                'video_ext': 'flv'
            })

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
        }
