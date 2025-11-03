import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    url_or_none,
)


class EromeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?erome\.com/a/(?P<id>[0-9A-Za-z]+)'
    _TESTS = [{
        'url': 'https://www.erome.com/a/puDn9Ypp',
        'info_dict': {
            'id': 'puDn9Ypp',
            'title': 'Gostosa de bikini',
            'age_limit': 18,
            'description': 'md5:8fcf452a31183ad6a23800adcd98c9f7',
        },
        'playlist_mincount': 15,
    }]

    def _real_extract(self, url):
        album_id = self._match_id(url)

        # Set age verification cookies before downloading
        self._set_cookie('erome.com', 'age_verified', '1')
        self._set_cookie('www.erome.com', 'age_verified', '1')

        webpage = self._download_webpage(url, album_id)

        # Check if content exists
        if any(x in webpage for x in [
            'This album no longer exists',
            'Album not found',
            'Album has been removed',
            'Page not found',
        ]):
            raise ExtractorError('Album not found', expected=True)

        # Extract title with better patterns
        title = self._html_search_regex(
            [r'<h1[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</h1>',
             r'<title>([^<]+)</title>'],
            webpage, 'title', default='Untitled')

        # Clean title
        title = clean_html(title) or 'Untitled'
        if 'EroMe' in title:
            title = title.replace('EroMe - ', '').replace(' - EroMe', '').strip()
        if not title:
            title = 'Untitled'

        # Extract description if available
        description = self._html_search_regex(
            r'<meta name="description" content="([^"]+)"',
            webpage, 'description', fatal=False)

        # Extract uploader - skip for now as pattern may vary
        uploader = None

        entries = []

        # Find video sources with multiple patterns
        video_patterns = [
            r'<source[^>]+src="([^"]+\.(?:mp4|webm|avi|mov|flv)(?:\?[^"]*)?)"[^>]*>',
            r'<video[^>]+src="([^"]+)"',
            r'"videoUrl":\s*"([^"]+)"',
        ]

        video_sources = []
        for pattern in video_patterns:
            matches = re.findall(pattern, webpage, re.IGNORECASE)
            video_sources.extend(matches)

        # Remove duplicates while preserving order
        video_sources = list(dict.fromkeys(video_sources))

        for i, video_url in enumerate(video_sources):
            if video_url.startswith('//'):
                video_url = 'https:' + video_url
            elif video_url.startswith('/'):
                video_url = f'https://www.erome.com{video_url}'

            video_url = url_or_none(video_url)
            if video_url:
                entries.append({
                    'id': f'{album_id}_video_{i + 1}',
                    'url': video_url,
                    'title': f'{title} - Video {i + 1}',
                    'uploader': uploader,
                    'description': description,
                })

        # Extract images - look for content images in the album directory
        img_pattern = r'<img[^>]+src="(https?://s\d+\.erome\.com/\d+/' + re.escape(album_id) + r'/[^"]*\.(?:jpg|jpeg|png|gif)(?:\?[^"]*)?)"[^>]*>'
        img_matches = re.finditer(img_pattern, webpage, re.IGNORECASE)

        img_count = 0
        for match in img_matches:
            img_url = match.group(1)
            if img_url:
                # Skip thumbnails and small images
                if not any(x in img_url for x in ['thumb', '_s.', '_t.', '/t/']):
                    img_url = url_or_none(img_url)
                    if img_url:
                        img_count += 1
                        entries.append({
                            'id': f'{album_id}_img_{img_count}',
                            'url': img_url,
                            'title': f'{title} - Image {img_count}',
                            'uploader': uploader,
                            'ext': 'jpg',
                            'description': description,
                        })

        if not entries:
            raise ExtractorError('No media found', expected=True)

        return self.playlist_result(
            entries, album_id, title, description, uploader=uploader, age_limit=18)


class EromeProfileIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?erome\.com/(?P<id>[a-zA-Z0-9_-]+)(?:/page/(?P<page>\d+))?'
    _TESTS = [{
        'url': 'https://www.erome.com/username',
        'info_dict': {
            'id': 'username',
            'title': 'username - EroMe Profile',
            'age_limit': 18,
        },
        'playlist_mincount': 1,
        'skip': 'Profile test - requires valid profile URL',
    }]

    @classmethod
    def suitable(cls, url):
        return (False if EromeIE.suitable(url) else
                super().suitable(url))

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        profile_id = mobj.group('id')
        page = mobj.group('page') or '1'

        # Set age verification cookies before downloading
        self._set_cookie('erome.com', 'age_verified', '1')
        self._set_cookie('www.erome.com', 'age_verified', '1')

        webpage = self._download_webpage(url, profile_id)

        # Check if profile exists
        if any(x in webpage for x in [
            'User not found',
            'Profile not found',
            'This user does not exist',
            'Page not found',
        ]):
            raise ExtractorError('Profile not found', expected=True)

        # Extract profile title
        title = self._html_search_regex(
            [r'<h1[^>]*class="[^"]*username[^"]*"[^>]*>([^<]+)</h1>',
             r'<title>([^<]+)</title>'],
            webpage, 'title', default=f'{profile_id} - EroMe Profile')

        title = clean_html(title).strip()

        # Extract profile description if available
        description = self._html_search_regex(
            r'<meta name="description" content="([^"]+)"',
            webpage, 'description', fatal=False)

        # Find album links
        album_links = re.findall(r'href="(/a/[a-zA-Z0-9]+)"', webpage)

        # Remove duplicates while preserving order
        album_links = list(dict.fromkeys(album_links))

        entries = []
        for album_path in album_links:
            album_url = f'https://www.erome.com{album_path}'
            album_id = album_path.split('/')[-1]
            entries.append(self.url_result(
                album_url, EromeIE.ie_key(),
                video_id=album_id,
                video_title=f'{profile_id} - Album {album_id}'))

        if not entries:
            raise ExtractorError('No albums found on this profile')

        playlist_title = f'{title} - Page {page}' if page != '1' else title
        playlist_id = f'{profile_id}_page_{page}' if page != '1' else profile_id

        return {
            '_type': 'playlist',
            'id': playlist_id,
            'title': playlist_title,
            'description': description,
            'entries': entries,
            'age_limit': 18,
        }
