import re
import time

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import ExtractorError


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

    API_URL_CHANNELS = 'https://play.elemental.tv/v1/channels'
    API_URL_LOGIN = 'https://play.elemental.tv/v1/users/login'
    API_URL_STREAM_URL = 'https://play.elemental.tv/v1/playlists/%s/playlist.m3u8?begin=%d&access_token=%s'

    access_token = ''
    channel_id = ''

    def get_channel_id(self, url):
        url_parts = re.search('(?<=channel/)[0-9a-f]{24}', url)

        if not url_parts or not url_parts.group(0):
            return None

        return url_parts.group(0)

    def get_stream_metadata(self):
        try:
            headers = {
                'Authorization': 'Bearer ' + self.access_token
            }

            res_api = self._download_json(
                self.API_URL_CHANNELS, self.channel_id, headers=headers)

            data = res_api.get('data').get(self.channel_id)

            if not data:
                return {}

            return {
                'title': data.get('name'),
                'age_limit': data.get('age'),
                'thumbnail': data.get('tumblrurl'),
            }
        except Exception:
            self.write_debug('Getting metadata failed')
            return {}

    def get_stream_url(self):
        # Stream URL needs current epoch time rounded to 10000s
        begin = int((time.time() - 60) / 10000) * 10000

        return self.API_URL_STREAM_URL % (self.channel_id, begin, self.access_token)

    def _perform_login(self, username, password):
        url = self.API_URL_LOGIN

        post_data = {
            'email': str(username),
            'grant_type': 'client_credentials',
            'password': str(password),
            'rememberme': 'true',
        }

        # Use double quotes (") as server returns error 400 while using apostrophe (')
        post_data = str(post_data).replace("'", '"').encode(encoding='UTF-8')

        res_api = self._download_json(url, self.channel_id, data=post_data)

        if not res_api.get('data') or not res_api.get('data').get('access_token'):
            raise ExtractorError('Accessing login token failed')

        self.access_token = res_api.get('data').get('access_token')
        token_type = res_api.get('data').get('token_type')

        if token_type != 'Bearer':
            raise ExtractorError('Unknown login token type')

    def _real_extract(self, url):
        if not self.access_token:
            raise ExtractorError('Logging in failed')

        self.channel_id = self.get_channel_id(url)

        if not self.channel_id:
            raise ExtractorError('Channel ID not found')

        self.write_debug('Channel ID: {0}'.format(self.channel_id))

        stream_url = self.get_stream_url()

        if not stream_url or '.m3u8' not in stream_url:
            raise ExtractorError('Unable to get stream URL')

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(stream_url, self.channel_id, ext='mp4')

        result = {
            'id': self.channel_id,
            'formats': formats,
            'subtitles': subtitles,
        }

        metadata = self.get_stream_metadata()

        return {**result, **metadata}
