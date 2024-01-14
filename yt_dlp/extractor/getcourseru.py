from .common import InfoExtractor
from ..utils import int_or_none, traverse_obj, url_or_none


class GetCourseRuIE(InfoExtractor):
    _VALID_URL = r'https?://[^.]+\.getcourse\.ru/sign-player/?\?(?:[^#]+&)?json=(?P<id>[^#&]+)'
    _TESTS = [{
        'url': 'http://player02.getcourse.ru/sign-player/?json=eyJ2aWRlb19oYXNoIjoiMTkwYmRmOTNmMWIyOTczNTMwOTg1M2E3YTE5ZTI0YjMiLCJ1c2VyX2lkIjozNTk1MjUxODMsInN1Yl9sb2dpbl91c2VyX2lkIjpudWxsLCJsZXNzb25faWQiOm51bGwsImlwIjoiNDYuMTQyLjE4Mi4yNDciLCJnY19ob3N0IjoiYWNhZGVteW1lbC5vbmxpbmUiLCJ0aW1lIjoxNzA1MjY2Njc2LCJwYXlsb2FkIjoidV8zNTk1MjUxODMiLCJ1aV9sYW5ndWFnZSI6InJ1IiwiaXNfaGF2ZV9jdXN0b21fc3R5bGUiOnRydWV9&s=0c5e0c6aef19da36add3135a162b8eba&vh-static-feature=zigzag',
        'info_dict': {
            'id': '4885302',
            'title': '190bdf93f1b29735309853a7a19e24b3',
            'ext': 'mp4',
            'duration': 1693
        },
        'skip': 'JWT expired',
    }]

    def _real_extract(self, url):
        webpage = self._download_webpage(url, None, 'Downloading player page')
        window_configs = self._search_json(
            r'window\.configs\s*=', webpage, 'config', None)
        video_id = str(window_configs['videoId'])
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            window_configs['masterPlaylistUrl'], video_id)

        return {
            **traverse_obj(window_configs, {
                'title': ('videoHash', {str}),
                'thumbnail': ('thumbnailUrl', {url_or_none}),
                'duration': ('videoDuration', {int_or_none}),
            }),
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles
        }
