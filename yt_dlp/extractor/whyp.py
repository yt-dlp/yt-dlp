from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
    parse_iso8601,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class WhypIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?whyp\.it/tracks/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.whyp.it/tracks/18337/home-page-example-track-b4kq7',
        'md5': '02fd96427acd9547445979bf0496b013',
        'info_dict': {
            'id': '18337',
            'title': 'Example Track',
            'display_id': 'example-track',
            'description': 'md5:e0b1bcf1d267dc1a0f15efff09c8f297',
            'ext': 'flac',
            'duration': 135.63,
            'timestamp': 1643216583,
            'upload_date': '20220126',
            'uploader': 'Brad',
            'uploader_id': '1',
            'thumbnail': 'https://cdn.whyp.it/6ad0bbd9-577d-42bb-9b61-2a4f57f647eb.jpg',
        },
    }, {
        'url': 'https://www.whyp.it/tracks/18337',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        unique_id = self._match_id(url)
        webpage = self._download_webpage(url, unique_id)
        data = self._search_nuxt_data(webpage, unique_id)['rawTrack']

        return {
            'id': unique_id,
            'formats': [{
                'url': data[f'{prefix}_url'],
                'format_id': prefix,
                'filesize': int_or_none(data.get(f'{prefix}_size')),
                'vcodec': 'none',
                'quality': 10 if prefix == 'lossless' else -1,
                'http_headers': {'Referer': 'https://whyp.it/'},
            } for prefix in ('audio', 'lossy', 'lossless') if url_or_none(data.get(f'{prefix}_url'))],
            **traverse_obj(data, {
                'title': ('title', {str}),
                'display_id': ('slug', {str}),
                'description': 'description',
                'duration': ('duration', {float_or_none}),
                'timestamp': ('created_at', {parse_iso8601}),
                'uploader': ('user', 'username', {str}),
                'uploader_id': ('user', 'id', {str_or_none}),
                'thumbnail': ('artwork_url', {url_or_none}),
            }),
        }
