import json
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class ThreadsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?threads\.com/(?:@(?P<user>[^/]+)/post|t)/(?P<id>[A-Za-z0-9_-]+)'
    _TESTS = [{
        'url': 'https://www.threads.com/@azatstr/post/DU04gATDD4e',
        'info_dict': {
            'id': 'DU04gATDD4e',
            'ext': 'mp4',
            'title': 'Video by azatstr',
            'uploader': 'azatstr',
            'uploader_id': 'azatstr',
            'like_count': int,
            'comment_count': int,
            'timestamp': 1771261019,
            'upload_date': '20260216',
            'thumbnail': r're:^https?://.*\.jpg',
        },
    }, {
        # Short URL format
        'url': 'https://www.threads.com/t/DU04gATDD4e',
        'only_matching': True,
    }]
    _NETRC_MACHINE = 'threads'

    def _find_media_in_relay_data(self, data):
        """Recursively search parsed JSON for the first dict with a non-empty ``video_versions`` list."""
        if isinstance(data, dict):
            if isinstance(data.get('video_versions'), list) and data['video_versions']:
                return data
            for v in data.values():
                if result := self._find_media_in_relay_data(v):
                    return result
        elif isinstance(data, list):
            for item in data:
                if result := self._find_media_in_relay_data(item):
                    return result
        return None

    def _extract_relay_media(self, webpage):
        """Search ``<script type="application/json">`` tags for Relay-embedded video data."""
        for json_str in re.findall(
                r'<script\s+type="application/json"[^>]*>(.*?)</script>',
                webpage, re.DOTALL):
            if 'video_versions' not in json_str:
                continue
            try:
                media = self._find_media_in_relay_data(json.loads(json_str))
            except (json.JSONDecodeError, ValueError):
                continue
            if media:
                self.write_debug('Found video data in embedded Relay data')
                return media

        # Regex fallback: grab raw video_versions arrays
        for mobj in re.finditer(r'"video_versions"\s*:\s*(\[\s*\{[^\]]+\])', webpage):
            try:
                vv = json.loads(mobj.group(1))
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(vv, list) and vv:
                self.write_debug('Found video_versions via regex fallback')
                return {'video_versions': vv}
        return None

    def _extract_formats(self, media, webpage):
        """Build formats from ``video_versions`` or direct URL patterns in HTML."""
        formats = [{
            'format_id': str_or_none(fmt.get('type')),
            'url': fmt_url,
            'width': int_or_none(fmt.get('width')),
            'height': int_or_none(fmt.get('height')),
        } for fmt in traverse_obj(media, 'video_versions') or []
            if (fmt_url := url_or_none((fmt.get('url') or '').replace('\\/', '/')))]

        if formats:
            return formats

        # Fallback: scrape direct video URL from the page
        for pattern in (
            r'"video_url"\s*:\s*"([^"]+)"',
            r'<video[^>]+\bsrc="([^"]+)"',
        ):
            if video_url := url_or_none(
                    (self._search_regex(pattern, webpage, 'video url', default=None) or '')
                    .replace('\\/', '/')):
                return [{'url': video_url}]
        return []

    def _real_extract(self, url):
        video_id, user = self._match_valid_url(url).group('id', 'user')
        webpage = self._download_webpage(url, video_id)

        media = self._extract_relay_media(webpage) or {}
        formats = self._extract_formats(media, webpage)

        if not formats:
            if traverse_obj(media, 'image_versions2') or re.search(
                    r'"video_versions"\s*:\s*null', webpage):
                raise ExtractorError(
                    'This post is an image, not a video', expected=True)
            self.raise_login_required(
                'Could not extract video. Try passing cookies '
                'with --cookies-from-browser or --cookies')

        thumbnails = [{
            'url': thumb_url,
            'width': int_or_none(thumb.get('width')),
            'height': int_or_none(thumb.get('height')),
        } for thumb in traverse_obj(media, ('image_versions2', 'candidates')) or []
            if (thumb_url := url_or_none(thumb.get('url')))]

        if not user:
            user = (
                traverse_obj(media, ('user', 'username'), expected_type=str)
                or self._search_regex(
                    r'threads\.com/@([^/?#]+)', url, 'username', default=None)
                or self._search_regex(
                    r'"username"\s*:\s*"([^"]+)"', webpage, 'username', default=None))

        caption = traverse_obj(media, ('caption', 'text'), expected_type=str)

        return {
            'id': video_id,
            'title': f'Video by {user}' if user else 'Threads video',
            'description': caption or self._og_search_description(webpage, default=None),
            'uploader': user,
            'uploader_id': user,
            'formats': formats,
            'thumbnails': thumbnails,
            'duration': float_or_none(media.get('video_duration')),
            'like_count': int_or_none(media.get('like_count')),
            'comment_count': int_or_none(traverse_obj(
                media, ('text_post_app_info', 'direct_reply_count'))),
            'view_count': int_or_none(media.get('view_count')),
            'timestamp': int_or_none(media.get('taken_at')),
        }
