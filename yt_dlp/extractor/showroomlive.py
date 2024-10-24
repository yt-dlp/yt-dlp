from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    urljoin,
)


class ShowRoomLiveIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?showroom-live\.com/(?!onlive|timetable|event|campaign|news|ranking|room)(?P<id>[^/?#&]+)'
    _TEST = {
        'url': 'https://www.showroom-live.com/48_Nana_Okada',
        'only_matching': True,
    }

    def _real_extract(self, url):
        broadcaster_id = self._match_id(url)

        webpage = self._download_webpage(url, broadcaster_id)

        room_id = self._search_regex(
            (r'SrGlobal\.roomId\s*=\s*(\d+)',
             r'(?:profile|room)\?room_id\=(\d+)'), webpage, 'room_id')

        room = self._download_json(
            urljoin(url, f'/api/room/profile?room_id={room_id}'),
            broadcaster_id)

        is_live = room.get('is_onlive')
        if is_live is not True:
            raise ExtractorError(f'{broadcaster_id} is offline', expected=True)

        uploader = room.get('performer_name') or broadcaster_id
        title = room.get('room_name') or room.get('main_name') or uploader

        streaming_url_list = self._download_json(
            urljoin(url, f'/api/live/streaming_url?room_id={room_id}'),
            broadcaster_id)['streaming_url_list']

        formats = []
        for stream in streaming_url_list:
            stream_url = stream.get('url')
            if not stream_url:
                continue
            stream_type = stream.get('type')
            if stream_type == 'hls':
                m3u8_formats = self._extract_m3u8_formats(
                    stream_url, broadcaster_id, ext='mp4', m3u8_id='hls',
                    live=True)
                for f in m3u8_formats:
                    f['quality'] = int_or_none(stream.get('quality', 100))
                formats.extend(m3u8_formats)
            elif stream_type == 'rtmp':
                stream_name = stream.get('stream_name')
                if not stream_name:
                    continue
                formats.append({
                    'url': stream_url,
                    'play_path': stream_name,
                    'page_url': url,
                    'player_url': 'https://www.showroom-live.com/assets/swf/v3/ShowRoomLive.swf',
                    'rtmp_live': True,
                    'ext': 'flv',
                    'format_id': 'rtmp',
                    'format_note': stream.get('label'),
                    'quality': int_or_none(stream.get('quality', 100)),
                })

        return {
            'id': str(room.get('live_id') or broadcaster_id),
            'title': title,
            'description': room.get('description'),
            'timestamp': int_or_none(room.get('current_live_started_at')),
            'uploader': uploader,
            'uploader_id': broadcaster_id,
            'view_count': int_or_none(room.get('view_num')),
            'formats': formats,
            'is_live': True,
        }
