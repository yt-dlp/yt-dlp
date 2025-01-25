from .common import InfoExtractor
from ..utils import (
    int_or_none,
    sanitize_url,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class GoodGameIE(InfoExtractor):
    IE_NAME = 'goodgame:stream'
    _VALID_URL = r'https?://goodgame\.ru/(?:channel/)?(?P<id>[\w.*-]+)'
    _TESTS = [{
        'url': 'https://goodgame.ru/Pomi#autoplay',
        'info_dict': {
            'id': 'pomi',
            'ext': 'mp4',
            'title': r're:Reynor vs Special \(1/2,bo3\) Wardi Spring EU \- playoff \(финальный день\) \d{4}-\d{2}-\d{2} \d{2}:\d{2}$',
            'channel_id': '1644',
            'channel': 'Pomi',
            'channel_url': 'https://goodgame.ru/Pomi',
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
        response = self._download_json(f'https://goodgame.ru/api/4/users/{channel_name}/stream', channel_name)
        player_id = response['streamkey']

        formats, subtitles = [], {}
        if response.get('status'):
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                f'https://hls.goodgame.ru/manifest/{player_id}_master.m3u8',
                channel_name, 'mp4', live=True)
        else:
            self.raise_no_formats('User is offline', expected=True, video_id=channel_name)

        return {
            'id': player_id,
            'formats': formats,
            'subtitles': subtitles,
            'is_live': bool(formats),
            **traverse_obj(response, {
                'title': ('title', {str}),
                'channel': ('channelkey', {str}),
                'channel_id': ('id', {str_or_none}),
                'channel_url': ('link', {url_or_none}),
                'uploader': ('streamer', 'username', {str}),
                'uploader_id': ('streamer', 'id', {str_or_none}),
                'thumbnail': ('preview', {url_or_none}, {sanitize_url}),
                'concurrent_view_count': ('views', {int_or_none}),
                'channel_follower_count': ('followers', {int_or_none}),
                'age_limit': ('adult', {bool}, {lambda x: 18 if x else None}),
            }),
        }
