import json
import time

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    float_or_none,
    jwt_decode_hs256,
    parse_iso8601,
    url_or_none,
    variadic,
)
from ..utils.traversal import traverse_obj


class CanalsurmasIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?canalsurmas\.es/videos/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.canalsurmas.es/videos/44006-el-gran-queo-1-lora-del-rio-sevilla-20072014',
        'md5': '861f86fdc1221175e15523047d0087ef',
        'info_dict': {
            'id': '44006',
            'ext': 'mp4',
            'title': 'Lora del Río (Sevilla)',
            'description': 'md5:3d9ee40a9b1b26ed8259e6b71ed27b8b',
            'thumbnail': 'https://cdn2.rtva.interactvty.com/content_cards/00f3e8f67b0a4f3b90a4a14618a48b0d.jpg',
            'timestamp': 1648123182,
            'upload_date': '20220324',
        },
    }]
    _API_BASE = 'https://api-rtva.interactvty.com'
    _access_token = None

    @staticmethod
    def _is_jwt_expired(token):
        return jwt_decode_hs256(token)['exp'] - time.time() < 300

    def _call_api(self, endpoint, video_id, fields=None):
        if not self._access_token or self._is_jwt_expired(self._access_token):
            self._access_token = self._download_json(
                f'{self._API_BASE}/jwt/token/', None,
                'Downloading access token', 'Failed to download access token',
                headers={'Content-Type': 'application/json'},
                data=json.dumps({
                    'username': 'canalsur_demo',
                    'password': 'dsUBXUcI',
                }).encode())['access']

        return self._download_json(
            f'{self._API_BASE}/api/2.0/contents/{endpoint}/{video_id}/', video_id,
            f'Downloading {endpoint} API JSON', f'Failed to download {endpoint} API JSON',
            headers={'Authorization': f'jwtok {self._access_token}'},
            query={'optional_fields': ','.join(variadic(fields))} if fields else None)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_info = self._call_api('content', video_id, fields=[
            'description', 'image', 'duration', 'created_at', 'tags',
        ])
        stream_info = self._call_api('content_resources', video_id, 'media_url')

        formats, subtitles = [], {}
        for stream_url in traverse_obj(stream_info, ('results', ..., 'media_url', {url_or_none})):
            if determine_ext(stream_url) == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    stream_url, video_id, m3u8_id='hls', fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            else:
                formats.append({'url': stream_url})

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(video_info, {
                'title': ('name', {str.strip}),
                'description': ('description', {str}),
                'thumbnail': ('image', {url_or_none}),
                'duration': ('duration', {float_or_none}),
                'timestamp': ('created_at', {parse_iso8601}),
                'tags': ('tags', ..., {str}),
            }),
        }
