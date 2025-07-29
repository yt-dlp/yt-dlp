import base64
import hashlib
import random
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    int_or_none,
    parse_duration,
    str_or_none,
    try_get,
    unescapeHTML,
    update_url,
    update_url_query,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class HuyaLiveIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.|m\.)?huya\.com/(?!(?:video/play/))(?P<id>[^/#?&]+)(?:\D|$)'
    IE_NAME = 'huya:live'
    IE_DESC = '虎牙直播'
    _TESTS = [{
        'url': 'https://www.huya.com/572329',
        'info_dict': {
            'id': '572329',
            'title': str,
            'ext': 'flv',
            'description': str,
            'is_live': True,
            'view_count': int,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.huya.com/xiaoyugame',
        'only_matching': True,
    }]

    _RESOLUTION = {
        '蓝光': {
            'width': 1920,
            'height': 1080,
        },
        '超清': {
            'width': 1280,
            'height': 720,
        },
        '流畅': {
            'width': 800,
            'height': 480,
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id=video_id)
        stream_data = self._search_json(r'stream:\s', webpage, 'stream', video_id=video_id, default=None)
        room_info = try_get(stream_data, lambda x: x['data'][0]['gameLiveInfo'])
        if not room_info:
            raise ExtractorError('Can not extract the room info', expected=True)
        title = room_info.get('roomName') or room_info.get('introduction') or self._html_extract_title(webpage)
        screen_type = room_info.get('screenType')
        live_source_type = room_info.get('liveSourceType')
        stream_info_list = stream_data['data'][0]['gameStreamInfoList']
        if not stream_info_list:
            raise ExtractorError('Video is offline', expected=True)
        formats = []
        for stream_info in stream_info_list:
            stream_url = stream_info.get('sFlvUrl')
            if not stream_url:
                continue
            stream_name = stream_info.get('sStreamName')
            re_secret = not screen_type and live_source_type in (0, 8, 13)
            params = dict(urllib.parse.parse_qsl(unescapeHTML(stream_info['sFlvAntiCode'])))
            fm, ss = '', ''
            if re_secret:
                fm, ss = self.encrypt(params, stream_info, stream_name)
            for si in stream_data.get('vMultiStreamInfo'):
                display_name, bitrate = re.fullmatch(
                    r'(.+?)(?:(\d+)M)?', si.get('sDisplayName')).groups()
                rate = si.get('iBitRate')
                if rate:
                    params['ratio'] = rate
                else:
                    params.pop('ratio', None)
                    if bitrate:
                        rate = int(bitrate) * 1000
                if re_secret:
                    params['wsSecret'] = hashlib.md5(
                        '_'.join([fm, params['u'], stream_name, ss, params['wsTime']]))
                formats.append({
                    'ext': stream_info.get('sFlvUrlSuffix'),
                    'format_id': str_or_none(stream_info.get('iLineIndex')),
                    'tbr': rate,
                    'url': update_url_query(f'{stream_url}/{stream_name}.{stream_info.get("sFlvUrlSuffix")}',
                                            query=params),
                    **self._RESOLUTION.get(display_name, {}),
                })

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'view_count': room_info.get('totalCount'),
            'thumbnail': room_info.get('screenshot'),
            'description': room_info.get('contentIntro'),
            'http_headers': {
                'Origin': 'https://www.huya.com',
                'Referer': 'https://www.huya.com/',
            },
        }

    def encrypt(self, params, stream_info, stream_name):
        ct = int_or_none(params.get('wsTime'), 16) + random.random()
        presenter_uid = stream_info['lPresenterUid']
        if not stream_name.startswith(str(presenter_uid)):
            uid = presenter_uid
        else:
            uid = int_or_none(ct % 1e7 * 1e6 % 0xffffffff)
        u1 = uid & 0xffffffff00000000
        u2 = uid & 0xffffffff
        u3 = uid & 0xffffff
        u = u1 | u2 >> 24 | u3 << 8
        params.update({
            'u': str_or_none(u),
            'seqid': str_or_none(int_or_none(ct * 1000) + uid),
            'ver': '1',
            'uuid': int_or_none(ct % 1e7 * 1e6 % 0xffffffff),
            't': '100',
        })
        fm = base64.b64decode(params['fm']).decode().split('_', 1)[0]
        ss = hashlib.md5('|'.join([params['seqid'], params['ctype'], params['t']]))
        return fm, ss


class HuyaVideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?huya\.com/video/play/(?P<id>\d+)\.html'
    IE_NAME = 'huya:video'
    IE_DESC = '虎牙视频'

    _TESTS = [{
        'url': 'https://www.huya.com/video/play/1002412640.html',
        'info_dict': {
            'id': '1002412640',
            'ext': 'mp4',
            'title': '8月3日',
            'categories': ['主机游戏'],
            'duration': 14.0,
            'uploader': '虎牙-ATS欧卡车队青木',
            'uploader_id': '1564376151',
            'upload_date': '20240803',
            'view_count': int,
            'comment_count': int,
            'like_count': int,
            'thumbnail': r're:https?://.+\.jpg',
            'timestamp': 1722675433,
        },
    }, {
        'url': 'https://www.huya.com/video/play/556054543.html',
        'info_dict': {
            'id': '556054543',
            'ext': 'mp4',
            'title': '我不挑事 也不怕事',
            'categories': ['英雄联盟'],
            'description': 'md5:58184869687d18ce62dc7b4b2ad21201',
            'duration': 1864.0,
            'uploader': '卡尔',
            'uploader_id': '367138632',
            'upload_date': '20210811',
            'view_count': int,
            'comment_count': int,
            'like_count': int,
            'tags': 'count:4',
            'thumbnail': r're:https?://.+\.jpg',
            'timestamp': 1628675950,
        },
    }, {
        # Only m3u8 available
        'url': 'https://www.huya.com/video/play/1063345618.html',
        'info_dict': {
            'id': '1063345618',
            'ext': 'mp4',
            'title': '峡谷第一中！黑铁上钻石顶级教学对抗elo',
            'categories': ['英雄联盟'],
            'comment_count': int,
            'duration': 21603.0,
            'like_count': int,
            'thumbnail': r're:https?://.+\.jpg',
            'timestamp': 1749668803,
            'upload_date': '20250611',
            'uploader': '北枫CC',
            'uploader_id': '2183525275',
            'view_count': int,
        },
    }]

    def _real_extract(self, url: str):
        video_id = self._match_id(url)
        moment = self._download_json(
            'https://liveapi.huya.com/moment/getMomentContent',
            video_id, query={'videoId': video_id})['data']['moment']

        formats = []
        for definition in traverse_obj(moment, (
            'videoInfo', 'definitions', lambda _, v: url_or_none(v['m3u8']),
        )):
            fmts = self._extract_m3u8_formats(definition['m3u8'], video_id, 'mp4', fatal=False)
            for fmt in fmts:
                fmt.update(**traverse_obj(definition, {
                    'filesize': ('size', {int_or_none}),
                    'format_id': ('defName', {str}),
                    'height': ('height', {int_or_none}),
                    'quality': ('definition', {int_or_none}),
                    'width': ('width', {int_or_none}),
                }))
            formats.extend(fmts)

        return {
            'id': video_id,
            'formats': formats,
            **traverse_obj(moment, {
                'comment_count': ('commentCount', {int_or_none}),
                'description': ('content', {clean_html}, filter),
                'like_count': ('favorCount', {int_or_none}),
                'timestamp': ('cTime', {int_or_none}),
            }),
            **traverse_obj(moment, ('videoInfo', {
                'title': ('videoTitle', {str}),
                'categories': ('category', {str}, filter, all, filter),
                'duration': ('videoDuration', {parse_duration}),
                'tags': ('tags', ..., {str}, filter, all, filter),
                'thumbnail': (('videoBigCover', 'videoCover'), {url_or_none}, {update_url(query=None)}, any),
                'uploader': ('nickName', {str}),
                'uploader_id': ('uid', {str_or_none}),
                'view_count': ('videoPlayNum', {int_or_none}),
            })),
        }
