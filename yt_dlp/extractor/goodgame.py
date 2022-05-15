from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    int_or_none,
    traverse_obj,
)


class GoodGameIE(InfoExtractor):
    IE_NAME = 'goodgame:stream'
    _VALID_URL = r'https?://goodgame\.ru/channel/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://goodgame.ru/channel/LampaRPG',
        'info_dict': {
            'id': '156878',
            'ext': 'mp4',
            'title': r're:Рейтинговые герои \d{4}-\d{2}-\d{2} \d{2}:\d{2}$',
            'channel': 'Рейтинговые герои',
            'channel_id': 'LampaRPG',
            'channel_url': 'https://goodgame.ru/channel/LampaRPG',
            'description': 'md5:ca5faa69b5d9215afdc65caeca68e1f6',
            'thumbnail': r're:^https?://.*\.jpg$',
            'live_status': 'is_live',
            'view_count': int,
        },
        'params': {'skip_download': 'm3u8'},
        'skip': 'May not be online',
    }]

    def _real_extract(self, url):
        channel_name = self._match_id(url)
        response = self._download_json(f'https://api2.goodgame.ru/v2/streams/{channel_name}', channel_name)

        formats, subtitles = [], {}
        if response.get('status') == 'Live':
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                f'https://hls.goodgame.ru/manifest/{response["id"]}_master.m3u8',
                channel_name, 'mp4', live=True)
        else:
            self.raise_no_formats('User is offline', expected=True, video_id=channel_name)

        self._sort_formats(formats)
        return {
            'id': response['channel']['gg_player_src'],
            'formats': formats,
            'subtitles': subtitles,
            'title': traverse_obj(response, ('channel', 'title')),
            'channel': traverse_obj(response, ('channel', 'title')),
            'channel_id': channel_name,
            'channel_url': f'https://goodgame.ru/channel/{channel_name}',
            'description': clean_html(traverse_obj(response, ('channel', 'description'))),
            'thumbnail': traverse_obj(response, ('channel', 'thumb')),
            'is_live': True,
            'view_count': int_or_none(response.get('viewers')),
        }
