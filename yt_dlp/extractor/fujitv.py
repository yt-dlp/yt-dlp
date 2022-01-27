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
        'url': 'https://fod.fujitv.co.jp/title/5d40/5d40810081',
        'info_dict': {
            'id': '5d40810081',
            'title': '#1323 『まぼろしの「ツチノコ株式会社」』の巻',
            'description': 'md5:c7b39106e5dd4891f67cc858585d1b0c',
            'series_id': '5d40',
            'series': 'ちびまる子ちゃん',
            'thumbnail': 'http://i.fod.fujitv.co.jp/img/program/5d40/episode/5d40810081_a.jpg',
            'ext': 'mp4',
        },
        'params': {
            'skip_download': True
        },
    }]

    def _real_extract(self, url):
        series_id, video_id = self._match_valid_url(url).groups()
        self._download_webpage(url, video_id)
        json_info = {}
        if self._get_cookies(url).get('CT'):
            token = self._get_cookies(url).get('CT').value
            json_info = self._download_json('https://fod-sp.fujitv.co.jp/apps/api/episode/detail/?ep_id=%s&is_premium=false' % video_id,
                                            video_id, headers={'x-authorization': f'Bearer {token}'}, fatal=False)
        else:
            self.report_warning('Unable to extract token cookie, video information is unavailable')
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            self._BASE_URL + 'abr/tv_android/%s.m3u8' % video_id, video_id, 'mp4')
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
            'title': json_info.get('ep_title'),
            'series': json_info.get('lu_title'),
            'series_id': series_id,
            'description': json_info.get('ep_description'),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': f'{self._BASE_URL}img/program/{series_id}/episode/{video_id}_a.jpg',
        }
