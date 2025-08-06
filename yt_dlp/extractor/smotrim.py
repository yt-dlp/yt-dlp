import re

from .common import InfoExtractor
from ..utils import ExtractorError, int_or_none
from ..utils.traversal import traverse_obj


class SmotrimIE(InfoExtractor):
    _VALID_URL = r'https?://smotrim\.ru/(?P<type>brand|video|article|live|channel)/(?P<id>[0-9]+)'
    _TESTS = [
        {
            'url': 'https://smotrim.ru/video/3003613',
            'info_dict': {
                'id': '3003613',
                'ext': 'mp4',
                'title': 'Погода. на 2 августа 2025 года',
                'thumbnail': r're:https?://cdn-st\d\.smotrim\.ru/vh/pictures/[a-z]{2}/\d+/\d+/\d+\.(?:jpg|png)',
                'subtitles': {},
                'is_live': False,
                'duration': 105,
            },
            'add_ie': ['RUTV'],
        },
        {
            'url': 'https://smotrim.ru/article/4609632',
            'info_dict': {
                'id': '3000761',
                'ext': 'mp4',
                'title': 'Новости культуры. Ольга Любимова провела рабочую встречу в Еврейской автономной области',
                'thumbnail': r're:https?://cdn-st\d\.smotrim\.ru/vh/pictures/[a-z]{2}/\d+/\d+/\d+\.(?:jpg|png)',
                'subtitles': {},
                'is_live': False,
                'duration': 69,
            },
            'add_ie': ['RUTV'],
        },
        {
            'url': 'https://smotrim.ru/brand/64356',
            'info_dict': {
                'id': '2885093',
                'ext': 'mp4',
                'title': 'Большие и маленькие. 6-й сезон 8-й выпуск',
                'thumbnail': r're:https?://cdn-st\d\.smotrim\.ru/vh/pictures/[a-z]{2}/\d+/\d+/\d+\.(?:jpg|png)',
                'subtitles': {},
                'is_live': False,
                'duration': 6622,
            },
            'add_ie': ['RUTV'],
        },
        {  # GEO RESTRICTED
            'url': 'https://smotrim.ru/live/19201',
            'info_dict': {
                'id': '381308c7-a066-4c4f-9656-83e2e792a7b4',
                'ext': 'mp4',
                'title': 'Россия К',
                'thumbnail': r're:https?://cdn-st\d\.smotrim\.ru/vh/pictures/[a-z]{2}/\d+/\d+/\d+\.(?:jpg|png)',
                'subtitles': {
                    'ru': [
                        {'url': 'https://vgtrkregion-reg.cdnvideo.ru/vgtrk/0/kultura-hd/track_2001_319a299f/chunklist.m3u8', 'ext': 'vtt', 'protocol': 'm3u8_native'},
                    ],
                },
                'is_live': True,
                'duration': None,
            },
            'add_ie': ['RUTV'],
        },
        {  # GEO RESTRICTED, REDIRECT FROM live, CANONICAL FOR live urls
            'url': 'https://smotrim.ru/channel/4',
            'info_dict': {
                'id': '4',
                'ext': 'mp4',
                'title': 'Россия К',
                'thumbnail': r're:https?://cdn-st\d\.smotrim\.ru/vh/pictures/[a-z]{2}/\d+/\d+/\d+\.(?:jpg|png)',
                'subtitles': {
                    'ru': [
                        {'url': 'https://vgtrkregion-reg.cdnvideo.ru/vgtrk/0/kultura-hd/track_2001_319a299f/chunklist.m3u8', 'ext': 'vtt', 'protocol': 'm3u8_native'},
                    ],
                },
                'is_live': True,
                'duration': None,
            },
            'add_ie': ['RUTV'],
        },
    ]

    def _real_extract(self, url):
        video_id, typ = self._match_valid_url(url).group('id', 'type')
        webpage = self._download_webpage(url, video_id, f'Resolving {typ} link')
        iframe_url = self._search_regex(
            r'<iframe\b[^>]+\bsrc=["\'](https?://player\.smotrim\.ru/iframe/[^"\']+)',
            webpage,
            'iframe URL',
        )
        if typ in {'live', 'channel'}:
            # iframe_url = 'https://player.smotrim.ru/iframe/live/uid/381308c7-a066-4c4f-9656-83e2e792a7b4/showZoomBtn/false/isPlay/true/mute/true/sid/smotrim_rk/'
            video_id = re.search(
                r'(?P<video_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})',
                iframe_url,
            )
            if not video_id:
                raise ExtractorError(
                    'There are no player uuid in this page.', expected=True,
                )
            video_id = video_id.group('video_id')
            jsondata_url = (
                f'https://player.smotrim.ru/iframe/datalive/uid/{video_id}/sid/smotrim'
            )
        else:
            # iframe_url = 'https://player.smotrim.ru/iframe/video/id/3000761/sid/smotrim/isPlay/true/mute/true/?acc_video_id=3204061'
            video_id = re.search(
                r'^https?://player\.smotrim\.ru/iframe/video/id/(?P<video_id>\d+)/sid/',
                iframe_url,
            )
            if not video_id:
                raise ExtractorError(
                    'There are no player id in this page.', expected=True,
                )
            video_id = video_id.group('video_id')
            jsondata_url = (
                f'https://player.smotrim.ru/iframe/datavideo/id/{video_id}/sid/smotrim'
            )
        try:
            json_info = self._download_json(
                jsondata_url, video_id, 'Downloading player config JSON metadata',
            )
        except Exception as e:
            raise ExtractorError(str(e), expected=True)
        if json_info.get('status') != 200:
            raise ExtractorError('Json download error. Status code: %s' % str(json_info.get('status')), expected=True)
        media_info = traverse_obj(json_info, ('data', 'playlist', 'medialist', 0))
        if not media_info:
            raise ExtractorError('Unable to get media_info', expected=True)
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            traverse_obj(media_info, ('sources', 'm3u8', 'auto')), video_id, 'mp4', m3u8_id='hls',
        )

        return {
            'id': video_id,
            'title': traverse_obj(media_info, ('title')),
            'thumbnail': traverse_obj(media_info, ('pictures', '16:9')),
            'formats': formats,
            'subtitles': subtitles,
            'is_live': traverse_obj(json_info, ('data', 'playlist', 'type')) == 'live',
            'duration': int_or_none(traverse_obj(media_info, ('duration'))),
        }
