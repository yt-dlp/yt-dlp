# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class FujiTVFODPlus7IE(InfoExtractor):
    _VALID_URL = r'https?://fod\.fujitv\.co\.jp/title/[0-9a-z]{4}/(?P<id>[0-9a-z]+)'
    _BASE_URL = 'http://i.fod.fujitv.co.jp/'
    _BITRATE_MAP = {
        300: (320, 180),
        800: (640, 360),
        1200: (1280, 720),
        2000: (1280, 720),
        4000: (1920, 1080),
    }

    _TESTS = [{
        'url': 'https://fod.fujitv.co.jp/title/5d40/5d40810075',
        'info_dict': {
            'id': '5d40810075',
            'title': '5d40810075',
            'ext': 'mp4',
            'format_id': '4000',
            'thumbnail': 'http://i.fod.fujitv.co.jp/pc/image/wbtn/wbtn_5d40810075.jpg'
        },
        'skip': 'Expires after a week'
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        formats = self._extract_m3u8_formats(
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
            'title': video_id,
            'formats': formats,
            'thumbnail': self._BASE_URL + 'pc/image/wbtn/wbtn_%s.jpg' % video_id,
        }
