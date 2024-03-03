import base64
import hashlib
import functools
import time
import urllib.parse
import zlib

from ..aes import aes_cbc_encrypt
from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    int_or_none,
    parse_iso8601,
    traverse_obj,
    unified_strdate,
    unified_timestamp
)


class FiteTVBase(InfoExtractor):
    _NETRC_MACHINE = 'fitetv'
    _IV = bytes([10, 21, 121, 106, 15, 24, 21, 74,
        58, 30, 127, 65, 102, 29, 124, 123])
    _KEY = hashlib.md5(b'iM3diaShar3P4SSw0rD').digest()
    _API_BASE_URL = 'https://ims-lbs-us-east.fite.tv/fite'
    _USER_AGENT = 'Flipps/20/16/8.1.3'

    @staticmethod
    def _format_params(params):
        return '#'.join(
            [f'{x}{urllib.parse.quote_plus(y)}' for x, y in params.items()])

    def _get_api_url(self, params=None, formatted_params=None, suffix='.browse'):
        if not formatted_params:
            formatted_params = self._format_params(params)
        encrypted_params = bytes(aes_cbc_encrypt(list(zlib.compress(
            formatted_params.encode('utf-8'))), list(self._KEY), self._IV))
        return f"{self._API_BASE_URL}/{base64.b64encode(encrypted_params).decode('utf-8')}{suffix}"

    def _get_session(self, video_id):
        params = {
            'y': 'Android',
            'v': '8.1.3',
            'F': '16',
            't': '20',
            'm': 'model',
            'k': '47c7e17d95c2e5c49a21efeb24b27cb',
            'f': '10',
            'a': 'S'
        }
        data = self._download_json(
            self._get_api_url(params, suffix='.info'), video_id,
            'Retrieving Session',
            headers={
                'User-Agent': self._USER_AGENT
            })

        return traverse_obj(data, ('config', 'IMS-SESS-ID'))


class FiteTVIE(FiteTVBase):
    _VALID_URL = r'https?://(?:www\.)?trillertv\.com/(?:watch|video|v)/(?:[^/]+/)*(?P<id>[^/]+)/?$'

    def _login(self, video_id):
        username, password = self._get_login_info()
        if not username:
            return True

        self._SESSION = self._get_session(video_id)

        params = {
            'a': 'U',
            'l': self._SESSION,
            'v': '8.1.3',
            't': '20',
            'F': '16',
            'P': password,
            'E': username,
            'c': 'flipps'
        }

        login = self._download_json(
            self._get_api_url(params, suffix='.info'), video_id,
            'Logging in',
            headers={
                'User-Agent': self._USER_AGENT
            })

        user_login = login.get('message')
        if user_login.lower() == 'ok':
            return
        else:
            raise ExtractorError(
                'Unable to login: %s' % user_login, expected=True)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        self._login(video_id)

        params = {
            'a': 'I',
            'l': self._SESSION,
            'v': '8.8',
            'u': video_id,
            't': '20',
            'F': '17'
        }
        video_meta = self._download_json(
            self._get_api_url(params), video_id,
            note='Downloading video info', errnote='Unable to download video info',
            headers={
                'User-Agent': self._USER_AGENT
            })

        if video_meta.get('vodStartTime'):
            vod_start = parse_iso8601(video_meta['vodStartTime'])
            if vod_start > int(time.time()):
                raise ExtractorError(
                    'Event has not aired yet', expected=True)

        url = video_meta.get('directLink')
        if 'forbidden.mp4' in url:
            raise ExtractorError(
                f'Video ({video_id}) require purchase or subscription',
                expected=True)

        formats = self._extract_m3u8_formats(
            url, video_id, 'mp4', m3u8_id='hls', fatal=True)

        return {
            'id': video_id,
            'title': traverse_obj(video_meta, 'title', 'reportTitle'),
            'description': traverse_obj(video_meta, 'description'),
            'thumbnail': traverse_obj(video_meta, ('thumbnails', -1, 'url'), 'thumbnailUrl'),
            'timestamp': unified_timestamp(video_meta.get('airStartTime')),
            'release_date': unified_strdate(video_meta.get('airStartTime')),
            'duration': int_or_none(video_meta.get('duration')),
            'channel': video_meta.get('subscription'),
            'channel_id': int_or_none(video_meta.get('channelId')),
            'formats': formats
        }


class FiteTVChannelIE(FiteTVBase):
    _PAGE_SIZE = 50
    _VALID_URL = r'https?://(?:www\.)?trillertv\.com/channel/(?P<id>[^/]+)/?$'

    def _fetch_page(self, url, channel_title, page):
        page *= 50
        params = {
            'a': 's',
            'l': self._SESSION,
            'q': f'channel: {channel_title}',
            'z': str(page)
        }
        channel_meta = self._download_json(
            self._get_api_url(params), channel_title,
            note='Downloading channel info', errnote='Unable to download channel info',
            headers={
                'User-Agent': self._USER_AGENT
            })
        items = traverse_obj(channel_meta, ('layouts', 0, 'items'), 'items')
        yield from [self.url_result(item.get('pageUrl'), FiteTVIE) for item in items]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        channel_title = self._search_regex(
            (r'<h1>([^<]+)</h1>', r'>More from ([^<]+)</h2>'), webpage,
            'title')

        self._SESSION = self._get_session(channel_title)

        return self.playlist_result(
            OnDemandPagedList(functools.partial(self._fetch_page, url, channel_title), self._PAGE_SIZE),
            channel_title)
