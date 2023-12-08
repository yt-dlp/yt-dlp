import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    try_call,
    unified_timestamp,
    urlencode_postdata,
)


class EplusIbIE(InfoExtractor):
    _NETRC_MACHINE = 'eplus'
    IE_NAME = 'eplus'
    IE_DESC = 'e+ (イープラス)'
    _VALID_URL = [r'https?://live\.eplus\.jp/ex/player\?ib=(?P<id>(?:\w|%2B|%2F){86}%3D%3D)',
                  r'https?://live\.eplus\.jp/(?P<id>sample|\d+)']
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
    }, {
        'url': 'https://live.eplus.jp/sample',
        'info_dict': {
            'id': 'stream1ng20210719-test-005',
            'title': 'Online streaming test for DRM',
            'live_status': 'was_live',
            'release_date': '20210719',
            'release_timestamp': 1626703200,
            'description': None,
        },
        'params': {
            'skip_download': True,
            'ignore_no_formats_error': True,
        },
        'expected_warnings': [
            'Could not find the playlist URL. This event may not be accessible',
            'No video formats found!',
            'Requested format is not available',
            'This video is DRM protected',
        ],
    }, {
        'url': 'https://live.eplus.jp/2053935',
        'info_dict': {
            'id': '331320-0001-001',
            'title': '丘みどり2020配信LIVE Vol.2 ～秋麗～ 【Streaming+(配信チケット)】',
            'live_status': 'was_live',
            'release_date': '20200920',
            'release_timestamp': 1600596000,
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

    _USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0'

    def _login(self, username, password, urlh):
        if not self._get_cookies('https://live.eplus.jp/').get('ci_session'):
            raise ExtractorError('Unable to get ci_session cookie')

        cltft_token = urlh.headers.get('X-CLTFT-Token')
        if not cltft_token:
            raise ExtractorError('Unable to get X-CLTFT-Token')
        self._set_cookie('live.eplus.jp', 'X-CLTFT-Token', cltft_token)

        login_json = self._download_json(
            'https://live.eplus.jp/member/api/v1/FTAuth/idpw', None,
            note='Sending pre-login info', errnote='Unable to send pre-login info', headers={
                'Content-Type': 'application/json; charset=UTF-8',
                'Referer': urlh.url,
                'X-Cltft-Token': cltft_token,
                'Accept': '*/*',
            }, data=json.dumps({
                'loginId': username,
                'loginPassword': password,
            }).encode())
        if not login_json.get('isSuccess'):
            raise ExtractorError('Login failed: Invalid id or password', expected=True)

        self._request_webpage(
            urlh.url, None, note='Logging in', errnote='Unable to log in',
            data=urlencode_postdata({
                'loginId': username,
                'loginPassword': password,
                'Token.Default': cltft_token,
                'op': 'nextPage',
            }), headers={'Referer': urlh.url})

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage, urlh = self._download_webpage_handle(
            url, video_id, headers={'User-Agent': self._USER_AGENT})
        if urlh.url.startswith('https://live.eplus.jp/member/auth'):
            username, password = self._get_login_info()
            if not username:
                self.raise_login_required()
            self._login(username, password, urlh)
            webpage = self._download_webpage(
                url, video_id, headers={'User-Agent': self._USER_AGENT})

        data_json = self._search_json(r'<script>\s*var app\s*=', webpage, 'data json', video_id)

        if data_json.get('drm_mode') == 'ON':
            self.report_drm(video_id)

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
            r'var\s+listChannels\s*=', webpage, 'hls URLs', video_id, contains_pattern=r'\[.+\]', default=[])
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
