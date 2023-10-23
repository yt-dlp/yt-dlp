from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    try_call,
    unified_timestamp,
)


class EplusIbIE(InfoExtractor):
    IE_NAME = 'eplus:inbound'
    IE_DESC = 'e+ (イープラス) overseas'
    _VALID_URL = r'https?://live\.eplus\.jp/ex/player\?ib=(?P<id>(?:\w|%2B|%2F){86}%3D%3D)'
    _TESTS = [{
        'url': 'https://live.eplus.jp/ex/player?ib=YEFxb3Vyc2Dombnjg7blkrLlrablnJLjgrnjgq%2Fjg7zjg6vjgqLjgqTjg4njg6vlkIzlpb3kvJpgTGllbGxhIQ%3D%3D',
        'info_dict': {
            'id': '354502-0001-002',
            'title': 'LoveLive!Series Presents COUNTDOWN LoveLive! 2021→2022～LIVE with a smile!～【Streaming+(配信)】',
            'live_status': 'was_live',
            'release_date': '20211231',
            'release_timestamp': 1640952000,
            'description': str,
        },
        'params': {
            'skip_download': True,
            'ignore_no_formats_error': True,
        },
        'expected_warnings': [
            'Could not find the playlist URL. This event may not be accessible',
            'No video formats found!',
            'Requested format is not available',
        ],
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        data_json = self._search_json(r'<script>\s*var app\s*=', webpage, 'data json', video_id)

        delivery_status = data_json.get('delivery_status')
        archive_mode = data_json.get('archive_mode')
        release_timestamp = try_call(lambda: unified_timestamp(data_json['event_datetime']) - 32400)
        release_timestamp_str = data_json.get('event_datetime_text')  # JST

        self.write_debug(f'delivery_status = {delivery_status}, archive_mode = {archive_mode}')

        if delivery_status == 'PREPARING':
            live_status = 'is_upcoming'
        elif delivery_status == 'STARTED':
            live_status = 'is_live'
        elif delivery_status == 'STOPPED':
            if archive_mode != 'ON':
                raise ExtractorError(
                    'This event has ended and there is no archive for this event', expected=True)
            live_status = 'post_live'
        elif delivery_status == 'WAIT_CONFIRM_ARCHIVED':
            live_status = 'post_live'
        elif delivery_status == 'CONFIRMED_ARCHIVE':
            live_status = 'was_live'
        else:
            self.report_warning(f'Unknown delivery_status {delivery_status}, treat it as a live')
            live_status = 'is_live'

        formats = []

        m3u8_playlist_urls = self._search_json(
            r'var listChannels\s*=', webpage, 'hls URLs', video_id, contains_pattern=r'\[.+\]', default=[])
        if not m3u8_playlist_urls:
            if live_status == 'is_upcoming':
                self.raise_no_formats(
                    f'Could not find the playlist URL. This live event will begin at {release_timestamp_str} JST', expected=True)
            else:
                self.raise_no_formats(
                    'Could not find the playlist URL. This event may not be accessible', expected=True)
        elif live_status == 'is_upcoming':
            self.raise_no_formats(f'This live event will begin at {release_timestamp_str} JST', expected=True)
        elif live_status == 'post_live':
            self.raise_no_formats('This event has ended, and the archive will be available shortly', expected=True)
        else:
            for m3u8_playlist_url in m3u8_playlist_urls:
                formats.extend(self._extract_m3u8_formats(m3u8_playlist_url, video_id))
            # FIXME: HTTP request headers need to be updated to continue download
            warning = 'Due to technical limitations, the download will be interrupted after one hour'
            if live_status == 'is_live':
                self.report_warning(warning)
            elif live_status == 'was_live':
                self.report_warning(f'{warning}. You can restart to continue the download')

        return {
            'id': data_json['app_id'],
            'title': data_json.get('app_name'),
            'formats': formats,
            'live_status': live_status,
            'description': data_json.get('content'),
            'release_timestamp': release_timestamp,
        }
