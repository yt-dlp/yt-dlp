import datetime as dt
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    clean_html,
    datetime_from_str,
    unified_timestamp,
    urljoin,
)


class JoqrAgIE(InfoExtractor):
    IE_DESC = '超!A&G+ 文化放送 (f.k.a. AGQR) Nippon Cultural Broadcasting, Inc. (JOQR)'
    _VALID_URL = [r'https?://www\.uniqueradio\.jp/agplayer5/(?:player|inc-player-hls)\.php',
                  r'https?://(?:www\.)?joqr\.co\.jp/ag/',
                  r'https?://(?:www\.)?joqr\.co\.jp/qr/ag(?:daily|regular)program/?(?:$|[#?])']
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

    def _extract_metadata(self, variable, html):
        return clean_html(urllib.parse.unquote_plus(self._search_regex(
            rf'var\s+{variable}\s*=\s*(["\'])(?P<value>(?:(?!\1).)+)\1',
            html, 'metadata', group='value', default=''))) or None

    def _extract_start_timestamp(self, video_id, is_live):
        def extract_start_time_from(date_str):
            dt_ = datetime_from_str(date_str) + dt.timedelta(hours=9)
            date = dt_.strftime('%Y%m%d')
            start_time = self._search_regex(
                r'<h3[^>]+\bclass="dailyProgram-itemHeaderTime"[^>]*>[\s\d:]+–\s*(\d{1,2}:\d{1,2})',
                self._download_webpage(
                    f'https://www.joqr.co.jp/qr/agdailyprogram/?date={date}', video_id,
                    note=f'Downloading program list of {date}', fatal=False,
                    errnote=f'Failed to download program list of {date}') or '',
                'start time', default=None)
            if start_time:
                return unified_timestamp(f'{dt_.strftime("%Y/%m/%d")} {start_time} +09:00')
            return None

        start_timestamp = extract_start_time_from('today')
        if not start_timestamp:
            return None

        if not is_live or start_timestamp < datetime_from_str('now').timestamp():
            return start_timestamp
        else:
            return extract_start_time_from('yesterday')

    def _real_extract(self, url):
        video_id = 'live'

        metadata = self._download_webpage(
            'https://www.uniqueradio.jp/aandg', video_id,
            note='Downloading metadata', errnote='Failed to download metadata')
        title = self._extract_metadata('Program_name', metadata)

        if title == '放送休止':
            formats = []
            live_status = 'is_upcoming'
            release_timestamp = self._extract_start_timestamp(video_id, False)
            msg = 'This stream is not currently live'
            if release_timestamp:
                msg += (' and will start at '
                        + dt.datetime.fromtimestamp(release_timestamp).strftime('%Y-%m-%d %H:%M:%S'))
            self.raise_no_formats(msg, expected=True)
        else:
            m3u8_path = self._search_regex(
                r'<source\s[^>]*\bsrc="([^"]+)"',
                self._download_webpage(
                    'https://www.uniqueradio.jp/agplayer5/inc-player-hls.php', video_id,
                    note='Downloading player data', errnote='Failed to download player data'),
                'm3u8 url')
            formats = self._extract_m3u8_formats(
                urljoin('https://www.uniqueradio.jp/', m3u8_path), video_id)
            live_status = 'is_live'
            release_timestamp = self._extract_start_timestamp(video_id, True)

        return {
            'id': video_id,
            'title': title,
            'channel': '超!A&G+',
            'description': self._extract_metadata('Program_text', metadata),
            'formats': formats,
            'live_status': live_status,
            'release_timestamp': release_timestamp,
        }
