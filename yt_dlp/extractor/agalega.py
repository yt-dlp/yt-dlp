import json

from .common import InfoExtractor
from ..utils import str_or_none, traverse_obj, url_or_none


class AGalegaBaseIE(InfoExtractor):
    def _fetch_auth_headers(self, video_id):
        access_token = self._download_json(
            'https://www.agalega.gal/api/fetch-api/jwt/token', video_id,
            note='Downloading access token',
            data=json.dumps({
                'username': None,
                'password': None,
                'client': 'crtvg',
                'checkExistsCookies': False,
            }).encode())['access']
        return {'authorization': f'jwtok {access_token}'}


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
        playlist_id = self._match_id(url)
        auth_headers = self._fetch_auth_headers(playlist_id)
        content_data = self._download_json(
            f'https://api-agalega.interactvty.com/api/2.0/contents/content/{playlist_id}/', playlist_id,
            note='Downloading content data', fatal=False, headers=auth_headers,
            query={
                'optional_fields': 'image,is_premium,short_description,has_subtitle',
            })
        resource_data = self._download_json(
            f'https://api-agalega.interactvty.com/api/2.0/contents/content_resources/{playlist_id}/',
            playlist_id, note='Downloading resource data', headers=auth_headers,
            query={
                'optional_fields': 'media_url',
            })

        formats = []
        subtitles = {}
        for m3u8_url in traverse_obj(resource_data, ('results', ..., 'media_url', {url_or_none})):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                m3u8_url, playlist_id, ext='mp4', m3u8_id='hls')
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)
            return {
                'id': playlist_id,
                'formats': formats,
                **traverse_obj(content_data, {
                    'title': ('name', {str_or_none}),
                    'description': (('description', 'short_description'), {str_or_none}, any),
                    'thumbnail': ('image', {url_or_none}),
                }),
            }
        return None
