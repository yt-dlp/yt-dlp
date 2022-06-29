import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    float_or_none,
    int_or_none,
    traverse_obj,
)


class AcFunVideoIE(InfoExtractor):
    IE_NAME = 'AcFunVideoIE'
    _VALID_URL = r'(?x)https?://(?:www\.acfun\.cn/v/)ac(?P<id>[_\d]+)'

    _TESTS = [{
        'url': 'https://www.acfun.cn/v/ac35457073',
        'info_dict': {
            'id': '35283657',
            'title': '【十五周年庆】文章区UP主祝AcFun生日快乐！',
            'duration': 455.21,
            'timestamp': 1655289827,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'skip': 'Geo-restricted to China',
    }, {
        'url': 'https://www.acfun.cn/v/ac35457073',
        'only_matching': True,
    }]

    @staticmethod
    def parse_format(info):
        vcodec, acodec = None, None

        codec_str = info.get('codecs') or ''
        m = re.match('(?P<vc>[^,]+),(?P<ac>[^,]+)', codec_str)
        if m:
            vcodec = m.group("vc")
            acodec = m.group("ac")

        return {
            'url': info.get('url'),
            'fps': int_or_none(info.get('frameRate')),
            'width': int_or_none(info.get('width')),
            'height': int_or_none(info.get('height')),
            'vcodec': vcodec,
            'acodec': acodec,
            'tbr': float_or_none(info.get('avgBitrate'))
        }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')

        webpage = self._download_webpage(url, video_id)
        json_all = self._search_json(r'window.videoInfo\s*=\s*', webpage, 'videoInfo', video_id)

        video_info = json_all['currentVideoInfo']
        playjson = self._parse_json(video_info['ksPlayJson'], video_id)
        video_inner_id = traverse_obj(json_all, ('currentVideoInfo', 'id'))

        ext = determine_ext(video_info.get('fileName'), 'mp4')

        formats = []
        for video in traverse_obj(playjson, ('adaptationSet', 0, 'representation')):
            fmt = AcFunVideoIE.parse_format(video)
            formats.append({**fmt, 'ext': ext})

        self._sort_formats(formats)

        video_list = json_all['videoList']
        p_idx, video_info = [(idx + 1, v) for (idx, v) in enumerate(video_list)
                             if v['id'] == video_inner_id
                             ][0]

        title = json_all['title']
        if len(video_list) > 1:
            title = f"{title} P{p_idx:02d} {video_info['title']}"

        return {
            'id': video_id,
            'title': title,
            'duration': float_or_none(video_info.get('durationMillis'), 1000),
            'timestamp': int_or_none(video_info.get('uploadTime'), 1000),
            'formats': formats,
            'http_headers': {
                'Referer': url,
            },
        }


class AcFunBangumiIE(InfoExtractor):
    IE_NAME = 'AcFunBangumiIE'
    _VALID_URL = r'''(?x)
                    https?://(?:www\.acfun\.cn/bangumi/)
                        (?P<id>aa[_\d]+)
                        (?:\?ac=(?P<ac_idx>\d+))?
                    '''

    _TESTS = [{
        'url': 'https://www.acfun.cn/bangumi/aa6002917',
        'info_dict': {
            'id': 'aa6002917',
            'title': '租借女友 第1话 租借女友',
            'duration': 1467,
            'timestamp': 1594432800,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'skip': 'Geo-restricted to China',
    }, {
        'url': 'https://www.acfun.cn/bangumi/aa6002917',
        'only_matching': True,
    }, {
        'url': 'https://www.acfun.cn/bangumi/aa6002917_36188_1745457?ac=2',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')

        webpage = self._download_webpage(url, video_id)
        json_bangumi_data = self._search_json(r'window.bangumiData\s*=\s*', webpage, 'bangumiData', video_id)

        if not mobj.group('ac_idx'):
            json_key, title_key = 'currentVideoInfo', 'showTitle'
        else:
            # if has ac_idx, this url is a proxy to other video which is at https://www.acfun.cn/v/ac
            # the normal video_id is not in json
            ac_idx = mobj.group('ac_idx')
            video_id = f"{video_id}_ac={ac_idx}"
            json_key, title_key = 'hlVideoInfo', 'title'

        video_info = json_bangumi_data[json_key]
        playlist = self._parse_json(video_info['ksPlayJson'], video_id)
        title = video_info[title_key]

        ext = determine_ext(video_info.get('fileName'), 'mp4')

        formats = []
        for video in traverse_obj(playlist, ('adaptationSet', 0, 'representation')):
            fmt = AcFunVideoIE.parse_format(video)
            formats.append({**fmt, 'ext': ext})

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'duration': float_or_none(video_info.get('durationMillis'), 1000),
            'timestamp': int_or_none(video_info.get('uploadTime'), 1000),
            'formats': formats,
            'http_headers': {
                'Referer': url,
            },
        }
