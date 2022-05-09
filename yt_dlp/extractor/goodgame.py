from .common import InfoExtractor
from ..utils import clean_html, traverse_obj

_GOODGAME_API = 'https://api2.goodgame.ru/v2'
_GOODGAME_HLS = 'https://hls.goodgame.ru'


class GoodGameIE(InfoExtractor):
    IE_NAME = 'goodgame:stream'
    _VALID_URL = r'https?://goodgame\.ru/channel/(?P<id>[a-zA-Z0-9_]+)'
    _TESTS = [{
        'url': 'https://goodgame.ru/channel/Kochevnik',
        'info_dict': {
            'id': 'Kochevnik',
            'ext': 'mp4',
            'title': 'Кочетятр',
            'description': '',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }]

    def _real_extract(self, url):
        channel_id = self._match_id(url)

        gg = self._download_json(f'https://api2.goodgame.ru/v2/streams/{channel_id}', channel_id)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            f'https://hls.goodgame.ru/manifest/{gg["id"]}_master.m3u8',
            channel_id, 'mp4', m3u8_id='hls', live=True)
        self._sort_formats(formats)

        return {
            'id': channel_id,
            'formats': formats,
            'subtitles': subtitles,
            'title': traverse_obj(gg, ('channel', 'title')),
            'description': clean_html(traverse_obj(gg, ('channel', 'description'))),
            'thumbnail': traverse_obj(gg, ('channel', 'thumb')),
            'is_live': True,
        }
