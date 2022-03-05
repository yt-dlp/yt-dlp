# coding: utf-8
from __future__ import unicode_literals

import base64
import time
import urllib.parse
import uuid

from .common import InfoExtractor
from ..utils import (
    try_get,
)


class MangotvIE(InfoExtractor):
    _VALID_URL = r'https?://w\.mgtv\.com/\D+\/\d+\/(?P<id>[^\/]+?)(?:\D|$)'
    IE_NAME = 'MangoTV'
    IE_DESC = 'mgtv.com'
    _TESTS = [{
        'url': 'https://w.mgtv.com/b/427837/15588271.html',
        'info_dict': {
            'id': '15588271',
            'ext': 'mp4',
            'title': '春日迟迟再出发 沉浸版',
            'description': 'md5:a7a05a05b1aa87bd50cae619b19bbca6',
            'thumbnail': r're:^https?://.+\.jpg',
        },
    }, {
        'url': 'https://w.mgtv.com/b/427837/15591647.html',
        'only_matching': True
    }, {
        'url': 'https://w.mgtv.com/b/388252/15634192.html?fpa=33318&fpos=4&lastp=ch_home',
        'only_matching': True
    }]
    _DOMAIN = 'https://w.mgtv.com/'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        tk2_token = bytearray(base64.b64encode(
            f'did={str(uuid.uuid4())}|pno=103040|ver=0.3.0301|clit={int(time.time())}'.encode()).translate(
            bytes.maketrans(b'+/=', b'_~-')))
        tk2_token.reverse()
        params = {
            'video_id': video_id,
            'tk2': tk2_token.decode(),
            'type': 'pch5'
        }
        info = self._download_json(f'https://pcweb.api.mgtv.com/player/video?{urllib.parse.urlencode(params)}',
                                   video_id=video_id)
        params.update({
            'pm2': try_get(info, lambda x: x['data']['atc']['pm2']),
            'src': 'intelmgtv'})
        data = self._download_json(f'https://pcweb.api.mgtv.com/player/getSource?{urllib.parse.urlencode(params)}',
                                   video_id=video_id)
        domain = try_get(data, lambda x: x['data']['stream_domain'][0])
        formats = []
        for stream in try_get(data, lambda x: x['data']['stream']):
            stream_url = stream.get('url')
            if not stream_url:
                continue
            url_m3u8 = try_get(self._download_json(f'{domain}{stream_url}', video_id=video_id), lambda x: x['info'])
            if not url_m3u8:
                continue
            formats.extend(
                self._extract_m3u8_formats(url_m3u8, video_id, headers={'Referer': self._DOMAIN},
                                           ext='mp4'))
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': try_get(info, lambda x: x['data']['info']['title']),
            'description': try_get(info, lambda x: x['data']['info']['desc']),
            'thumbnail': try_get(info, lambda x: x['data']['info']['thumb']),
            'formats': formats,
            'subtitles': self.get_all_subtitles(video_id=video_id, domain=domain),
            'http_headers': {'Referer': self._DOMAIN}
        }

    def get_all_subtitles(self, video_id, domain):
        info = self._download_json(f'https://pcweb.api.mgtv.com/video/title?videoId={video_id}', video_id=video_id)
        subtitles = {}
        for sub in try_get(info, lambda x: x['data']['title']):
            url_sub = sub.get('url')
            if not url_sub:
                continue
            locale = sub.get('captionCountrySimpleName').lower()
            subtitles[locale] = [{
                'url': try_get(
                    self._download_json(f'{domain}{url_sub}', video_id=video_id,
                                        note=f'Extract subtitle ({locale})'), lambda x: x['info']),
                'ext': 'srt'
            }]
        return subtitles
