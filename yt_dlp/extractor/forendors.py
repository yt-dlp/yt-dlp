import functools
import itertools
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    format_field,
    int_or_none,
    unified_strdate,
    unified_timestamp,
)
from ..utils.traversal import traverse_obj


class ForendorsBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'forendors'
    _API_BASE = 'https://api.forendors.cz'
    _BASE_URL = 'https://www.forendors.cz'

    @functools.cached_property
    def _api_headers(self):
        """Get API headers with CSRF token from cookies"""
        csrf_token = self._get_cookies(self._API_BASE).get('XSRF-TOKEN')
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Referer': f'{self._BASE_URL}/',
        }
        if csrf_token:
            headers['x-xsrf-token'] = urllib.parse.unquote(csrf_token.value)
        return headers

    def _ensure_csrf_token(self, url, page_id):
        """Ensure CSRF token cookie is set by requesting the page if needed"""
        if not self._get_cookies(self._API_BASE).get('XSRF-TOKEN'):
            self._request_webpage(url, page_id, note='Requesting CSRF token cookie')

    def _extract_thumbnails(self, post):
        """Extract thumbnails from post cover"""
        cover = post.get('cover', {})
        thumbnails = []
        if isinstance(cover, dict):
            if cover.get('desktop'):
                thumbnails.append({'id': 'desktop', 'url': cover.get('desktop')})
            if cover.get('mobile'):
                thumbnails.append({'id': 'mobile', 'url': cover.get('mobile')})
        return thumbnails

    def _extract_post(self, post_id, post):
        """Extract data from a post"""
        if 'is_accessible' in post and post.get('is_accessible') is False:
            self.raise_login_required(
                'This video is not available. Authentication may be required.',
                metadata_available=True)

        formats = []
        subtitles = {}

        for playback_url, media_type in self._extract_formats(post_id, post):
            component_formats, component_subtitles = self._extract_m3u8_formats_and_subtitles(
                playback_url, post_id, 'mp4', m3u8_id=f'hls-{media_type}')

            if component_formats:
                formats.extend(component_formats)
            if component_subtitles:
                for lang, subs in component_subtitles.items():
                    subtitles.setdefault(lang, []).extend(subs)

        if not formats:
            self.raise_no_formats('The post does not have any audio or video', expected=True, video_id=post_id)

        author = traverse_obj(post, 'author', expected_type=dict)
        handle = traverse_obj(author, 'handle')

        return {
            'id': post_id,
            'title': post.get('title') or post_id,
            'description': self._extract_description(post),
            'thumbnails': self._extract_thumbnails(post),
            'formats': formats,
            'subtitles': subtitles,
            'modified_timestamp': unified_timestamp(post.get('published_at')),
            'modified_date': unified_strdate(post.get('published_at')),
            'channel': traverse_obj(author, 'name'),
            'channel_id': handle,
            'channel_url': format_field(handle, None, f'{self._BASE_URL}/%s'),
            'like_count': int_or_none(post.get('likes_count')),
            'comment_count': int_or_none(post.get('comments_count')),
        }


