# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class FujiTVFODPlus7IE(InfoExtractor):
    _VALID_URL = r'https?://fod\.fujitv\.co\.jp/title/(?P<sid>[0-9a-z]{4})/(?P<id>[0-9a-z]+)'
    _BASE_URL = 'https://i.fod.fujitv.co.jp/'

    _TESTS = [{
        'url': 'https://fod.fujitv.co.jp/title/5d40/5d40110076',
        'info_dict': {
            'id': '5d40110076',
            'ext': 'mp4',
            'title': '#1318 『まる子、まぼろしの洋館を見る』の巻',
            'series': 'ちびまる子ちゃん',
            'series_id': '5d40',
            'description': 'md5:b3f51dbfdda162ac4f789e0ff4d65750',
            'thumbnail': 'https://i.fod.fujitv.co.jp/img/program/5d40/episode/5d40110076_a.jpg',
        },
    }]

    def _real_extract(self, url):
        series_id, video_id = self._match_valid_url(url).groups()
        self._download_webpage(url, video_id)
        json_info = {}
        token = self._get_cookies(url).get('CT')
        if token:
            json_info = self._download_json('https://fod-sp.fujitv.co.jp/apps/api/episode/detail/?ep_id=%s&is_premium=false' % video_id, video_id, headers={'x-authorization': f'Bearer {token.value}'}, fatal=False)
        else:
            self.report_warning('Unable to extract token cookie, video information is unavailable')
            print(self._LOGIN_HINTS['cookies'])
        formats = []
        subtitles = []
        src_json = self._download_json(self._BASE_URL + 'abrjson_v2/tv_android/%s' % video_id, video_id)
        for src in src_json.get('video_selector'):
            format, subtitle = self._extract_m3u8_formats_and_subtitles(src.get('url'), video_id, 'mp4')
            formats += format
            subtitles += subtitle
        self._sort_formats(formats, ['tbr'])

        return {
            'id': video_id,
            'title': json_info.get('ep_title'),
            'series': json_info.get('lu_title'),
            'series_id': series_id,
            'description': json_info.get('ep_description'),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': self._BASE_URL + f'img/program/{series_id}/episode/{video_id}_a.jpg',
        }
