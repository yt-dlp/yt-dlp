import urllib.parse
import datetime

from .common import InfoExtractor
from ..utils import (
    clean_html,
    datetime_from_str,
    unified_timestamp,
    urljoin,
)


class JoqrAgIE(InfoExtractor):
    IE_DESC = '超!A&G+ 文化放送 Nippon Cultural Broadcasting, Inc. (JOQR)'
    _VALID_URL = [r'https?://www\.uniqueradio\.jp/agplayer5/player\.php',
                  r'https?://www\.uniqueradio\.jp/agplayer5/inc-player-hls\.php',
                  r'https?://(?:www\.)?joqr\.co\.jp/ag/',
                  r'https?://(?:www\.)?joqr\.co\.jp/qr/(?:agdailyprogram|agregularprogram)/']
    _TESTS = [{
        'url': 'https://www.uniqueradio.jp/agplayer5/player.php',
        'info_dict': {
            'id': 'live',
            'title': str,
            'channel': '超!A&G+',
            'description': str,
            'live_status': 'is_live',
            'release_timestamp': int,
        },
        'params': {
            'skip_download': True,
            'ignore_no_formats_error': True,
        },
    }, {
        'url': 'https://www.uniqueradio.jp/agplayer5/inc-player-hls.php',
        'only_matching': True,
    }, {
        'url': 'https://www.joqr.co.jp/ag/article/103760/',
        'only_matching': True,
    }, {
        'url': 'http://www.joqr.co.jp/qr/agdailyprogram/',
        'only_matching': True,
    }, {
        'url': 'http://www.joqr.co.jp/qr/agregularprogram/',
        'only_matching': True,
    }]

    def _extract_metadata(self, variable, html, name):
        return clean_html(urllib.parse.unquote_plus(self._search_regex(
            rf'var\s+{variable}\s*=\s*["\']([^"\']+)["\']', html, name, default=''))) or None

    def _extract_start_timestamp(self, video_id, is_live):
        def __extract_start_timestamp_of_day(date_str):
            dt = datetime_from_str(date_str, 'day') + datetime.timedelta(hours=9)
            date = dt.strftime("%Y%m%d")
            start_time = self._search_regex(
                r'<h3\s+class="dailyProgram-itemHeaderTime"\s*>\s*\d{1,2}:\d{1,2}\s*–\s*(?P<time>\d{1,2}:\d{1,2})\s*<\/h3>',
                self._download_webpage(
                    f'https://www.joqr.co.jp/qr/agdailyprogram/?date={date}', video_id,
                    fatal=False, note=f'Downloading program list of {date}',
                    errnote=f'Failed to download program list of {date}'),
                'start time of the first program', default=None, group='time')
            if start_time:
                return unified_timestamp(f'{dt.strftime("%Y/%m/%d")} {start_time} +09:00')
            return None

        start_timestamp = __extract_start_timestamp_of_day('today')
        if not start_timestamp:
            return None

        if not is_live or start_timestamp < datetime_from_str('now').timestamp():
            return start_timestamp
        else:
            return __extract_start_timestamp_of_day('yesterday')

    def _real_extract(self, url):
        video_id = 'live'

        metadata = self._download_webpage(
            'https://www.uniqueradio.jp/aandg', video_id,
            note='Downloading metadata', errnote='Failed to download metadata')
        title = self._extract_metadata('Program_name', metadata, 'program title')
        desc = self._extract_metadata('Program_text', metadata, 'program description')

        if title == '放送休止':
            formats = []
            live_status = 'is_upcoming'
            release_timestamp = self._extract_start_timestamp(video_id, False)
            if release_timestamp:
                msg = f'This stream will start at {datetime.datetime.fromtimestamp(release_timestamp).strftime("%Y-%m-%d %H:%M:%S")}'
            else:
                msg = 'This stream has not started yet'
            self.raise_no_formats(msg, expected=True)
        else:
            m3u8_path = self._search_regex(
                r'<source\s[^>]*\bsrc="([^"]+)"',
                self._download_webpage(
                    'https://www.uniqueradio.jp/agplayer5/inc-player-hls.php', video_id,
                    note='Downloading player data', errnote='Failed to download player data'),
                'm3u8 url')
            formats = self._extract_m3u8_formats(
                urljoin('https://www.uniqueradio.jp/', m3u8_path), video_id, fatal=False)
            live_status = 'is_live'
            release_timestamp = self._extract_start_timestamp(video_id, True)

        return {
            'id': video_id,
            'title': title,
            'channel': '超!A&G+',
            'description': desc,
            'formats': formats,
            'live_status': live_status,
            'release_timestamp': release_timestamp,
        }
