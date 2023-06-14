import time
import hashlib
import re
import urllib

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    unescapeHTML,
    unified_strdate,
    urljoin,
)


class DouyuTVIE(InfoExtractor):
    IE_DESC = '斗鱼'
    _VALID_URL = r'https?://(?:www\.)?douyu(?:tv)?\.com/(topic/\w+\?rid=|(?:[^/]+/))*(?P<id>[A-Za-z0-9]+)'
    _TESTS = [{
        'url': 'http://www.douyutv.com/iseven',
        'info_dict': {
            'id': '17732',
            'display_id': 'iseven',
            'ext': 'flv',
            'title': 're:^清晨醒脑！根本停不下来！ [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'description': r're:.*m7show@163\.com.*',
            'thumbnail': r're:^https?://.*\.png',
            'uploader': '7师傅',
            'is_live': True,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.douyutv.com/85982',
        'info_dict': {
            'id': '85982',
            'display_id': '85982',
            'ext': 'flv',
            'title': 're:^小漠从零单排记！——CSOL2躲猫猫 [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'description': 'md5:746a2f7a253966a06755a912f0acc0d2',
            'thumbnail': r're:^https?://.*\.png',
            'uploader': 'douyu小漠',
            'is_live': True,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Room not found',
    }, {
        'url': 'http://www.douyutv.com/17732',
        'info_dict': {
            'id': '17732',
            'display_id': '17732',
            'ext': 'flv',
            'title': 're:^清晨醒脑！根本停不下来！ [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'description': r're:.*m7show@163\.com.*',
            'thumbnail': r're:^https?://.*\.png',
            'uploader': '7师傅',
            'is_live': True,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.douyu.com/topic/ydxc?rid=6560603',
        'info_dict': {
            'id': '6560603',
            'display_id': '6560603',
            'ext': 'flv',
            'title': 're:^阿余：新年快乐恭喜发财！ [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'description': 're:.*直播时间.*',
            'thumbnail': r're:^https?://.*\.png',
            'uploader': '阿涛皎月Carry',
            'live_status': 'is_live',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.douyu.com/xiaocang',
        'only_matching': True,
    }, {
        # \"room_id\"
        'url': 'http://www.douyu.com/t/lpl',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        if video_id.isdigit():
            room_id = video_id
        else:
            page = self._download_webpage(url, video_id)
            room_id = self._html_search_regex(
                r'"room_id\\?"\s*:\s*(\d+),', page, 'room id')

        # Grab metadata from API
        params = {
            'aid': 'wp',
            'client_sys': 'wp',
            'time': int(time.time()),
        }
        params['auth'] = hashlib.md5(
            f'room/{video_id}?{urllib.parse.urlencode(params)}zNzMV1y4EMxOHS6I5WKm'.encode()).hexdigest()
        room = self._download_json(
            f'http://www.douyutv.com/api/v1/room/{room_id}', video_id,
            note='Downloading room info', query=params)['data']

        # 1 = live, 2 = offline
        if room.get('show_status') == '2':
            raise ExtractorError('Live stream is offline', expected=True)

        video_url = urljoin('https://hls3-akm.douyucdn.cn/', self._search_regex(r'(live/.*)', room['hls_url'], 'URL'))
        formats, subs = self._extract_m3u8_formats_and_subtitles(video_url, room_id)

        title = unescapeHTML(room['room_name'])
        description = room.get('show_details')
        thumbnail = room.get('room_src')
        uploader = room.get('nickname')

        return {
            'id': room_id,
            'display_id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'uploader': uploader,
            'is_live': True,
            'subtitles': subs,
            'formats': formats,
        }


class DouyuShowIE(InfoExtractor):
    _VALID_URL = r'https?://v(?:mobile)?\.douyu\.com/show/(?P<id>[0-9a-zA-Z]+)'

    _TESTS = [{
        'url': 'https://v.douyu.com/show/rjNBdvnVXNzvE2yw',
        'md5': '0c2cfd068ee2afe657801269b2d86214',
        'info_dict': {
            'id': 'rjNBdvnVXNzvE2yw',
            'ext': 'mp4',
            'title': '陈一发儿：砒霜 我有个室友系列！04-01 22点场',
            'duration': 7150.08,
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': '陈一发儿',
            'uploader_id': 'XrZwYelr5wbK',
            'uploader_url': 'https://v.douyu.com/author/XrZwYelr5wbK',
            'upload_date': '20170402',
        },
    }, {
        'url': 'https://vmobile.douyu.com/show/rjNBdvnVXNzvE2yw',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        url = url.replace('vmobile.', 'v.')
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        room_info = self._parse_json(self._search_regex(
            r'var\s+\$ROOM\s*=\s*({.+});', webpage, 'room info'), video_id)

        video_info = None

        for trial in range(5):
            # Sometimes Douyu rejects our request. Let's try it more times
            try:
                video_info = self._download_json(
                    'https://vmobile.douyu.com/video/getInfo', video_id,
                    query={'vid': video_id},
                    headers={
                        'Referer': url,
                        'x-requested-with': 'XMLHttpRequest',
                    })
                break
            except ExtractorError:
                self._sleep(1, video_id)

        if not video_info:
            raise ExtractorError('Can\'t fetch video info')

        formats = self._extract_m3u8_formats(
            video_info['data']['video_url'], video_id,
            entry_protocol='m3u8_native', ext='mp4')

        upload_date = unified_strdate(self._html_search_regex(
            r'<em>上传时间：</em><span>([^<]+)</span>', webpage,
            'upload date', fatal=False))

        uploader = uploader_id = uploader_url = None
        mobj = re.search(
            r'(?m)<a[^>]+href="/author/([0-9a-zA-Z]+)".+?<strong[^>]+title="([^"]+)"',
            webpage)
        if mobj:
            uploader_id, uploader = mobj.groups()
            uploader_url = urljoin(url, '/author/' + uploader_id)

        return {
            'id': video_id,
            'title': room_info['name'],
            'formats': formats,
            'duration': room_info.get('duration'),
            'thumbnail': room_info.get('pic'),
            'upload_date': upload_date,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'uploader_url': uploader_url,
        }
