import base64
import time
import uuid

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_resolution,
    traverse_obj,
    try_get,
    url_or_none,
    urljoin,
)


class MGTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:w(?:ww)?\.)?mgtv\.com/[bv]/(?:[^/]+/)*(?P<id>\d+)\.html'
    IE_DESC = '芒果TV'
    IE_NAME = 'MangoTV'

    _TESTS = [{
        'url': 'http://www.mgtv.com/v/1/290525/f/3116640.html',
        'info_dict': {
            'id': '3116640',
            'ext': 'mp4',
            'title': '我是歌手 第四季',
            'description': '我是歌手第四季双年巅峰会',
            'duration': 7461,
            'thumbnail': r're:^https?://.*\.jpg$',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://w.mgtv.com/b/427837/15588271.html',
        'info_dict': {
            'id': '15588271',
            'ext': 'mp4',
            'title': '春日迟迟再出发 沉浸版第1期：陆莹结婚半年查出肾炎被离婚 吴雅婷把一半票根退给前夫',
            'description': 'md5:a7a05a05b1aa87bd50cae619b19bbca6',
            'thumbnail': r're:^https?://.+\.jpg',
            'duration': 4026,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://w.mgtv.com/b/333652/7329822.html',
        'info_dict': {
            'id': '7329822',
            'ext': 'mp4',
            'title': '拜托，请你爱我',
            'description': 'md5:cd81be6499bafe32e4d143abd822bf9c',
            'thumbnail': r're:^https?://.+\.jpg',
            'duration': 2656,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://w.mgtv.com/b/427837/15591647.html',
        'only_matching': True,
    }, {
        'url': 'https://w.mgtv.com/b/388252/15634192.html?fpa=33318&fpos=4&lastp=ch_home',
        'only_matching': True,
    }, {
        'url': 'http://www.mgtv.com/b/301817/3826653.html',
        'only_matching': True,
    }, {
        'url': 'https://w.mgtv.com/b/301817/3826653.html',
        'only_matching': True,
    }]

    _RESOLUTIONS = {
        '标清': ('480p', '854x480'),
        '高清': ('540p', '960x540'),
        '超清': ('720p', '1280x720'),
        '蓝光': ('1080p', '1920x1080'),
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        tk2 = base64.urlsafe_b64encode(
            f'did={uuid.uuid4()}|pno=1030|ver=0.3.0301|clit={int(time.time())}'.encode())[::-1]
        try:
            api_data = self._download_json(
                'https://pcweb.api.mgtv.com/player/video', video_id, query={
                    'tk2': tk2,
                    'video_id': video_id,
                    'type': 'pch5',
                }, headers=self.geo_verification_headers())['data']
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 401:
                error = self._parse_json(e.cause.response.read().decode(), None)
                if error.get('code') == 40005:
                    self.raise_geo_restricted(countries=self._GEO_COUNTRIES)
                raise ExtractorError(error['msg'], expected=True)
            raise

        stream_data = self._download_json(
            'https://pcweb.api.mgtv.com/player/getSource', video_id, query={
                'tk2': tk2,
                'pm2': api_data['atc']['pm2'],
                'video_id': video_id,
                'type': 'pch5',
                'src': 'intelmgtv',
            }, headers=self.geo_verification_headers())['data']
        stream_domain = traverse_obj(stream_data, ('stream_domain', ..., {url_or_none}), get_all=False)

        formats = []
        for idx, stream in enumerate(traverse_obj(stream_data, ('stream', lambda _, v: v['url']))):
            stream_name = traverse_obj(stream, 'name', 'standardName', 'barName', expected_type=str)
            resolution = traverse_obj(
                self._RESOLUTIONS, (stream_name, 1 if stream.get('scale') == '16:9' else 0))
            format_url = traverse_obj(self._download_json(
                urljoin(stream_domain, stream['url']), video_id, fatal=False,
                note=f'Downloading video info for format {resolution or stream_name}'),
                ('info', {url_or_none}))
            if not format_url:
                continue
            tbr = int_or_none(stream.get('filebitrate') or self._search_regex(
                r'_(\d+)_mp4/', format_url, 'tbr', default=None))
            formats.append({
                'format_id': str(tbr or idx),
                'url': format_url,
                'ext': 'mp4',
                'tbr': tbr,
                'vcodec': stream.get('videoFormat'),
                'acodec': stream.get('audioFormat'),
                **parse_resolution(resolution),
                'protocol': 'm3u8_native',
                'http_headers': {
                    'Referer': url,
                },
                'format_note': stream_name,
            })

        return {
            'id': video_id,
            'formats': formats,
            **traverse_obj(api_data, ('info', {
                'title': ('title', {str.strip}),
                'description': ('desc', {str}),
                'duration': ('duration', {int_or_none}),
                'thumbnail': ('thumb', {url_or_none}),
            })),
            'subtitles': self.extract_subtitles(video_id, stream_domain),
        }

    def _get_subtitles(self, video_id, domain):
        info = self._download_json(f'https://pcweb.api.mgtv.com/video/title?videoId={video_id}',
                                   video_id, fatal=False) or {}
        subtitles = {}
        for sub in try_get(info, lambda x: x['data']['title']) or []:
            url_sub = sub.get('url')
            if not url_sub:
                continue
            locale = sub.get('captionSimpleName') or 'en'
            sub = self._download_json(f'{domain}{url_sub}', video_id, fatal=False,
                                      note=f'Download subtitle for locale {sub.get("name")} ({locale})') or {}
            sub_url = url_or_none(sub.get('info'))
            if not sub_url:
                continue
            subtitles.setdefault(locale.lower(), []).append({
                'url': sub_url,
                'name': sub.get('name'),
                'ext': 'srt',
            })
        return subtitles
