# coding: utf-8
from __future__ import unicode_literals

import base64
import time
import uuid

from .common import InfoExtractor
from ..compat import (
    compat_HTTPError,
    compat_str,
)
from ..utils import (
    ExtractorError,
    int_or_none,
)


class MGTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:w(?:ww)?\.)?mgtv\.com/(v|b)/(?:[^/]+/)*(?P<id>\d+)\.html'
    IE_DESC = '芒果TV'

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
    }, {
        'url': 'http://www.mgtv.com/b/301817/3826653.html',
        'only_matching': True,
    }, {
        'url': 'https://w.mgtv.com/b/301817/3826653.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        tk2 = base64.urlsafe_b64encode(b'did=%s|pno=1030|ver=0.3.0301|clit=%d' % (compat_str(uuid.uuid4()).encode(), time.time()))[::-1]
        try:
            api_data = self._download_json(
                'https://pcweb.api.mgtv.com/player/video', video_id, query={
                    'tk2': tk2,
                    'video_id': video_id,
                }, headers=self.geo_verification_headers())['data']
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 401:
                error = self._parse_json(e.cause.read().decode(), None)
                if error.get('code') == 40005:
                    self.raise_geo_restricted(countries=self._GEO_COUNTRIES)
                raise ExtractorError(error['msg'], expected=True)
            raise
        info = api_data['info']
        title = info['title'].strip()
        stream_data = self._download_json(
            'https://pcweb.api.mgtv.com/player/getSource', video_id, query={
                'pm2': api_data['atc']['pm2'],
                'tk2': tk2,
                'video_id': video_id,
            }, headers=self.geo_verification_headers())['data']
        stream_domain = stream_data['stream_domain'][0]

        formats = []
        for idx, stream in enumerate(stream_data['stream']):
            stream_path = stream.get('url')
            if not stream_path:
                continue
            format_data = self._download_json(
                stream_domain + stream_path, video_id,
                note='Download video info for format #%d' % idx)
            format_url = format_data.get('info')
            if not format_url:
                continue
            tbr = int_or_none(stream.get('filebitrate') or self._search_regex(
                r'_(\d+)_mp4/', format_url, 'tbr', default=None))
            formats.append({
                'format_id': compat_str(tbr or idx),
                'url': format_url,
                'ext': 'mp4',
                'tbr': tbr,
                'protocol': 'm3u8_native',
                'http_headers': {
                    'Referer': url,
                },
                'format_note': stream.get('name'),
            })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'description': info.get('desc'),
            'duration': int_or_none(info.get('duration')),
            'thumbnail': info.get('thumb'),
        }
