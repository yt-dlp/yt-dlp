import calendar
import datetime

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    UserNotLive,
    traverse_obj,
)


class EplusIbIE(InfoExtractor):
    IE_NAME = 'eplus:inbound'
    IE_DESC = 'e+ (イープラス). Only works for the link starts with "live.eplus.jp/ex/player?ib="'
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

        data_json = self._parse_json(self._html_search_regex(
            r'<script>\s*var app = (.+);\n', webpage, 'data_json'), video_id)

        delivery_status = traverse_obj(data_json, 'delivery_status')
        archive_mode = traverse_obj(data_json, 'archive_mode')

        self.to_screen(f'delivery_status = {delivery_status}, archive_mode = {archive_mode}')

        if delivery_status == 'PREPARING':
            raise UserNotLive('This event has not started yet.')
        elif delivery_status == 'STARTED':
            # FFmpeg is unable to update HTTP request headers during download.
            self.report_warning(
                'Due to technical limitations, the download will be interrupted after one hour.')
            live_status = 'is_live'
        elif delivery_status == 'STOPPED':
            # check archive status
            errmsg = 'This event has been ended. '
            if archive_mode == 'ON':  # I didn't see values other than "ON"
                raise UserNotLive(errmsg + 'The archive has not been generated yet.')
            else:
                raise ExtractorError(errmsg + 'No archive for this event.', expected=True)
        elif delivery_status == 'WAIT_CONFIRM_ARCHIVED':
            raise UserNotLive('The archive will be available shortly.')
        elif delivery_status == 'CONFIRMED_ARCHIVE':
            # The archive may be available.
            # TODO: how to update HTTP request headers for "HlsFD" during download?
            self.report_warning(
                'Due to technical limitations, the download will be interrupted after one hour. You can restart to continue the download.')
            live_status = 'was_live'
        else:
            raise ExtractorError(f'Unknown delivery_status: {delivery_status}', expected=False)

        # TODO: if there are multiple playlists, tell me.
        m3u8_playlist_urls = self._html_search_regex(
            r'var listChannels = (.+);\n', webpage, 'listChannels', default=None)
        if not m3u8_playlist_urls:
            raise ExtractorError(
                'Could not find the playlist URL. This event may not be accessible.', expected=True)

        return {
            # mandatory metafields

            'id': data_json['app_id'],
            'title': data_json['app_name'],
            'formats': self._extract_m3u8_formats(m3u8_url=traverse_obj(self._parse_json(
                m3u8_playlist_urls, video_id), 0), video_id=video_id),

            # optional metafields

            'live_status': live_status,
            'description': traverse_obj(data_json, 'content'),
            'timestamp': calendar.timegm((datetime.datetime.strptime(
                traverse_obj(data_json, 'event_datetime'), '%Y%m%d%H%M')
                - datetime.timedelta(hours=9)).timetuple()),
        }
