import datetime as dt
import json

from .common import InfoExtractor
from ..utils import (
    UserNotLive,
    clean_html,
    extract_attributes,
    int_or_none,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import (
    find_element,
    require,
    traverse_obj,
)


class ShowRoomBaseIE(InfoExtractor):
    _API_BASE = 'https://www.showroom-live.com/api'


class ShowRoomLiveIE(ShowRoomBaseIE):
    IE_NAME = 'showroom:live'
    IE_DESC = 'SHOWROOM'

    _VALID_URL = r'https?://(?:www\.)?showroom-live\.com/r/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.showroom-live.com/r/48_Yui_Oguri',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        broadcaster_id = self._match_id(url)
        room_status = self._download_json(
            f'{self._API_BASE}/room/status', broadcaster_id,
            query={'room_url_key': broadcaster_id})
        start_timestamp = traverse_obj(room_status, ('started_at', {int_or_none}))
        is_live = traverse_obj(room_status, ('is_live', {bool}))

        if not is_live:
            if start_timestamp:
                start_time = dt.datetime.fromtimestamp(
                    start_timestamp, dt.timezone.utc,
                ).astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')

                self.raise_no_formats(
                    f'Next livestream is scheduled to start at {start_time}', expected=True)

                return {
                    'id': broadcaster_id,
                    'live_status': 'is_upcoming',
                    'release_timestamp': start_timestamp,
                }
            raise UserNotLive(video_id=broadcaster_id)

        room_id = traverse_obj(room_status, ('room_id', {str_or_none}))
        room_profile = self._download_json(
            f'{self._API_BASE}/room/profile',
            broadcaster_id, query={'room_id': room_id})
        room_name = traverse_obj(room_profile, (
            ('room_name', 'main_name'), {clean_html}, filter, any))

        streaming_url_list = self._download_json(
            f'{self._API_BASE}/live/streaming_url',
            broadcaster_id, query={'room_id': room_id})
        m3u8_url = traverse_obj(streaming_url_list, (
            'streaming_url_list', lambda _, v: v['type'] == 'hls_all',
            'url', {url_or_none}, any, {require('m3u8 URL')}))

        return {
            'title': room_name,
            'channel': room_name,
            'channel_id': broadcaster_id,
            'formats': self._extract_m3u8_formats(m3u8_url, broadcaster_id, 'mp4'),
            'is_live': is_live,
            'release_timestamp': start_timestamp,
            **traverse_obj(room_profile, {
                'id': ('live_id', {str_or_none}),
                'channel_follower_count': ('follower_num', {int_or_none}),
                'channel_is_verified': ('is_official', {bool}),
                'description': ('description', {clean_html}, filter),
                'genres': ('genre_name', {clean_html}, filter, all, filter),
                'tags': ('live_tags', ..., 'name', {clean_html}, filter, all, filter),
                'thumbnail': (('image_square', 'image'), {url_or_none}, any),
                'view_count': ('view_num', {int_or_none}),
            }),
        }


class ShowRoomVodIE(ShowRoomBaseIE):
    IE_NAME = 'showroom:vod'

    _VALID_URL = r'https?://(?:www\.)?showroom-live\.com/episode/watch\?(?:[^#]+&)?id=(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://www.showroom-live.com/episode/watch?id=214',
        'info_dict': {
            'id': '214',
            'ext': 'mp4',
            'title': 'aaa',
        },
    }]

    def _real_extract(self, url):
        episode_id = self._match_id(url)
        webpage = self._download_webpage(url, episode_id)
        episode_data = traverse_obj(webpage, (
            {find_element(id='episode-data', html=True)},
            {extract_attributes}, 'data-episode', {json.loads}, {dict}))

        streaming_url_list = self._download_json(
            f'{self._API_BASE}/episode/streaming_url',
            episode_id, query={'episode_id': episode_id})
        m3u8_url = traverse_obj(streaming_url_list, (
            'streaming_url_list', 'hls_all',
            'hls_all', {url_or_none}, {require('m3u8 URL')}))

        return {
            'id': episode_id,
            'formats': self._extract_m3u8_formats(m3u8_url, episode_id, 'mp4'),
            'thumbnail': traverse_obj(streaming_url_list, ('thumbnail_url', {url_or_none})),
            **traverse_obj(episode_data, {
                'title': ('title', {clean_html}, filter),
                'description': ('description', {clean_html}, filter),
                'duration': ('video_time', {int_or_none}),
                'timestamp': ('display_started_at', {int_or_none}),
            }),
            **traverse_obj(episode_data, ('series', {
                'series': ('name', {clean_html}, filter),
                'series_id': ('id', {str_or_none}),
            })),
        }
