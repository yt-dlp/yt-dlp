import enum
import functools
import re
import time

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
)


class EventStatus(enum.Enum):
    NOT_STARTED = enum.auto()
    STARTED = enum.auto()
    REPLAY = enum.auto()
    ENDED = enum.auto()
    UNKNOWN = enum.auto()


class PeatixIE(InfoExtractor):
    IE_NAME = 'peatix.com'

    _VALID_URL = r'(?P<root_url>https?://peatix\.com)/event/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://peatix.com/event/4204947',
        'info_dict': {
            'id': '4204947',
            'title': '『本』と『声』TOKYO BOOK NIGHT2024 人気好評につき【疑似ライブ配信】決定！ | Peatix',
            'thumbnail': 'https://cdn.peatix.com/event/4204947/cover-zTJjkvKwSeRkONN49kTbhqcHw8swHlLC.png',
            'description': '申し込み開始：11月27日（水）より 申し込み締切：12月8日（日）20時販売終了 &nbsp; 大好評につき疑似ライブ配信決定！『本』と『声』TOKYO BOOK NIGHT 2... powered by Peatix : More than a ticket.',
        },
    }]

    def _extract_var(self, variable, html):
        var = self._search_regex(
            rf'(?:var|let|const)\s+{variable}\s*=\s*(?P<value>([^;]+))\s*;?',
            html, f'variable {variable}', group='value')
        return var[1:-1] if (var.startswith('"') and var.endswith('"')) or (var.startswith("'") and var.startswith('"')) else var

    def get_player_status(self, broadcast_info, webpage):
        """
        broadcast_info: Dict[str, Union[int, str]]
        A dictionary containing event data with the following keys:
        - 'started': int - Status indicating the start state (0 or 1)
        - 'event_tz_name': str - Time zone name, e.g., 'Asia/Tokyo'
        - 'go_live_epoch': int - Timestamp indicating when the live stream will start
        - 'ended': int - Status indicating the end state (0 or 1)
        - 'event_start_epoch': int - Epoch time for event start
        - 'end_live_epoch': int - Timestamp indicating the end of the live stream
        - 'event_end_epoch': int - Epoch time for event end
        - 'is_streaming_software_connected': int - Connection status of streaming software (0 or 1)
        """
        now = int(time.time())
        go_live_epoch = broadcast_info['go_live_epoch'] / 1000
        event_start_epoch = broadcast_info['event_start_epoch'] / 1000
        end_live_epoch = broadcast_info['end_live_epoch'] / 1000
        event_end_epoch = broadcast_info['event_end_epoch'] / 1000
        if now < go_live_epoch or now < event_start_epoch:
            return EventStatus.NOT_STARTED
        if now > end_live_epoch or now > event_end_epoch:
            if self._extract_var('replay_enabled', webpage) == 'parseInt("1")':
                replay_period_hr = re.findall(r'(\d+)', self._extract_var('replay_period_hr', webpage))
                if now < event_end_epoch + functools.reduce(lambda x, y: x * y, map(int, replay_period_hr)) * 3600:
                    return EventStatus.REPLAY
            return EventStatus.ENDED
        if (now >= go_live_epoch or now >= event_start_epoch) and (now <= end_live_epoch or now <= event_end_epoch):
            return EventStatus.STARTED
        return EventStatus.UNKNOWN

    def _real_extract(self, url):
        video_id, root_url = self._match_valid_url(url).group('id', 'root_url')
        event_webpage = self._download_webpage(f'{root_url}/event/{video_id}', video_id)
        player_webpage = self._download_webpage(f'{root_url}/event/{video_id}/watch_live', video_id,
                                                note='Downloading player information', errnote='Failed to download player information')
        try:
            state = self.get_player_status(self._download_json(f'{root_url}/event/{video_id}/broadcast_info', video_id)['json_data'], player_webpage)

        except ExtractorError as e:
            raise ExtractorError(e.msg, video_id=video_id)

        if state == EventStatus.NOT_STARTED:
            raise ExtractorError('The event has not started yet', expected=True, video_id=video_id)
        if state == EventStatus.ENDED:
            raise ExtractorError('The event has ended', expected=True, video_id=video_id)
        if state == EventStatus.UNKNOWN:
            raise ExtractorError('The event status is unknown', video_id=video_id)

        if state == EventStatus.REPLAY:
            m3u8_url = f'https://live-play.peatix.com/event{video_id}.m3u8'
        if state == EventStatus.STARTED:
            m3u8_url = f'https://live-play.peatix.com/live2/streams/{video_id}.m3u8?v={int(time.time() * 1000)}'

        manifest = self._download_webpage(
            m3u8_url, video_id, headers={'Referer': root_url}, note='Downloading m3u8 information', errnote='Failed to download m3u8 information')
        formats, _ = self._parse_m3u8_formats_and_subtitles(
            manifest, m3u8_url, 'mp4', m3u8_id='hls', video_id=video_id)

        return {
            'id': video_id,
            'title': self._html_extract_title(event_webpage) or self._html_search_meta(['og:title', 'twitter:title'], event_webpage, 'title', default=None),
            'thumbnail': self._html_search_meta(
                ['twitter:image', 'og:image'],
                event_webpage, 'thumbnail', default=None),
            'description': self._html_search_meta(
                ['description', 'twitter:description', 'og:description'],
                event_webpage, 'description', default=None),
            'formats': formats,
        }
