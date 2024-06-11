import hashlib
import time
import urllib
import uuid

from .common import InfoExtractor
from .openload import PhantomJSwrapper
from ..utils import (
    ExtractorError,
    UserNotLive,
    determine_ext,
    int_or_none,
    js_to_json,
    parse_resolution,
    str_or_none,
    traverse_obj,
    unescapeHTML,
    url_or_none,
    urlencode_postdata,
    urljoin,
)


class DouyuBaseIE(InfoExtractor):
    def _download_cryptojs_md5(self, video_id):
        for url in [
            'https://cdnjs.cloudflare.com/ajax/libs/crypto-js/3.1.2/rollups/md5.js',
            'https://cdn.bootcdn.net/ajax/libs/crypto-js/3.1.2/rollups/md5.js',
        ]:
            js_code = self._download_webpage(
                url, video_id, note='Downloading signing dependency', fatal=False)
            if js_code:
                self.cache.store('douyu', 'crypto-js-md5', js_code)
                return js_code
        raise ExtractorError('Unable to download JS dependency (crypto-js/md5)')

    def _get_cryptojs_md5(self, video_id):
        return self.cache.load('douyu', 'crypto-js-md5') or self._download_cryptojs_md5(video_id)

    def _calc_sign(self, sign_func, video_id, a):
        b = uuid.uuid4().hex
        c = round(time.time())
        js_script = f'{self._get_cryptojs_md5(video_id)};{sign_func};console.log(ub98484234("{a}","{b}","{c}"))'
        phantom = PhantomJSwrapper(self)
        result = phantom.execute(js_script, video_id,
                                 note='Executing JS signing script').strip()
        return {i: v[0] for i, v in urllib.parse.parse_qs(result).items()}

    def _search_js_sign_func(self, webpage, fatal=True):
        # The greedy look-behind ensures last possible script tag is matched
        return self._search_regex(
            r'(?:<script.*)?<script[^>]*>(.*?ub98484234.*?)</script>', webpage, 'JS sign func', fatal=fatal)


