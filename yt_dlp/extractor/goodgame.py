from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    str_or_none,
    traverse_obj,
)


class GoodGameIE(InfoExtractor):
    IE_NAME = 'goodgame:stream'
    _VALID_URL = r'https?://goodgame\.ru/channel/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://goodgame.ru/channel/Pomi/#autoplay',
        'info_dict': {
            'id': 'pomi',
            'ext': 'mp4',
            'title': r're:Reynor vs Special \(1/2,bo3\) Wardi Spring EU \- playoff \(финальный день\) \d{4}-\d{2}-\d{2} \d{2}:\d{2}$',
            'channel_id': '1644',
            'channel': 'Pomi',
            'channel_url': 'https://goodgame.ru/channel/Pomi/',
            'description': 'md5:4a87b775ee7b2b57bdccebe285bbe171',
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
        player_id = response['channel']['gg_player_src']

        formats, subtitles = [], {}
        if response.get('status') == 'Live':
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                f'https://hls.goodgame.ru/manifest/{player_id}_master.m3u8',
                channel_name, 'mp4', live=True)
        else:
            self.raise_no_formats('User is offline', expected=True, video_id=channel_name)

        return {
            'id': player_id,
            'formats': formats,
            'subtitles': subtitles,
            'title': traverse_obj(response, ('channel', 'title')),
            'channel': channel_name,
            'channel_id': str_or_none(traverse_obj(response, ('channel', 'id'))),
            'channel_url': response.get('url'),
            'description': clean_html(traverse_obj(response, ('channel', 'description'))),
            'thumbnail': traverse_obj(response, ('channel', 'thumb')),
            'is_live': bool(formats),
            'view_count': int_or_none(response.get('viewers')),
            'age_limit': 18 if traverse_obj(response, ('channel', 'adult')) else None,
        }
