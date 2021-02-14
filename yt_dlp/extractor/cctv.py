# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    float_or_none,
    try_get,
    unified_timestamp,
)


class CCTVIE(InfoExtractor):
    IE_DESC = '央视网'
    _VALID_URL = r'https?://(?:(?:[^/]+)\.(?:cntv|cctv)\.(?:com|cn)|(?:www\.)?ncpa-classic\.com)/(?:[^/]+/)*?(?P<id>[^/?#&]+?)(?:/index)?(?:\.s?html|[?#&]|$)'
    _TESTS = [{
        # fo.addVariable("videoCenterId","id")
        'url': 'http://sports.cntv.cn/2016/02/12/ARTIaBRxv4rTT1yWf1frW2wi160212.shtml',
        'md5': 'd61ec00a493e09da810bf406a078f691',
        'info_dict': {
            'id': '5ecdbeab623f4973b40ff25f18b174e8',
            'ext': 'mp4',
            'title': '[NBA]二少联手砍下46分 雷霆主场击败鹈鹕（快讯）',
            'description': 'md5:7e14a5328dc5eb3d1cd6afbbe0574e95',
            'duration': 98,
            'uploader': 'songjunjie',
            'timestamp': 1455279956,
            'upload_date': '20160212',
        },
    }, {
        # var guid = "id"
        'url': 'http://tv.cctv.com/2016/02/05/VIDEUS7apq3lKrHG9Dncm03B160205.shtml',
        'info_dict': {
            'id': 'efc5d49e5b3b4ab2b34f3a502b73d3ae',
            'ext': 'mp4',
            'title': '[赛车]“车王”舒马赫恢复情况成谜（快讯）',
            'description': '2月4日，蒙特泽莫罗透露了关于“车王”舒马赫恢复情况，但情况是否属实遭到了质疑。',
            'duration': 37,
            'uploader': 'shujun',
            'timestamp': 1454677291,
            'upload_date': '20160205',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # changePlayer('id')
        'url': 'http://english.cntv.cn/special/four_comprehensives/index.shtml',
        'info_dict': {
            'id': '4bb9bb4db7a6471ba85fdeda5af0381e',
            'ext': 'mp4',
            'title': 'NHnews008 ANNUAL POLITICAL SEASON',
            'description': 'Four Comprehensives',
            'duration': 60,
            'uploader': 'zhangyunlei',
            'timestamp': 1425385521,
            'upload_date': '20150303',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # loadvideo('id')
        'url': 'http://cctv.cntv.cn/lm/tvseries_russian/yilugesanghua/index.shtml',
        'info_dict': {
            'id': 'b15f009ff45c43968b9af583fc2e04b2',
            'ext': 'mp4',
            'title': 'Путь，усыпанный космеями Серия 1',
            'description': 'Путь, усыпанный космеями',
            'duration': 2645,
            'uploader': 'renxue',
            'timestamp': 1477479241,
            'upload_date': '20161026',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # var initMyAray = 'id'
        'url': 'http://www.ncpa-classic.com/2013/05/22/VIDE1369219508996867.shtml',
        'info_dict': {
            'id': 'a194cfa7f18c426b823d876668325946',
            'ext': 'mp4',
            'title': '小泽征尔音乐塾 音乐梦想无国界',
            'duration': 2173,
            'timestamp': 1369248264,
            'upload_date': '20130522',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # var ids = ["id"]
        'url': 'http://www.ncpa-classic.com/clt/more/416/index.shtml',
        'info_dict': {
            'id': 'a8606119a4884588a79d81c02abecc16',
            'ext': 'mp3',
            'title': '来自维也纳的新年贺礼',
            'description': 'md5:f13764ae8dd484e84dd4b39d5bcba2a7',
            'duration': 1578,
            'uploader': 'djy',
            'timestamp': 1482942419,
            'upload_date': '20161228',
        },
        'params': {
            'skip_download': True,
        },
        'expected_warnings': ['Failed to download m3u8 information'],
    }, {
        'url': 'http://ent.cntv.cn/2016/01/18/ARTIjprSSJH8DryTVr5Bx8Wb160118.shtml',
        'only_matching': True,
    }, {
        'url': 'http://tv.cntv.cn/video/C39296/e0210d949f113ddfb38d31f00a4e5c44',
        'only_matching': True,
    }, {
        'url': 'http://english.cntv.cn/2016/09/03/VIDEhnkB5y9AgHyIEVphCEz1160903.shtml',
        'only_matching': True,
    }, {
        'url': 'http://tv.cctv.com/2016/09/07/VIDE5C1FnlX5bUywlrjhxXOV160907.shtml',
        'only_matching': True,
    }, {
        'url': 'http://tv.cntv.cn/video/C39296/95cfac44cabd3ddc4a9438780a4e5c44',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        video_id = self._search_regex(
            [r'var\s+guid\s*=\s*["\']([\da-fA-F]+)',
             r'videoCenterId["\']\s*,\s*["\']([\da-fA-F]+)',
             r'changePlayer\s*\(\s*["\']([\da-fA-F]+)',
             r'load[Vv]ideo\s*\(\s*["\']([\da-fA-F]+)',
             r'var\s+initMyAray\s*=\s*["\']([\da-fA-F]+)',
             r'var\s+ids\s*=\s*\[["\']([\da-fA-F]+)'],
            webpage, 'video id')

        data = self._download_json(
            'http://vdn.apps.cntv.cn/api/getHttpVideoInfo.do', video_id,
            query={
                'pid': video_id,
                'url': url,
                'idl': 32,
                'idlr': 32,
                'modifyed': 'false',
            })

        title = data['title']

        formats = []

        video = data.get('video')
        if isinstance(video, dict):
            for quality, chapters_key in enumerate(('lowChapters', 'chapters')):
                video_url = try_get(
                    video, lambda x: x[chapters_key][0]['url'], compat_str)
                if video_url:
                    formats.append({
                        'url': video_url,
                        'format_id': 'http',
                        'quality': quality,
                        'preference': -1,
                    })

        hls_url = try_get(data, lambda x: x['hls_url'], compat_str)
        if hls_url:
            hls_url = re.sub(r'maxbr=\d+&?', '', hls_url)
            formats.extend(self._extract_m3u8_formats(
                hls_url, video_id, 'mp4', entry_protocol='m3u8_native',
                m3u8_id='hls', fatal=False))

        self._sort_formats(formats)

        uploader = data.get('editer_name')
        description = self._html_search_meta(
            'description', webpage, default=None)
        timestamp = unified_timestamp(data.get('f_pgmtime'))
        duration = float_or_none(try_get(video, lambda x: x['totalLength']))

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'uploader': uploader,
            'timestamp': timestamp,
            'duration': duration,
            'formats': formats,
        }
