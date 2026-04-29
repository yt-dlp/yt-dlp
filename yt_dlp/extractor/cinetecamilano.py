import json

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    float_or_none,
    parse_iso8601,
    strip_or_none,
    traverse_obj,
    try_get,
    urljoin,
)


class CinetecaMilanoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?cinetecamilano\.it/film/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.cinetecamilano.it/film/1942',
        'info_dict': {
            'id': '1942',
            'ext': 'mp4',
            'title': 'Il draghetto Gris\u00f9 (4 episodi)',
            'release_date': '20220129',
            'thumbnail': r're:.+\.png',
            'description': 'md5:5328cbe080b93224712b6f17fcaf2c01',
            'modified_date': '20200520',
            'duration': 3139,
            'release_timestamp': 1643446208,
            'modified_timestamp': int,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        try:
            film_json = self._download_json(
                f'https://www.cinetecamilano.it/api/catalogo/{video_id}/?',
                video_id, headers={
                    'Referer': url,
                    'Authorization': try_get(self._get_cookies('https://www.cinetecamilano.it'), lambda x: f'Bearer {x["cnt-token"].value}') or '',
                })
        except ExtractorError as e:
            if ((isinstance(e.cause, HTTPError) and e.cause.status == 500)
                    or isinstance(e.cause, json.JSONDecodeError)):
                self.raise_login_required(method='cookies')
            raise
        if not film_json.get('success') or not film_json.get('archive'):
            raise ExtractorError('Video information not found')
        archive = film_json['archive']

        return {
            'id': video_id,
            'title': archive.get('title'),
            'description': strip_or_none(archive.get('description')),
            'duration': float_or_none(archive.get('duration'), invscale=60),
            'release_timestamp': parse_iso8601(archive.get('updated_at'), delimiter=' '),
            'modified_timestamp': parse_iso8601(archive.get('created_at'), delimiter=' '),
            'thumbnail': urljoin(url, try_get(archive, lambda x: x['thumb']['src'].replace('/public/', '/storage/'))),
            'formats': self._extract_m3u8_formats(
                urljoin(url, traverse_obj(archive, ('drm', 'hls'))), video_id, 'mp4'),
        }
