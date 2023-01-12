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
    try_get,
    url_or_none,
)


class MGTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:w(?:ww)?\.)?mgtv\.com/(v|b)/(?:[^/]+/)*(?P<id>\d+)\.html'
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
    }, {
        'url': 'https://w.mgtv.com/b/427837/15588271.html',
        'info_dict': {
            'id': '15588271',
            'ext': 'mp4',
            'title': '春日迟迟再出发 沉浸版',
            'description': 'md5:a7a05a05b1aa87bd50cae619b19bbca6',
            'thumbnail': r're:^https?://.+\.jpg',
            'duration': 4026,
        },
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

    def _real_extract(self, url):
        video_id = self._match_id(url)
        tk2 = base64.urlsafe_b64encode(
            f'did={str(uuid.uuid4())}|pno=1030|ver=0.3.0301|clit={int(time.time())}'.encode())[::-1]
        try:
            api_data = self._download_json(
                'https://pcweb.api.mgtv.com/player/video', video_id, query={
                    'tk2': tk2,
                    'video_id': video_id,
                    'type': 'pch5'
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
                'src': 'intelmgtv',
            }, headers=self.geo_verification_headers())['data']
        stream_domain = stream_data['stream_domain'][0]

        formats = []
        for idx, stream in enumerate(stream_data['stream']):
            stream_path = stream.get('url')
            if not stream_path:
                continue
            format_data = self._download_json(
                stream_domain + stream_path, video_id,
                note=f'Download video info for format #{idx}')
            format_url = format_data.get('info')
            if not format_url:
                continue
            tbr = int_or_none(stream.get('filebitrate') or self._search_regex(
                r'_(\d+)_mp4/', format_url, 'tbr', default=None))
            formats.append({
                'format_id': compat_str(tbr or idx),
                'url': url_or_none(format_url),
                'ext': 'mp4',
                'tbr': tbr,
                'protocol': 'm3u8_native',
                'http_headers': {
                    'Referer': url,
                },
                'format_note': stream.get('name'),
            })

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'description': info.get('desc'),
            'duration': int_or_none(info.get('duration')),
            'thumbnail': info.get('thumb'),
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
                'ext': 'srt'
            })
        return subtitles
