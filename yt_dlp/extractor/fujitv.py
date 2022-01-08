# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class FujiTVFODPlus7IE(InfoExtractor):
    _VALID_URL = r'https?://fod\.fujitv\.co\.jp/title/(?P<sid>[0-9a-z]{4})/(?P<id>[0-9a-z]+)'
    _BASE_URL = 'http://i.fod.fujitv.co.jp/'
    _BITRATE_MAP = {
        300: (320, 180),
        800: (640, 360),
        1200: (1280, 720),
        2000: (1280, 720),
        4000: (1920, 1080),
    }

    _TESTS = [{
        'url': 'https://fod.fujitv.co.jp/title/5d40/5d40810076',
        'info_dict': {
            'id': '5d40810076',
            'ext': 'mp4',
            'title': '#1318 『まる子、まぼろしの洋館を見る』の巻',
            'series': 'ちびまる子ちゃん',
            'series_id': '5d40',
            'description': 'md5:b3f51dbfdda162ac4f789e0ff4d65750',
            'thumbnail': 'http://i.fod.fujitv.co.jp/img/program/5d40/episode/5d40810076_a.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        series_id = self._match_valid_url(url).group('sid')
        self._download_webpage(url, video_id)
        # TODO: extract thumbnail from webpage
        # then remove trim part using regexp: \/(imf\/.*)\/img
        # where the thumbnail is a img element with id of 'thumbnail'
        formats = self._extract_m3u8_formats(
            self._BASE_URL + 'abr/tv_android/%s.m3u8' % video_id, video_id, 'mp4')
        json_info={}
        if not self._get_cookies(url).get('CT'):
            token = self._get_cookies(url).get('CT').value
            json_info = self._download_json('https://fod-sp.fujitv.co.jp/apps/api/episode/detail/?ep_id=%s&is_premium=false' % video_id, video_id, headers={'x-authorization': f'Bearer {token}'}, fatal=False)
        else: 
            self._report_warning("Unable to extract token cookie, video information is unavailable")
        for f in formats:
            wh = self._BITRATE_MAP.get(f.get('tbr'))
            if wh:
                f.update({
                    'width': wh[0],
                    'height': wh[1],
                })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': json_info.get('ep_title') or video_id,
            'series': json_info.get('lu_title'),
            'series_id': series_id,
            'description': json_info.get('ep_description'),
            'formats': formats,
            'thumbnail': self._BASE_URL + f'img/program/{series_id}/episode/{video_id}_a.jpg',
        }
