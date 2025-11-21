import json
import time

from .common import InfoExtractor
from ..utils import jwt_decode_hs256, url_or_none
from ..utils.traversal import traverse_obj


class AGalegaBaseIE(InfoExtractor):
    _access_token = None

    @staticmethod
    def _jwt_is_expired(token):
        return jwt_decode_hs256(token)['exp'] - time.time() < 120

    def _refresh_access_token(self, video_id):
        AGalegaBaseIE._access_token = self._download_json(
            'https://www.agalega.gal/api/fetch-api/jwt/token', video_id,
            note='Downloading access token',
            data=json.dumps({
                'username': None,
                'password': None,
                'client': 'crtvg',
                'checkExistsCookies': False,
            }).encode())['access']

    def _call_api(self, endpoint, display_id, note, fatal=True, query=None):
        if not AGalegaBaseIE._access_token or self._jwt_is_expired(AGalegaBaseIE._access_token):
            self._refresh_access_token(endpoint)
        return self._download_json(
            f'https://api-agalega.interactvty.com/api/2.0/contents/{endpoint}', display_id,
            note=note, fatal=fatal, query=query,
            headers={'Authorization': f'jwtok {AGalegaBaseIE._access_token}'})


class AGalegaIE(AGalegaBaseIE):
    IE_NAME = 'agalega:videos'
    _VALID_URL = r'https?://(?:www\.)?agalega\.gal/videos/(?:detail/)?(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.agalega.gal/videos/288664-lr-ninguencheconta',
        'md5': '04533a66c5f863d08dd9724b11d1c223',
        'info_dict': {
            'id': '288664',
            'title': 'Roberto e Ángel Martín atenden consultas dos espectadores',
            'description': 'O cómico ademais fai un repaso dalgúns momentos da súa traxectoria profesional',
            'thumbnail': 'https://crtvg-bucket.flumotion.cloud/content_cards/2ef32c3b9f6249d9868fd8f11d389d3d.png',
            'ext': 'mp4',
        },
    }, {
        'url': 'https://www.agalega.gal/videos/detail/296152-pulso-activo-7',
        'md5': '26df7fdcf859f38ad92d837279d6b56d',
        'info_dict': {
            'id': '296152',
            'title': 'Pulso activo | 18-11-2025',
            'description': 'Anxo, Noemí, Silvia e Estrella  comparten as sensacións da clase de Eddy.',
            'thumbnail': 'https://crtvg-bucket.flumotion.cloud/content_cards/a6bb7da6c8994b82bf961ac6cad1707b.png',
            'ext': 'mp4',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        content_data = self._call_api(
            f'content/{video_id}/', video_id, note='Downloading content data', fatal=False,
            query={
                'optional_fields': 'image,is_premium,short_description,has_subtitle',
            })
        resource_data = self._call_api(
            f'content_resources/{video_id}/', video_id, note='Downloading resource data',
            query={
                'optional_fields': 'media_url',
            })

        formats = []
        subtitles = {}
        for m3u8_url in traverse_obj(resource_data, ('results', ..., 'media_url', {url_or_none})):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                m3u8_url, video_id, ext='mp4', m3u8_id='hls')
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(content_data, {
                'title': ('name', {str}),
                'description': (('description', 'short_description'), {str}, any),
                'thumbnail': ('image', {url_or_none}),
            }),
        }
