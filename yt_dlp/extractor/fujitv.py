# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class FujiTVFODPlus7IE(InfoExtractor):
    _VALID_URL = r'https?://i\.fod\.fujitv\.co\.jp/plus7/web/[0-9a-z]{4}/(?P<id>[0-9a-z]+)'
    _BASE_URL = 'http://i.fod.fujitv.co.jp/'
    _BITRATE_MAP = {
        300: (320, 180),
        800: (640, 360),
        1200: (1280, 720),
        2000: (1280, 720),
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        formats = self._extract_m3u8_formats(
            self._BASE_URL + 'abr/pc_html5/%s.m3u8' % video_id, video_id)
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
