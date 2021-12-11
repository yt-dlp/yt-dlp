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
        print(formats)

        _TESTS = [{
            'url': 'https://fod.fujitv.co.jp/title/5d40/5d40810075',
            'info_dict': {
                'id': '5d40810075',
                'ext': 'mp4',
                'formats': [
                    {
                        'format_id': '800',
                        'format_index': None,
                        'url': 'https://fod-plus7.hls.wseod.stream.ne.jp/www08/fod-plus7/_definst_/mp4:video/56789/5d40/5d40810075me111e991.mp4/chunklist.m3u8',
                        'manifest_url': 'http://i.fod.fujitv.co.jp/abr/tv_us7.hls.wseod.stream.ne.jp/www08/fod-plus7/_definst_/mp4:video/56789/5d40/5d40810075me111e991.mp4/chunklist.m3u8', 'manifest_url': 'http://i.fod.fujitv.co.jp/abr/tv_android/5d40810075.m3u8',
                        'tbr': 800.0,
                        'ext': 'mp4',
                        'fps': None,
                        'protocol': 'm3u8_native',
                        'preference': None,
                        'quality': None,
                        'width': 640,
                        'height': 360,
                        'video_ext': 'mp4',
                        'audio_ext': 'none',
                        'vbr': 800.0,
                        'abr': 0.0,
                    },
                    {
                        'format_id': '4000',
                        'format_index': None,
                        'url': 'https://fod-plus7-high.hls.wseod.stream.ne.jp/www08/fod-plus7-high/_definst_/mp4:video/56789/5d40/5d40810075me112e991.mp4/chunklist.m3u8',
                        'manifest_url': 'http://i.fod.fujitv.co.jp/abr/tv_android/5d40810075.m3u8',
                        'tbr': 1200.0,
                        'ext': 'mp4',
                        'fps': None,
                        'protocol': 'm3u8_native',
                        'preference': None,
                        'quality': None,
                        'width': 1280,
                        'height': 720,
                        'video_ext': 'mp4',
                        'audio_ext': 'none',
                        'vbr': 1200.0,
                        'abr': 0.0
                    },
                    {
                        'format_id': '2000',
                        'format_index': None,
                        'url': 'https://fod-plus7-high.hls.wseod.stream.ne.jp/www08/fod-plus7-high/_definst_/mp4:video/56789/5d40/5d40810075me113e991.mp4/chunklist.m3u8',
                        'manifest_url': 'http://i.fod.fujitv.co.jp/abr/tv_android/5d40810075.m3u8',
                        'tbr': 2000.0,
                        'ext': 'mp4',
                        'fps': None,
                        'protocol': 'm3u8_native',
                        'preference': None,
                        'quality': None,
                        'width': 1280,
                        'height': 720,
                        'video_ext': 'mp4',
                        'audio_ext': 'none',
                        'vbr': 4000.0,
                        'abr': 0.0
                    },
                    {
                        'format_id': '4000',
                        'format_index': None,
                        'url': 'https://fod-plus7-high.hls.wseod.stream.ne.jp/www08/fod-plus7-high/_definst_/mp4:video/56789/5d40/5d40810075me115e991.mp4/chunklist.m3u8',
                        'manifest_url': 'http://i.fod.fujitv.co.jp/abr/tv_android/5d40810075.m3u8',
                        'tbr': 4000.0,
                        'ext': 'mp4',
                        'fps': None,
                        'protocol': 'm3u8_native',
                        'preference': None,
                        'quality': None,
                        'width': 1920,
                        'height': 1080,
                        'video_ext': 'mp4',
                        'audio_ext': 'none',
                        'vbr': 4000.0,
                        'abr': 0.0
                    }],
                'thumbnail': self._BASE_URL + 'pc/image/wbtn/wbtn_%s.jpg' % video_id,
            }
        }]

        return {
            'id': video_id,
            'title': video_id,
            'formats': formats,
            'thumbnail': self._BASE_URL + 'pc/image/wbtn/wbtn_%s.jpg' % video_id,
        }
