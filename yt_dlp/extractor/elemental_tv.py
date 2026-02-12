import json
import re
import time

from ..extractor.common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import ExtractorError


class ElementalTVIE(InfoExtractor):
    _LOGIN_REQUIRED = True
    _NETRC_MACHINE = 'elemental_tv'
    _VALID_URL = r'https?://play\.elemental\.tv/channel/[0-9a-f]{24}'
    _TESTS = [{
        'url': 'https://play.elemental.tv/channel/573f5a14761973ec1d502507',
        'info_dict': {
            'id': '573f5a14761973ec1d502507',
            'ext': 'mp4',
            'title': 'БНТ 1 HD',
            'thumbnail': 'https://play.elemental.tv/v1/tumblrs/573f5a14761973ec1d502507',
            'age_limit': 0,
        },
    }]

    access_token = ''
    channel_id = ''

    def _get_channel_id(self, url):
        url_parts = re.search('(?<=channel/)[0-9a-f]{24}', url)

        if not url_parts or not url_parts.group(0):
            return None

        self.channel_id = url_parts.group(0)
        self.write_debug(f'Channel ID: {self.channel_id}')

        if not self.channel_id:
            raise ExtractorError('Channel ID not found')

    def _get_stream_metadata(self):
        try:
            headers = {
                'Authorization': 'Bearer ' + self.access_token,
            }
            res_api = self._download_json(
                'https://play.elemental.tv/v1/channels', self.channel_id, headers=headers)
            data = res_api.get('data').get(self.channel_id)

            if not data:
                self.write_debug('Getting metadata failed')
                return {}

            return {
                'title': data.get('name'),
                'age_limit': data.get('age'),
                'thumbnail': data.get('tumblrurl'),
            }
        except Exception:
            self.write_debug('Getting metadata failed')
            return {}

    def _get_stream_url(self):
        # Stream URL needs current epoch time rounded to 10000s
        begin = int((time.time() - 60) / 10000) * 10000
        stream_url = 'https://play.elemental.tv/v1/playlists/%s/playlist.m3u8?begin=%d&access_token=%s' % (self.channel_id, begin, self.access_token)

        if not stream_url or '.m3u8' not in stream_url:
            raise ExtractorError('Unable to get stream URL')

        return stream_url

    def _perform_login(self, username, password):
        post_data = {
            'email': str(username),
            'grant_type': 'client_credentials',
            'password': str(password),
            'rememberme': 'true',
        }

        try:
            res_api = self._download_json(
                'https://play.elemental.tv/v1/users/login', self.channel_id, data=json.dumps(post_data).encode()).get('data')
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 400:
                error_message = self._parse_json(e.cause.response.read().decode(), self.channel_id).get('error_info').get('description')
                raise ExtractorError(error_message, expected=True)

        if not res_api or not res_api.get('access_token'):
            raise ExtractorError('Accessing login token failed')

        self.access_token = res_api.get('access_token')

        if res_api.get('token_type') != 'Bearer':
            raise ExtractorError('Unknown login token type')

    def _real_extract(self, url):
        self._get_channel_id(url)
        stream_url = self._get_stream_url()
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(stream_url, self.channel_id, ext='mp4')

        return {
            'id': self.channel_id,
            'is_live': True,
            'formats': formats,
            'subtitles': subtitles,
            **self._get_stream_metadata(),
        }