class ForendorsIE(ForendorsBaseIE):
    _VALID_URL = r'https?://(?:www\.)?forendors\.cz/p/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://www.forendors.cz/p/733045644230530172',
        'info_dict': {
            'id': '733045644230530172',
            'ext': 'mp4',
            'title': 'Představujeme vám nový editor příspěvků!',
            'description': 'md5:80105dc0c173aa0ea7a24bd5d11708d3',
            'channel_url': str,
            'comment_count': int,
            'like_count': int,
            'modified_timestamp': int,
            'modified_date': str,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.forendors.cz/p/878709067231662806',
        'info_dict': {
            'id': '878709067231662806',
            'ext': 'mp4',
            'title': str,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Requires authentication',
    }, {
        'url': 'https://forendors.cz/p/987654321',
        'only_matching': True,
    }, {
        'url': 'https://www.forendors.cz/p/0e111e7be34de04a8b2cfdd254eecfb9',
        'info_dict': {
            'id': '0e111e7be34de04a8b2cfdd254eecfb9',
        },
        'skip': 'The post does not have any audio or video',
    }]

    def _extract_description(self, post):
        """Extract description from text component"""
        components = post.get('components', [])
        for component in components:
            if component.get('type') == 'text':
                return clean_html(component.get('text'))
        return None

    def _extract_formats(self, post_id, post):
        """Yield playback URLs from post components"""
        # In posts "components" is a list
        components = post.get('components', [])

        for component in components:
            component_type = component.get('type')
            detail_id = component.get('detail_id')

            if not detail_id or component_type not in ('video', 'audio'):
                continue

            component_data = self._download_json(
                f'{self._API_BASE}/post/video/{detail_id}?type=url',
                post_id, note=f'Downloading {component_type} playback info', headers=self._api_headers)

            playback_url = component_data.get('playback_url')
            if playback_url:
                yield playback_url, component_type

    def _real_extract(self, url):
        post_id = self._match_id(url)
        self._ensure_csrf_token(url, post_id)

        # Fetch post metadata from API
        post = self._download_json(
            f'{self._API_BASE}/v2/detail/post/{post_id}',
            post_id, note='Downloading post metadata', headers=self._api_headers)

        return self._extract_post(post_id, post)


class ForendorsChannelIE(ForendorsBaseIE):
    IE_NAME = 'forendors:channel'
    _VALID_URL = r'https?://(?:www\.)?forendors\.cz/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://www.forendors.cz/forendors',
        'info_dict': {
            'id': 'forendors',
        },
        'playlist_mincount': 1,
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.forendors.cz/jakfungujezivot',
        'info_dict': {
            'id': 'jakfungujezivot',
        },
        'playlist_mincount': 1,
        'params': {
            'skip_download': True,
        },
        'skip': 'Requires authentication',
    }, {
        'url': 'https://forendors.cz/somechannel',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return not ForendorsIE.suitable(url) and super().suitable(url)

    def _extract_description(self, post):
        """Extract description from perex field"""
        return clean_html(post.get('perex'))

    def _extract_formats(self, post_id, post):
        """Yield playback URLs from post component"""
        # In channel entries, "component" is a dict
        component = post.get('component') or {}

        for media_type in ('audio', 'video'):
            media_data = component.get(media_type, {})
            detail_id = media_data.get('detail_id')

            if not detail_id:
                continue

            component_data = self._download_json(
                f'{self._API_BASE}/post/video/{detail_id}?type=url',
                post_id, note=f'Downloading {media_type} playback info', headers=self._api_headers)

            playback_url = component_data.get('playback_url')
            if playback_url:
                yield playback_url, media_type

    def _entries(self, slug):
        """Generator for channel entries"""
        for page_num in itertools.count(1):
            page_data = self._download_json(
                f'{self._API_BASE}/v2/detail/user/{slug}/posts',
                slug, note=f'Downloading page {page_num}',
                headers=self._api_headers, query={'page': page_num})

            for post in page_data.get('data', []):
                post_id = post.get('hash')
                if not post_id:
                    self.to_screen('Skipping post - no hash found')
                    continue
                # Extract directly from channel entry
                try:
                    result = self._extract_post(post_id, post)
                except ExtractorError as error:
                    # Warn about entries that raised no formats or access denied
                    self.report_warning(error)
                    continue
                else:
                    if result:
                        yield result

            # Check if we've reached the last page
            current_page = page_data.get('current_page', page_num)
            last_page = page_data.get('last_page', current_page)
            if current_page >= last_page:
                break

    def _real_extract(self, url):
        slug = self._match_id(url)
        self._ensure_csrf_token(url, slug)

        # Return channel
        return self.playlist_result(self._entries(slug),
                                    playlist_id=slug)
