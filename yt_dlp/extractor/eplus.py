from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    try_call,
    unified_timestamp,
)


class EplusIbIE(InfoExtractor):
    IE_NAME = 'eplus:inbound'
    IE_DESC = 'e+ (イープラス) overseas'
    _VALID_URL = r'https?://live\.eplus\.jp/ex/player\?ib=(?P<id>([A-Za-z\d]|%2B|%2F){86}(%3D){2})'
    _TESTS = [{
        # simple fake url
        'url': 'https://live.eplus.jp/ex/player?ib=00000000000000000000000000000000000000000000000000000000000000000000000000000000000000%3D%3D',
        'only_matching': True,
    }, {
        # complex fake url
        'url': 'https://live.eplus.jp/ex/player?ib=YA4Z%2Fz2rpI5cDl3V%2Bx9PI%2FXTGOX0j8IBzPthgx7%2BieWeff6iLcdsdsds1926zosZU9AbB3gdL3wG%2BNa1afQdIf%3D%3D',
        'only_matching': True,
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
            # FIXME: HTTP request headers need to be updated to continue download
            self.report_warning(
                'Due to technical limitations, the download will be interrupted after one hour')
            live_status = 'is_live'
        elif delivery_status == 'STOPPED':
            if archive_mode != 'ON':
                raise ExtractorError(
                    'This event has ended and there is no archive for this event', expected=True)
            live_status = 'is_upcoming'
        elif delivery_status == 'WAIT_CONFIRM_ARCHIVED':
            live_status = 'is_upcoming'
        elif delivery_status == 'CONFIRMED_ARCHIVE':
            # FIXME: HTTP request headers need to be updated to continue download
            self.report_warning(
                'Due to technical limitations, the download will be interrupted after one hour. '
                'You can restart to continue the download')
            live_status = 'was_live'
        else:
            raise ExtractorError(f'Unknown delivery_status: {delivery_status}')

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
            if delivery_status == 'PREPARING':
                self.raise_no_formats(f'This live event will begin at {release_timestamp_str} JST', expected=True)
            else:
                self.raise_no_formats('This event has ended, and the archive will be available shortly', expected=True)
        else:
            for m3u8_playlist_url in m3u8_playlist_urls:
                formats.extend(self._extract_m3u8_formats(m3u8_playlist_url, video_id))

        return {
            'id': data_json['app_id'],
            'title': data_json.get('app_name'),
            'formats': formats,
            'live_status': live_status,
            'description': data_json.get('content'),
            'timestamp': release_timestamp,
            'release_timestamp': release_timestamp,
        }
