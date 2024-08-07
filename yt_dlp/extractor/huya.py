import base64
import hashlib
import random
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    int_or_none,
    parse_duration,
    str_or_none,
    traverse_obj,
    try_get,
    unescapeHTML,
    unified_strdate,
    update_url_query,
)


class HuyaLiveIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.|m\.)?huya\.com/(?!(?:video/play/))(?P<id>[^/#?&]+)(?:\D|$)'
    IE_NAME = 'huya:live'
    IE_DESC = 'huya.com'
    TESTS = [{
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
    _VALID_URL = r'https://(?:www\.)?huya\.com/video/play/(?P<id>\d+)\.html'

    IE_NAME = 'huya:video'
    IE_DESC = '虎牙视频'

    _TESTS = [{
        'url': 'https://www.huya.com/video/play/1002412640.html',
        'info_dict': {
            'id': '1002412640',
            'title': '8月3日',
            'thumbnail': r're:https://.*\.jpg*',
            'format_id': '1080P',
            'url': r're:https?://.*\.mp4*',
            'ext': 'mp4',
            'width': 1728,
            'height': 1080,
            'filesize': 5854080,
            'protocol': 'http',
            'format_note': '1080P - 1728x1080',
            'duration': 14,
            'uploader': '虎牙-ATS欧卡车队青木',
            'uploader_id': '1564376151',
            'upload_date': '20240803',
            'view_count': int,
            'comment_count': int,
            'like_count': int,
        }, 'params': {
            'skip_download': True,
        },
    },
        {
        'url': 'https://www.huya.com/video/play/556054543.html',
        'info_dict': {
            'id': '556054543',
            'title': '我不挑事 也不怕事',
            'thumbnail': r're:https://.*\.jpg*',
            'format_id': '1080P',
            'url': r're:https?://.*\.mp4*',
            'ext': 'mp4',
            'width': 1920,
            'height': 1080,
            'filesize': 368724330,
            'protocol': 'http',
            'format_note': '1080P - 1920x1080',
            'duration': 1864,
            'uploader': '卡尔',
            'uploader_id': '367138632',
            'upload_date': '20210811',
            'view_count': int,
            'comment_count': int,
            'like_count': int,
        }, 'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url: str) -> dict:
        video_id = self._match_id(url)
        api_url = f'https://liveapi.huya.com/moment/getMomentContent?videoId={video_id}'

        try:
            response = self._download_json(api_url, video_id)
        except Exception as e:
            raise ExtractorError(f'Failed to download JSON data: {e}', expected=True)

        video_data = traverse_obj(response, ('data', 'moment', 'videoInfo'))

        if not isinstance(video_data, dict):
            raise ExtractorError('No video data found')

        formats = []
        for definition in video_data.get('definitions', []):
            format_info = {
                'format_id': definition.get('defName'),
                'url': definition.get('url'),
                'ext': determine_ext(definition.get('url', '')),
                'width': int_or_none(definition.get('width')),
                'height': int_or_none(definition.get('height')),
                'filesize': int_or_none(definition.get('size')),
                'protocol': 'http',  # Assuming HTTP protocol
                'format_note': f'{definition.get("defName", "")} - {definition.get("width", "")}x{definition.get("height", "")}',
            }
            formats.append(format_info)

        return {
            'id': video_id,
            'title': video_data.get('videoTitle', 'Untitled'),
            'thumbnail': video_data.get('videoCover'),
            'formats': formats,
            'duration': self._parse_duration(video_data.get('videoDuration', '0')),
            'uploader': video_data.get('nickName'),
            'uploader_id': str_or_none(video_data.get('uid')),
            'upload_date': self._parse_date(video_data.get('videoUploadTime', '')),
            'view_count': video_data.get('videoPlayNum'),
            'comment_count': video_data.get('videoCommentNum'),
            'like_count': video_data.get('favorCount'),
        }

    def _parse_duration(self, duration_str: str) -> int:
        """Parse duration string (e.g., '00:14' or '01:23:45') into seconds."""
        try:
            duration = parse_duration(duration_str)
            return int(duration) if duration is not None else 0
        except ValueError:
            return 0

    def _parse_date(self, date_str: str) -> str:
        """Convert date string to YYYYMMDD format using yt-dlp's unified_strdate method."""
        try:
            # Use yt-dlp's unified_strdate method to parse the date string
            parsed_date = unified_strdate(date_str)
            return parsed_date if parsed_date is not None else ''
        except ValueError:
            return ''
