from datetime import date

from .common import InfoExtractor
from ..utils import urljoin
from ..utils.traversal import traverse_obj


class Pr0grammIE(InfoExtractor):
    _VALID_URL = r'https?://pr0gramm\.com\/(?:[^/?#]+/)+(?P<id>[\d]+)(?:[/?#:]|$)'
    _TESTS = [{
        'url': 'https://pr0gramm.com/new/video/5466437',
        'info_dict': {
            'id': '5466437',
            'ext': 'mp4',
            'title': 'pr0gramm-5466437 by g11st',
            'uploader': 'g11st',
            'uploader_id': 394718,
            'upload_timestamp': 1671590240,
            'upload_date': '20221221',
            'like_count': int,
            'dislike_count': int,
            'thumbnail': r're:^https://thumb\.pr0gramm\.com/.*\.jpg',
        },
    }, {
        'url': 'https://pr0gramm.com/new/3052805:comment28391322',
        'info_dict': {
            'id': '3052805',
            'ext': 'mp4',
            'title': 'pr0gramm-3052805 by Hansking1',
            'uploader': 'Hansking1',
            'uploader_id': 385563,
            'upload_timestamp': 1552930408,
            'upload_date': '20190318',
            'like_count': int,
            'dislike_count': int,
            'thumbnail': r're:^https://thumb\.pr0gramm\.com/.*\.jpg',
        },
    }, {
        'url': 'https://pr0gramm.com/static/5466437',
        'only_matching': True,
    }, {
        'url': 'https://pr0gramm.com/new/rowan%20atkinson%20herr%20bohne/3052805',
        'only_matching': True,
    }, {
        'url': 'https://pr0gramm.com/user/froschler/dafur-ist-man-hier/5091290',
        'only_matching': True,
    }]

    API_URL = 'https://pr0gramm.com/api/items/get'
    VIDEO_URL = 'https://img.pr0gramm.com'
    THUMB_URL = 'https://thumb.pr0gramm.com'

    def _real_extract(self, url):
        original_id = self._match_id(url)
        video_id = int(original_id)
        video_info = traverse_obj(
            self._download_json(self.API_URL, video_id, query={'id': video_id}),
            ('items', lambda _, v: v['id'] == video_id, {dict}), get_all=False) or {}

        source = urljoin(self.VIDEO_URL, video_info.get('image'))
        if not source or not source.endswith('mp4'):
            self.raise_no_formats('Could not extract a video', expected=bool(source), video_id=video_id)

        return {
            'id': original_id,
            'title': f'pr0gramm-{video_id} by {video_info.get("user")}',
            'formats': [{
                'url': source,
                'ext': 'mp4',
                **traverse_obj(video_info, {
                    'width': ('width', {int}),
                    'height': ('height', {int}),
                }),
            }],
            **traverse_obj(video_info, {
                'uploader': ('user', {str}),
                'uploader_id': ('userId', {int}),
                'like_count': ('up', {int}),
                'dislike_count': ('down', {int}),
                'upload_timestamp': ('created', {int}),
                'upload_date': ('created', {int}, {date.fromtimestamp}, {lambda x: x.strftime('%Y%m%d')}),
                'thumbnail': ('thumb', {lambda x: urljoin(self.THUMB_URL, x)})
            }),
        }
