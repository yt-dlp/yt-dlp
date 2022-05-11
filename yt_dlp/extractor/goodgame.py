from .common import InfoExtractor
from ..utils import (
    clean_html,
    traverse_obj,
    ExtractorError,
)


class GoodGameIE(InfoExtractor):
    IE_NAME = 'goodgame:stream'
    _VALID_URL = r'https?://goodgame\.ru/channel/(?P<id>[a-zA-Z0-9_]+)'
    _TESTS = [{
        'url': 'https://goodgame.ru/channel/LampaRPG',
        'info_dict': {
            'id': '156878',
            'ext': 'mp4',
            'title': r're:Рейтинговые герои \d{4}-\d{2}-\d{2} \d{2}:\d{2}$',
            'description': 'md5:ca5faa69b5d9215afdc65caeca68e1f6',
            'thumbnail': r're:^https?://.*\.jpg$',
            'is_live': True,
            'live_status': 'is_live',
            'view_count': int,
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        channel_name = self._match_id(url)

        response = self._download_json(f'https://api2.goodgame.ru/v2/streams/{channel_name}', channel_name)

        if response.get('status') != 'Live':
            raise ExtractorError(f'{channel_name} is offline', expected=True)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            f'https://hls.goodgame.ru/manifest/{response.get("id")}_master.m3u8',
            channel_name, 'mp4', m3u8_id='hls', live=True)
        self._sort_formats(formats)

        return {
            'id': traverse_obj(response, ('channel', 'gg_player_src')) or channel_name,
            'formats': formats,
            'subtitles': subtitles,
            'title': traverse_obj(response, ('channel', 'title')),
            'description': clean_html(traverse_obj(response, ('channel', 'description'))),
            'thumbnail': traverse_obj(response, ('channel', 'thumb')),
            'is_live': True,
            'view_count': int(response.get('viewers', 0)),
        }
