from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
    parse_iso8601,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import require, traverse_obj


class WhypIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?whyp\.it/tracks/(?:(?P<id>\d{5,})/)?(?P<display_id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://whyp.it/tracks/example-track-HPuZgly3yViP',
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
            'thumbnail': r're:https://cdn\.whyp\.it/.+\.jpg',
        },
    }, {
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
            'thumbnail': r're:https://cdn\.whyp\.it/.+\.jpg',
        },
    }, {
        'url': 'https://www.whyp.it/tracks/18337',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        unique_id, display_id = self._match_valid_url(url).group('id', 'display_id')
        webpage = self._download_webpage(url, unique_id or display_id)
        data = traverse_obj(
            self._search_nuxt_json(webpage, unique_id or display_id),
            ('pinia', {dict}, {require('pinia data')}))
        track_data = traverse_obj(
            data, ('track', 'data', ..., {dict}, any, {require('track data')}))

        return {
            'id': unique_id,
            'formats': [{
                'url': track_data[f'{prefix}_url'],
                'format_id': prefix,
                'filesize': int_or_none(track_data.get(f'{prefix}_size')),
                'vcodec': 'none',
                'quality': 10 if prefix == 'lossless' else -1,
                'http_headers': {'Referer': 'https://whyp.it/'},
            } for prefix in ('audio', 'lossy', 'lossless') if url_or_none(track_data.get(f'{prefix}_url'))],
            **traverse_obj(track_data, {
                'id': ('id', {int}, {str_or_none}),
                'title': ('title', {str}),
                'display_id': ('slug', {str}),
                'description': 'description',
                'duration': ('duration', {float_or_none}),
                'timestamp': ('created_at', {parse_iso8601}),
                'thumbnail': ('artwork_url', {url_or_none}),
            }),
            **traverse_obj(data, ('user', 'data', ..., {dict}, any, {
                'uploader': ('username', {str}),
                'uploader_id': ('id', {int}, {str_or_none}),
            })),
        }
