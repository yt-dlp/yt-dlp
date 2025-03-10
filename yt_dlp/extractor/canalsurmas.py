import json

from .common import InfoExtractor
from ..utils import ExtractorError, traverse_obj


class CanalsurmasIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?canalsurmas\.es/videos/(?P<id>\d+)'

    _TESTS = [
        {
            'url': 'https://www.canalsurmas.es/videos/44006-el-gran-queo-1-lora-del-rio-sevilla-20072014',
            'md5': '861f86fdc1221175e15523047d0087ef',
            'info_dict': {
                'id': '44006',
                'ext': 'mp4',
                'title': 'Lora del Río (Sevilla)  ',
                'description': 'md5:3d9ee40a9b1b26ed8259e6b71ed27b8b',
                'thumbnail': 'https://cdn2.rtva.interactvty.com/content_cards/00f3e8f67b0a4f3b90a4a14618a48b0d.jpg',
                'tags': [],
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        access_token = self._download_json(
            'https://api-rtva.interactvty.com/jwt/token/', video_id,
            headers={'Content-Type': 'application/json'},
            data=json.dumps({
                'username': 'canalsur_demo',
                'password': 'dsUBXUcI',
            }).encode())['access']

        video_info = self._download_json(
            f'https://api-rtva.interactvty.com/api/2.0/contents/content/{video_id}/', video_id,
            headers={'Authorization': f'jwtok {access_token}'},
            query={
                'optional_fields': 'description,main_category,image,duration,genre,created_at,publish_date,tags',
            })

        stream_info = self._download_json(
            f'https://api-rtva.interactvty.com/api/2.0/contents/content_resources/{video_id}/', video_id,
            headers={'Authorization': f'jwtok {access_token}'},
            query={
                'optional_fields': 'media_url',
            })

        formats = []
        subtitles = {}
        for stream_url in traverse_obj(stream_info, ('results', ..., 'media_url', {url_or_none})):
            if determine_ext(stream_url) == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    stream_url, video_id, m3u8_id='hls', fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            else:
                formats.append({
                    'url': stream_url,
                })

        return {
            'id': video_id,
            'title': traverse_obj(
                video_info,
                ('name'),
            ),
            'description': traverse_obj(
                video_info,
                ('description'),
            ),
            'formats': formats,
            'thumbnail': traverse_obj(
                video_info,
                ('image'),
            ),
            'tags': traverse_obj(
                video_info,
                ('tags'),
            ),
        }