class DouyuTVIE(DouyuBaseIE):
    IE_DESC = '斗鱼直播'
    _VALID_URL = r'https?://(?:www\.)?douyu(?:tv)?\.com/(topic/\w+\?rid=|(?:[^/]+/))*(?P<id>[A-Za-z0-9]+)'
    _TESTS = [{
        'url': 'https://www.douyu.com/pigff',
        'info_dict': {
            'id': '24422',
            'display_id': 'pigff',
            'ext': 'mp4',
            'title': 're:^【PIGFF】.* [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'description': r'≥15级牌子看鱼吧置顶帖进粉丝vx群',
            'thumbnail': str,
            'uploader': 'pigff',
            'is_live': True,
            'live_status': 'is_live',
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

    def _get_sign_func(self, room_id, video_id):
        return self._download_json(
            f'https://www.douyu.com/swf_api/homeH5Enc?rids={room_id}', video_id,
            note='Getting signing script')['data'][f'room{room_id}']

    def _extract_stream_formats(self, stream_formats):
        formats = []
        for stream_info in traverse_obj(stream_formats, (..., 'data')):
            stream_url = urljoin(
                traverse_obj(stream_info, 'rtmp_url'), traverse_obj(stream_info, 'rtmp_live'))
            if stream_url:
                rate_id = traverse_obj(stream_info, ('rate', {int_or_none}))
                rate_info = traverse_obj(stream_info, ('multirates', lambda _, v: v['rate'] == rate_id), get_all=False)
                ext = determine_ext(stream_url)
                formats.append({
                    'url': stream_url,
                    'format_id': str_or_none(rate_id),
                    'ext': 'mp4' if ext == 'm3u8' else ext,
                    'protocol': 'm3u8_native' if ext == 'm3u8' else 'https',
                    'quality': rate_id % -10000 if rate_id is not None else None,
                    **traverse_obj(rate_info, {
                        'format': ('name', {str_or_none}),
                        'tbr': ('bit', {int_or_none}),
                    }),
                })
        return formats

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)
        room_id = self._search_regex(r'\$ROOM\.room_id\s*=\s*(\d+)', webpage, 'room id')

        if self._search_regex(r'"videoLoop"\s*:\s*(\d+)', webpage, 'loop', default='') == '1':
            raise UserNotLive('The channel is auto-playing VODs', video_id=video_id)
        if self._search_regex(r'\$ROOM\.show_status\s*=\s*(\d+)', webpage, 'status', default='') == '2':
            raise UserNotLive(video_id=video_id)

        # Grab metadata from API
        params = {
            'aid': 'wp',
            'client_sys': 'wp',
            'time': int(time.time()),
        }
        params['auth'] = hashlib.md5(
            f'room/{room_id}?{urllib.parse.urlencode(params)}zNzMV1y4EMxOHS6I5WKm'.encode()).hexdigest()
        room = traverse_obj(self._download_json(
            f'http://www.douyutv.com/api/v1/room/{room_id}', video_id,
            note='Downloading room info', query=params, fatal=False), 'data')

        # 1 = live, 2 = offline
        if traverse_obj(room, 'show_status') == '2':
            raise UserNotLive(video_id=video_id)

        js_sign_func = self._search_js_sign_func(webpage, fatal=False) or self._get_sign_func(room_id, video_id)
        form_data = {
            'rate': 0,
            **self._calc_sign(js_sign_func, video_id, room_id),
        }
        stream_formats = [self._download_json(
            f'https://www.douyu.com/lapi/live/getH5Play/{room_id}',
            video_id, note='Downloading livestream format',
            data=urlencode_postdata(form_data))]

        for rate_id in traverse_obj(stream_formats[0], ('data', 'multirates', ..., 'rate')):
            if rate_id != traverse_obj(stream_formats[0], ('data', 'rate')):
                form_data['rate'] = rate_id
                stream_formats.append(self._download_json(
                    f'https://www.douyu.com/lapi/live/getH5Play/{room_id}',
                    video_id, note=f'Downloading livestream format {rate_id}',
                    data=urlencode_postdata(form_data)))

        return {
            'id': room_id,
            'formats': self._extract_stream_formats(stream_formats),
            'is_live': True,
            **traverse_obj(room, {
                'display_id': ('url', {str}, {lambda i: i[1:]}),
                'title': ('room_name', {unescapeHTML}),
                'description': ('show_details', {str}),
                'uploader': ('nickname', {str}),
                'thumbnail': ('room_src', {url_or_none}),
            }),
        }


class DouyuShowIE(DouyuBaseIE):
    _VALID_URL = r'https?://v(?:mobile)?\.douyu\.com/show/(?P<id>[0-9a-zA-Z]+)'

    _TESTS = [{
        'url': 'https://v.douyu.com/show/mPyq7oVNe5Yv1gLY',
        'info_dict': {
            'id': 'mPyq7oVNe5Yv1gLY',
            'ext': 'mp4',
            'title': '四川人小时候的味道“蒜苗回锅肉”，传统菜不能丢，要常做来吃',
            'duration': 633,
            'thumbnail': str,
            'uploader': '美食作家王刚V',
            'uploader_id': 'OVAO4NVx1m7Q',
            'timestamp': 1661850002,
            'upload_date': '20220830',
            'view_count': int,
            'tags': ['美食', '美食综合'],
        },
    }, {
        'url': 'https://vmobile.douyu.com/show/rjNBdvnVXNzvE2yw',
        'only_matching': True,
    }]

    _FORMATS = {
        'super': '原画',
        'high': '超清',
        'normal': '高清',
    }

    _QUALITIES = {
        'super': -1,
        'high': -2,
        'normal': -3,
    }

    _RESOLUTIONS = {
        'super': '1920x1080',
        'high': '1280x720',
        'normal': '852x480',
    }

    def _real_extract(self, url):
        url = url.replace('vmobile.', 'v.')
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        video_info = self._search_json(
            r'<script>\s*window\.\$DATA\s*=', webpage,
            'video info', video_id, transform_source=js_to_json)

        js_sign_func = self._search_js_sign_func(webpage)
        form_data = {
            'vid': video_id,
            **self._calc_sign(js_sign_func, video_id, video_info['ROOM']['point_id']),
        }
        url_info = self._download_json(
            'https://v.douyu.com/api/stream/getStreamUrl', video_id,
            data=urlencode_postdata(form_data), note='Downloading video formats')

        formats = []
        for name, url in traverse_obj(url_info, ('data', 'thumb_video', {dict.items}, ...)):
            video_url = traverse_obj(url, ('url', {url_or_none}))
            if video_url:
                ext = determine_ext(video_url)
                formats.append({
                    'format': self._FORMATS.get(name),
                    'format_id': name,
                    'url': video_url,
                    'quality': self._QUALITIES.get(name),
                    'ext': 'mp4' if ext == 'm3u8' else ext,
                    'protocol': 'm3u8_native' if ext == 'm3u8' else 'https',
                    **parse_resolution(self._RESOLUTIONS.get(name)),
                })
            else:
                self.to_screen(
                    f'"{self._FORMATS.get(name, name)}" format may require logging in. {self._login_hint()}')

        return {
            'id': video_id,
            'formats': formats,
            **traverse_obj(video_info, ('DATA', {
                'title': ('content', 'title', {str}),
                'uploader': ('content', 'author', {str}),
                'uploader_id': ('content', 'up_id', {str_or_none}),
                'duration': ('content', 'video_duration', {int_or_none}),
                'thumbnail': ('content', 'video_pic', {url_or_none}),
                'timestamp': ('content', 'create_time', {int_or_none}),
                'view_count': ('content', 'view_num', {int_or_none}),
                'tags': ('videoTag', ..., 'tagName', {str}),
            })),
        }
