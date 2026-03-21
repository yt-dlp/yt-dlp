from .common import InfoExtractor
from ..utils import (
    int_or_none,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class XfansIE(InfoExtractor):
    IE_NAME = 'xfans'
    IE_DESC = 'xfans.tokyo'
    _VALID_URL = r'https?://(?:www\.)?xfans\.tokyo/(?:[a-z]{2}/)?posts/(?P<id>[0-9a-f-]{36})'
    _TESTS = [{
        'url': 'https://www.xfans.tokyo/en/posts/6c673534-5d02-4d60-ab0d-82b9349acd9a',
        'info_dict': {
            'id': '6c673534-5d02-4d60-ab0d-82b9349acd9a',
            'ext': 'mp4',
            'title': r're:.+',
            'description': r're:.+',
            'thumbnail': r're:https?://.+',
            'uploader': r're:.+',
            'uploader_id': r're:.+',
            'like_count': int,
            'comment_count': int,
            'age_limit': 18,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.xfans.tokyo/posts/6c673534-5d02-4d60-ab0d-82b9349acd9a',
        'only_matching': True,
    }]

    _API_BASE = 'https://api.xfans.tokyo/api'

    def _real_extract(self, url):
        post_id = self._match_id(url)

        post = self._download_json(
            f'{self._API_BASE}/posts/{post_id}', post_id,
            note='Downloading post info',
            headers={
                'Accept': 'application/json, text/plain, */*',
                'Origin': 'https://www.xfans.tokyo',
                'Referer': 'https://www.xfans.tokyo/',
            })

        video = post.get('video') or {}
        m3u8_url = video.get('video_url')
        if not m3u8_url:
            self.raise_no_formats('No video URL found in this post', video_id=post_id)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            m3u8_url, post_id, ext='mp4', m3u8_id='hls',
            headers={
                'Origin': 'https://www.xfans.tokyo',
                'Referer': 'https://www.xfans.tokyo/',
            })

        is_restricted = post.get('is_restricted', False)
        duration = int_or_none(video.get('main_video_time') if not is_restricted else video.get('total_time'))

        creator = post.get('creator') or {}

        return {
            'id': post_id,
            'formats': formats,
            'subtitles': subtitles,
            'duration': duration,
            'age_limit': 18 if creator.get('is_r18') else None,
            **traverse_obj(post, {
                'title': ('title', {str}),
                'description': ('description', {str}),
                'thumbnail': ('thumbnail_url', {url_or_none}),
                'like_count': ('likes', {int_or_none}),
                'comment_count': ('number_of_comments', {int_or_none}),
            }),
            **traverse_obj(creator, {
                'uploader': ('name', {str}),
                'uploader_id': ('nickname', {str}),
            }),
        }
