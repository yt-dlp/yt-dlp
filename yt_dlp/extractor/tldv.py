import json
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import traverse_obj


def _caesar_decode(text, shift):
    """Decode Caesar cipher by shifting each letter forward by ``shift`` positions."""
    result = []
    for ch in text:
        if 'a' <= ch <= 'z':
            result.append(chr((ord(ch) - ord('a') + shift) % 26 + ord('a')))
        elif 'A' <= ch <= 'Z':
            result.append(chr((ord(ch) - ord('A') + shift) % 26 + ord('A')))
        else:
            result.append(ch)
    return ''.join(result)


class TldvIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tldv\.io/app/meetings/(?P<id>[a-f0-9]+)'
    _NETRC_MACHINE = 'tldv'
    IE_NAME = 'tldv'

    _API_BASE = 'https://gaia.tldv.io/v1'

    _TESTS = [{
        'url': 'https://tldv.io/app/meetings/6979fa3e5095a7001341ea2c',
        'only_matching': True,
    }]

    def _get_auth_token(self, video_id):
        token = self._configuration_arg('token', [None], casesense=True)[0]
        if token:
            return token

        username, password = self._get_login_info()
        if username and password:
            return self._login(username, password, video_id)

        token = self._get_token_from_cookies()
        if token:
            return token

        raise ExtractorError(
            'No authentication token found. Use one of:\n'
            '  --extractor-args "tldv:token=YOUR_JWT_TOKEN"\n'
            '  --username EMAIL --password PASSWORD\n'
            '\n'
            'To get your token from the browser:\n'
            '  1. Open tldv.io and log in\n'
            '  2. Press F12 and open the Console tab\n'
            '  3. Run: JSON.parse(localStorage.getItem("_cap_jwt")).token\n'
            '  4. Copy the output',
            expected=True)

    def _login(self, username, password, video_id):
        response = self._download_json(
            f'{self._API_BASE}/auth/login', video_id,
            note='Logging in to tldv',
            errnote='Login failed',
            data=json.dumps({
                'email': username,
                'password': password,
            }).encode(),
            headers={'Content-Type': 'application/json'},
            expected_status=(401, 403))

        token = traverse_obj(response, (
            ('token', 'accessToken', 'access_token'), {str}, any))
        if not token:
            token = traverse_obj(response, ('data', 'token', {str}))

        if not token:
            raise ExtractorError(
                'Login failed. Check your credentials or provide the token directly:\n'
                '  --extractor-args "tldv:token=YOUR_JWT_TOKEN"',
                expected=True)

        return token

    def _get_token_from_cookies(self):
        cookies = self._get_cookies('https://tldv.io')
        for name in ('token', 'jwt', 'access_token', 'auth_token', 'session', 'tldv_token'):
            cookie = cookies.get(name)
            if cookie:
                return cookie.value
        return None

    def _decode_playlist(self, raw_m3u8, shift, base_url):
        """Decode an obfuscated tldv m3u8 playlist.

        Segment URL lines are Caesar-cipher decoded and prepended with
        ``base_url`` to form absolute S3 pre-signed URLs. HLS tags,
        comments, and blank lines are kept as-is.
        """
        decoded_lines = []
        for line in raw_m3u8.splitlines():
            if line.startswith('#TLDVCONF'):
                continue
            if line.startswith('#') or not line.strip():
                decoded_lines.append(line)
                continue
            decoded_lines.append(base_url + _caesar_decode(line.strip(), shift))

        return '\n'.join(decoded_lines)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        token = self._get_auth_token(video_id)
        headers = {'Authorization': f'Bearer {token}'}

        metadata = self._download_json(
            f'{self._API_BASE}/meetings/{video_id}',
            video_id, note='Downloading meeting metadata',
            headers=headers, fatal=False) or {}

        raw_m3u8 = self._download_webpage(
            f'{self._API_BASE}/meetings/{video_id}/playlist.m3u8',
            video_id, note='Downloading obfuscated playlist',
            headers=headers)

        tldvconf_match = re.search(r'#TLDVCONF:(\d+),(\d+),(.+)', raw_m3u8)
        if not tldvconf_match:
            raise ExtractorError(
                'Could not find TLDVCONF header in playlist. '
                'The format may have changed.', expected=True)

        shift = int(tldvconf_match.group(2))
        base_url = tldvconf_match.group(3).strip()

        self.to_screen(f'Decoding playlist (Caesar shift={shift})')
        decoded_m3u8 = self._decode_playlist(raw_m3u8, shift, base_url)

        formats, subtitles = self._parse_m3u8_formats_and_subtitles(
            decoded_m3u8, m3u8_url=None, ext='mp4',
            m3u8_id='hls', video_id=video_id)

        return {
            'id': video_id,
            'title': traverse_obj(metadata, (
                ('name', 'title', 'meetingName'), {str_or_none}, any)) or video_id,
            'formats': formats,
            'subtitles': subtitles,
            'duration': traverse_obj(metadata, ('duration', {int_or_none})),
            'thumbnail': traverse_obj(metadata, ('thumbnail', {url_or_none})),
        }
