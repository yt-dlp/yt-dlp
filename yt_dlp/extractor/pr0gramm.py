import json
from datetime import date
from urllib.parse import unquote

from .common import InfoExtractor
from ..compat import functools
from ..utils import ExtractorError, make_archive_id, urljoin
from ..utils.traversal import traverse_obj


class Pr0grammIE(InfoExtractor):
    _VALID_URL = r'https?://pr0gramm\.com\/(?:[^/?#]+/)+(?P<id>[\d]+)(?:[/?#:]|$)'
    _TESTS = [{
        # Tags require account
        'url': 'https://pr0gramm.com/new/video/5466437',
        'info_dict': {
            'id': '5466437',
            'ext': 'mp4',
            'title': 'pr0gramm-5466437 by g11st',
            'tags': ['Neon Genesis Evangelion', 'Touhou Project', 'Fly me to the Moon', 'Marisad', 'Marisa Kirisame', 'video', 'sound', 'Marisa', 'Anime'],
            'uploader': 'g11st',
            'uploader_id': 394718,
            'upload_timestamp': 1671590240,
            'upload_date': '20221221',
            'like_count': int,
            'dislike_count': int,
            'age_limit': 0,
            'thumbnail': r're:^https://thumb\.pr0gramm\.com/.*\.jpg',
        },
    }, {
        # Tags require account
        'url': 'https://pr0gramm.com/new/3052805:comment28391322',
        'info_dict': {
            'id': '3052805',
            'ext': 'mp4',
            'title': 'pr0gramm-3052805 by Hansking1',
            'tags': 'count:15',
            'uploader': 'Hansking1',
            'uploader_id': 385563,
            'upload_timestamp': 1552930408,
            'upload_date': '20190318',
            'like_count': int,
            'dislike_count': int,
            'age_limit': 0,
            'thumbnail': r're:^https://thumb\.pr0gramm\.com/.*\.jpg',
        },
    }, {
        # Requires verified account
        'url': 'https://pr0gramm.com/new/Gianna%20Michaels/5848332',
        'info_dict': {
            'id': '5848332',
            'ext': 'mp4',
            'title': 'pr0gramm-5848332 by erd0pfel',
            'tags': 'count:18',
            'uploader': 'erd0pfel',
            'uploader_id': 349094,
            'upload_timestamp': 1694489652,
            'upload_date': '20230912',
            'like_count': int,
            'dislike_count': int,
            'age_limit': 18,
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

    BASE_URL = 'https://pr0gramm.com'

    @functools.cached_property
    def _is_logged_in(self):
        return 'pp' in self._get_cookies(self.BASE_URL)

    @functools.cached_property
    def _maximum_flags(self):
        # We need to guess the flags for the content otherwise the api will raise an error
        # We can guess the maximum allowed flags for the account from the cookies
        # Bitflags are (msbf): nsfp, nsfl, nsfw, sfw
        flags = 0b0001
        if self._is_logged_in:
            flags |= 0b1000
            cookies = self._get_cookies(self.BASE_URL)
            if 'me' not in cookies:
                self._download_webpage(self.BASE_URL, None, 'Refreshing verification information')
            if traverse_obj(cookies, ('me', {lambda x: x.value}, {unquote}, {json.loads}, 'verified')):
                flags |= 0b0110

        return flags

    def _call_api(self, endpoint, video_id, query={}, note='Downloading API json'):
        data = self._download_json(
            f'https://pr0gramm.com/api/items/{endpoint}',
            video_id, note, query=query, expected_status=403)

        error = traverse_obj(data, ('error', {str}))
        if error in ('nsfwRequired', 'nsflRequired', 'nsfpRequired', 'verificationRequired'):
            if not self._is_logged_in:
                self.raise_login_required()
            raise ExtractorError(f'Unverified account cannot access NSFW/NSFL ({error})', expected=True)
        elif error:
            message = traverse_obj(data, ('msg', {str})) or error
            raise ExtractorError(f'API returned error: {message}', expected=True)

        return data

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_info = traverse_obj(
            self._call_api('get', video_id, {'id': video_id, 'flags': self._maximum_flags}),
            ('items', 0, {dict}))

        source = urljoin('https://img.pr0gramm.com', video_info.get('image'))
        if not source or not source.endswith('mp4'):
            self.raise_no_formats('Could not extract a video', expected=bool(source), video_id=video_id)

        tags = None
        if self._is_logged_in:
            metadata = self._call_api('info', video_id, {'itemId': video_id})
            tags = traverse_obj(metadata, ('tags', ..., 'tag', {str}))
            # Sorted by "confidence", higher confidence = earlier in list
            confidences = traverse_obj(metadata, ('tags', ..., 'confidence', ({int}, {float})))
            if confidences:
                tags = [tag for _, tag in sorted(zip(confidences, tags), reverse=True)]

        return {
            'id': video_id,
            'title': f'pr0gramm-{video_id} by {video_info.get("user")}',
            'formats': [{
                'url': source,
                'ext': 'mp4',
                **traverse_obj(video_info, {
                    'width': ('width', {int}),
                    'height': ('height', {int}),
                }),
            }],
            'tags': tags,
            'age_limit': 18 if traverse_obj(video_info, ('flags', {0b110.__and__})) else 0,
            '_old_archive_ids': [make_archive_id('Pr0grammStatic', video_id)],
            **traverse_obj(video_info, {
                'uploader': ('user', {str}),
                'uploader_id': ('userId', {int}),
                'like_count': ('up', {int}),
                'dislike_count': ('down', {int}),
                'upload_timestamp': ('created', {int}),
                'upload_date': ('created', {int}, {date.fromtimestamp}, {lambda x: x.strftime('%Y%m%d')}),
                'thumbnail': ('thumb', {lambda x: urljoin('https://thumb.pr0gramm.com', x)})
            }),
        }
