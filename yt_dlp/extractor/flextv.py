from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    UserNotLive,
    parse_iso8601,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class FlexTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?flextv\.co\.kr/channels/(?P<id>\d+)/live'
    _TESTS = [{
        'url': 'https://www.flextv.co.kr/channels/231638/live',
        'info_dict': {
            'id': '231638',
            'ext': 'mp4',
            'title': r're:^214하나만\.\.\. ',
            'thumbnail': r're:^https?://.+\.jpg',
            'upload_date': r're:\d{8}',
            'timestamp': int,
            'live_status': 'is_live',
            'channel': 'Hi별',
            'channel_id': '244396',
        },
        'skip': 'The channel is offline',
    }, {
        'url': 'https://www.flextv.co.kr/channels/746/live',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        channel_id = self._match_id(url)

        try:
            stream_data = self._download_json(
                f'https://api.flextv.co.kr/api/channels/{channel_id}/stream',
                channel_id, query={'option': 'all'})
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 400:
                raise UserNotLive(video_id=channel_id)
            raise

        playlist_url = stream_data['sources'][0]['url']
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            playlist_url, channel_id, 'mp4')

        return {
            'id': channel_id,
            'formats': formats,
            'subtitles': subtitles,
            'is_live': True,
            **traverse_obj(stream_data, {
                'title': ('stream', 'title', {str}),
                'timestamp': ('stream', 'createdAt', {parse_iso8601}),
                'thumbnail': ('thumbUrl', {url_or_none}),
                'channel': ('owner', 'name', {str}),
                'channel_id': ('owner', 'id', {str_or_none}),
            }),
        }
