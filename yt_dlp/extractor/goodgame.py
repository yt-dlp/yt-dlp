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
        'url': 'https://goodgame.ru/channel/Pomi',
        'info_dict': {
            'id': '1644',
            'ext': 'mp4',
            'title': r're:Clem vs Special \(bo3\) Wardi Spring EU \- playoff \(финальный день\) \d{4}-\d{2}-\d{2} \d{2}:\d{2}$',
            'channel': 'Clem vs Special (bo3) Wardi Spring EU - playoff (финальный день)',
            'channel_id': 'Pomi',
            'channel_url': 'https://goodgame.ru/channel/Pomi',
            'description': 'md5:7753f17d161c06af196401b0d5dae61e',
            'thumbnail': r're:^https?://.*\.jpg$',
            'live_status': 'is_live',
            'view_count': int,
        },
        'params': {'skip_download': 'm3u8'},
        # 'skip': 'May not be online',
    }]

    def _real_extract(self, url):
        channel_name = self._match_id(url)
        response = self._download_json(f'https://api2.goodgame.ru/v2/streams/{channel_name}', channel_name)
        player_id = traverse_obj(response, ('channel', 'gg_player_src'))

        formats, subtitles = [], {}
        if response.get('status') == 'Live':
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                f'https://hls.goodgame.ru/manifest/{player_id}_master.m3u8',
                channel_name, 'mp4', live=True)
        else:
            self.raise_no_formats('User is offline', expected=True, video_id=channel_name)

        self._sort_formats(formats)
        return {
            'id': str_or_none(response.get('id')),
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
