import itertools
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    clean_html,
    format_field,
    int_or_none,
    unified_strdate,
    unified_timestamp,
)
from ..utils.traversal import traverse_obj


class ForendorsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?forendors\.cz/(?:p/(?P<id>[0-9]+)|(?P<slug>[^/]+))'
    _NETRC_MACHINE = 'forendors'
    _API_BASE = 'https://api.forendors.cz'
    _BASE_URL = 'https://www.forendors.cz'
    _TESTS = [{
        'url': 'https://www.forendors.cz/p/733045644230530172',
        'info_dict': {
            'id': '733045644230530172',
            'ext': 'mp4',
            'title': 'Představujeme vám nový editor příspěvků!',
            'description': 'md5:80105dc0c173aa0ea7a24bd5d11708d3',
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

    def _get_headers(self, csrf_token):
        """Prepare headers with CSRF token"""
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Referer': f'{self._BASE_URL}/',
        }
        if csrf_token:
            headers['x-xsrf-token'] = urllib.parse.unquote(csrf_token.value)
        return headers

    def _extract_thumbnails(self, cover):
        """Extract thumbnails from cover dict"""
        thumbnails = []
        if isinstance(cover, dict):
            if cover.get('desktop'):
                thumbnails.append({'id': 'desktop', 'url': cover.get('desktop')})
            if cover.get('mobile'):
                thumbnails.append({'id': 'mobile', 'url': cover.get('mobile')})
        return thumbnails

    def _has_media_components(self, components):
        """Check if components list has any video or audio components"""
        return any(c.get('type') in ('video', 'audio') for c in components)

    def _check_no_media_components(self, components, video_id):
        """Check if there are no media components and return None if so"""
        if not self._has_media_components(components):
            component_types = [c.get('type') for c in components if c.get('type')]
            self.report_warning(
                f'Post {video_id} has no video or audio content (found: {", ".join(component_types) or "none"}). Skipping.')
            return None
        return False

    def _check_no_audio_video_component(self, component, post_hash):
        """Check if component is not audio_video type and return None if so"""
        component_type = component.get('type')
        if component_type != 'audio_video':
            self.to_screen(
                f'Skipping post {post_hash} - no audio_video content '
                f'(found type: {component_type or "none"})')
            return None
        return False

    def _check_no_formats(self, formats, post_hash):
        """Check if formats list is empty and return None if so"""
        if not formats:
            self.to_screen(
                f'Skipping post {post_hash} - no playable audio or video found')
            return None
        return False

    def _extract_formats_from_detail_id(self, detail_id, video_id, media_type, headers):
        """Extract formats and subtitles from a detail_id"""
        component_data = self._download_json(
            f'{self._API_BASE}/post/video/{detail_id}?type=url',
            video_id, note=f'Downloading {media_type} playback info', headers=headers)

        playback_url = component_data.get('playback_url')
        if not playback_url:
            return None, None

        component_formats, component_subtitles = self._extract_m3u8_formats_and_subtitles(
            playback_url, video_id, 'mp4', m3u8_id=f'hls-{media_type}')

        return component_formats, component_subtitles

    def _build_info_dict(self, video_id, title, description, thumbnails, formats, subtitles,
                         published_at, author, like_count, comment_count):
        """Build the info dictionary with common fields"""
        handle = traverse_obj(author, 'handle')
        return {
            'id': video_id,
            'title': title or video_id,
            'description': description,
            'thumbnails': thumbnails,
            'formats': formats,
            'subtitles': subtitles,
            'modified_timestamp': unified_timestamp(published_at),
            'modified_date': unified_strdate(published_at),
            'channel': traverse_obj(author, 'name'),
            'channel_id': handle,
            'channel_url': format_field(handle, None, f'{self._BASE_URL}/%s'),
            'like_count': int_or_none(like_count),
            'comment_count': int_or_none(comment_count),
        }

    def _extract_video(self, video_id, headers):
        """Extract a single video"""
        # Fetch post metadata from API
        data = self._download_json(
            f'{self._API_BASE}/v2/detail/post/{video_id}',
            video_id, note='Downloading post metadata', headers=headers)

        # Check if video is accessible
        if 'is_accessible' in data and data.get('is_accessible') is False:
            self.raise_login_required(
                'This video is not available. Authentication may be required.',
                metadata_available=True)

        # Extract all video and audio components
        formats = []
        subtitles = {}
        components = data.get('components', [])

        # Check if there are any video or audio components
        if self._check_no_media_components(components, video_id):
            return None

        # Extract description from text component
        description = None
        for component in components:
            if component.get('type') == 'text':
                description = clean_html(component.get('text'))
                break

        # Extract thumbnails from cover
        thumbnails = self._extract_thumbnails(data.get('cover', {}))

        for component in components:
            component_type = component.get('type')
            detail_id = component.get('detail_id')

            if not detail_id or component_type not in ('video', 'audio'):
                continue

            component_formats, component_subtitles = self._extract_formats_from_detail_id(
                detail_id, video_id, component_type, headers)

            if component_formats is not None:
                formats.extend(component_formats)
            if component_subtitles is not None:
                for lang, subs in component_subtitles.items():
                    subtitles.setdefault(lang, []).extend(subs)

        return self._build_info_dict(
            video_id, data.get('title'), description, thumbnails, formats, subtitles,
            data.get('published_at'), traverse_obj(data, 'author', expected_type=dict),
            data.get('likes_count'), data.get('comments_count'))

    def _extract_from_playlist_entry(self, post, headers):
        """Extract video from a playlist entry"""
        post_hash = post.get('hash')
        if not post_hash:
            self.to_screen('Skipping post - no hash found')
            return None

        # Check if video is accessible
        if 'is_accessible' in post and post.get('is_accessible') is False:
            self.raise_login_required(
                'This video is not available. Authentication may be required.',
                metadata_available=True)

        # In playlist entries, "component" is a dict (not "components" list)
        component = post.get('component', {})

        # Check if this is an audio_video type
        if self._check_no_audio_video_component(component, post_hash):
            return None

        # Extract description from perex
        description = clean_html(post.get('perex'))

        # Extract thumbnails from cover
        thumbnails = self._extract_thumbnails(post.get('cover', {}))

        # Extract detail_ids from audio and video
        formats = []
        subtitles = {}

        for media_type in ('audio', 'video'):
            media_data = component.get(media_type, {})
            detail_id = media_data.get('detail_id')

            if not detail_id:
                continue

            component_formats, component_subtitles = self._extract_formats_from_detail_id(
                detail_id, post_hash, media_type, headers)

            if component_formats is not None:
                formats.extend(component_formats)
            if component_subtitles is not None:
                for lang, subs in component_subtitles.items():
                    subtitles.setdefault(lang, []).extend(subs)

        if self._check_no_formats(formats, post_hash):
            return None

        return self._build_info_dict(
            post_hash, post.get('title'), description, thumbnails, formats, subtitles,
            post.get('published_at'), traverse_obj(post, 'author', expected_type=dict),
            post.get('likes_count'), post.get('comments_count'))

    def _entries(self, slug, headers):
        """Generator for playlist entries"""
        for page_num in itertools.count(1):
            page_data = self._download_json(
                f'{self._API_BASE}/v2/detail/user/{slug}/posts',
                slug, note=f'Downloading page {page_num}',
                headers=headers, query={'page': page_num})

            for post in page_data.get('data', []):
                # Extract directly from playlist entry
                result = self._extract_from_playlist_entry(post, headers)
                if result:
                    yield result

            # Check if we've reached the last page
            current_page = page_data.get('current_page', page_num)
            last_page = page_data.get('last_page', current_page)
            if current_page >= last_page:
                break

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        slug = mobj.group('slug')

        # Get CSRF token from cookies
        csrf_token = self._get_cookies(self._API_BASE).get('XSRF-TOKEN')

        # If CSRF token not found, request the main page to set it
        if not csrf_token:
            page_id = video_id or slug
            self._request_webpage(url, page_id,
                                  note='Requesting CSRF token cookie')
            csrf_token = self._get_cookies(self._API_BASE).get('XSRF-TOKEN')

        headers = self._get_headers(csrf_token)

        # Check if this is a playlist (slug) or a single video (id)
        if slug:
            # Return playlist
            return self.playlist_result(self._entries(slug, headers),
                                        playlist_id=slug)
        else:
            # Return single video
            return self._extract_video(video_id, headers)
