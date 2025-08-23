from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    remove_end,
    strip_or_none,
    traverse_obj,
    url_or_none,
)


class NZOnScreenVideoIE(InfoExtractor):
    """Extract individual video with fresh URLs"""
    _VALID_URL = r'nzonscreen:video:(?P<id>[^:]+):(?P<uuid>[a-f0-9]+)'

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        display_id = mobj.group('id')
        uuid = mobj.group('uuid')

        # Fetch fresh video data to get non-expired URLs
        try:
            video_data = self._download_json(
                f'https://www.nzonscreen.com/html5/video_data/{display_id}',
                uuid, note=f'Downloading fresh video data for {uuid}', fatal=False)

            if video_data and isinstance(video_data, list):
                # Find the specific video by UUID
                playlist = None
                for video in video_data:
                    if video.get('uuid') == uuid:
                        playlist = video
                        break

                if not playlist:
                    raise ExtractorError(f'Video {uuid} not found in playlist')
            else:
                raise ExtractorError('Failed to get video data')

        except Exception as e:
            raise ExtractorError(f'Failed to extract video {uuid}: {e!s}')

        return {
            'id': uuid,
            'display_id': display_id,
            'title': strip_or_none(playlist.get('label')),
            'description': strip_or_none(playlist.get('description')),
            'thumbnail': traverse_obj(playlist, ('thumbnail', 'path')),
            'duration': float_or_none(playlist.get('duration')),
            'formats': self._extract_formats(playlist, uuid),
            'http_headers': {
                'Referer': 'https://www.nzonscreen.com/',
                'Origin': 'https://www.nzonscreen.com/',
            },
        }

    def _extract_formats(self, playlist, video_id):
        # Extract fresh stream URLs to avoid expiration issues
        formats = []
        for quality, (id_, url) in enumerate(traverse_obj(
                playlist, ('h264', {'lo': 'lo_res', 'hi': 'hi_res'}), expected_type=url_or_none).items()):
            if not url:
                continue
            formats.append({
                'url': url,
                'format_id': id_,
                'ext': 'mp4',
                'quality': quality,
                'height': int_or_none(playlist.get('height')) if id_ == 'hi' else None,
                'width': int_or_none(playlist.get('width')) if id_ == 'hi' else None,
                'filesize_approx': float_or_none(traverse_obj(playlist, ('h264', f'{id_}_res_mb')), invscale=1024**2),
            })
        return formats


class NZOnScreenIE(InfoExtractor):
    _VALID_URL = r'https?://www\.nzonscreen\.com/title/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.nzonscreen.com/title/shoop-shoop-diddy-wop-cumma-cumma-wang-dang-1982',
        'info_dict': {
            'id': '726ed6585c6bfb30',
            'ext': 'mp4',
            'format_id': 'hi',
            'display_id': 'shoop-shoop-diddy-wop-cumma-cumma-wang-dang-1982',
            'title': 'Monte Video - "Shoop Shoop, Diddy Wop"',
            'description': 'Monte Video - "Shoop Shoop, Diddy Wop"',
            'alt_title': 'Shoop Shoop Diddy Wop Cumma Cumma Wang Dang | Music Video',
            'thumbnail': r're:https://www\.nzonscreen\.com/content/images/.+\.jpg',
            'duration': 158,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.nzonscreen.com/title/shes-a-mod-1964?collection=best-of-the-60s',
        'info_dict': {
            'id': '3dbe709ff03c36f1',
            'ext': 'mp4',
            'format_id': 'hi',
            'display_id': 'shes-a-mod-1964',
            'title': 'Ray Columbus - \'She\'s A Mod\'',
            'description': 'Ray Columbus - \'She\'s A Mod\'',
            'alt_title': 'She\'s a Mod | Music Video',
            'thumbnail': r're:https://www\.nzonscreen\.com/content/images/.+\.jpg',
            'duration': 130,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.nzonscreen.com/title/puha-and-pakeha-1968/overview',
        'info_dict': {
            'id': 'f86342544385ad8a',
            'ext': 'mp4',
            'format_id': 'hi',
            'display_id': 'puha-and-pakeha-1968',
            'title': 'Looking At New Zealand - Puha and Pakeha',
            'alt_title': 'Looking at New Zealand - \'Pūhā and Pākehā\' | Television',
            'description': 'An excerpt from this television programme.',
            'duration': 212,
            'thumbnail': r're:https://www\.nzonscreen\.com/content/images/.+\.jpg',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # Multiple videos (trailer + full length)
        'url': 'https://www.nzonscreen.com/title/the-deadly-ponies-gang-2013',
        'info_dict': {
            'id': 'the-deadly-ponies-gang-2013',
            'title': 'The Deadly Ponies Gang | Film',
        },
        'playlist_count': 2,
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        # Try to get multiple videos from the video_data endpoint first
        try:
            video_data = self._download_json(
                f'https://www.nzonscreen.com/html5/video_data/{video_id}', video_id,
                note='Downloading video data', fatal=False)

            if video_data and isinstance(video_data, list) and len(video_data) > 1:
                # Multiple videos found, return a playlist with fresh URL delegation
                # Each playlist entry delegates to NZOnScreenVideoIE for fresh URLs
                entries = []
                for video in video_data:
                    uuid = video.get('uuid')
                    if not uuid:
                        continue
                    entries.append({
                        '_type': 'url_transparent',
                        'url': f'nzonscreen:video:{video_id}:{uuid}',
                        'ie_key': 'NZOnScreenVideo',
                        'id': uuid,
                        'title': strip_or_none(video.get('label')),
                        'description': strip_or_none(video.get('description')),
                        'thumbnail': traverse_obj(video, ('thumbnail', 'path')),
                        'duration': float_or_none(video.get('duration')),
                    })

                # Get page title for the playlist
                page_title = strip_or_none(remove_end(
                    self._html_extract_title(webpage, default=None) or self._og_search_title(webpage),
                    ' | NZ On Screen'))

                return self.playlist_result(entries, video_id, page_title)

            elif video_data and isinstance(video_data, list) and len(video_data) == 1:
                # Single video from API - delegate to video extractor for fresh URLs
                uuid = video_data[0].get('uuid')
                if uuid:
                    return {
                        '_type': 'url_transparent',
                        'url': f'nzonscreen:video:{video_id}:{uuid}',
                        'ie_key': 'NZOnScreenVideo',
                    }
                playlist = video_data[0]
            else:
                # Fallback to original method
                raise ExtractorError('No video data from API')

        except Exception:
            # Fallback to original extraction method
            playlist = self._parse_json(self._html_search_regex(
                r'data-video-config=\'([^\']+)\'', webpage, 'media data'), video_id)

            # For fallback, also delegate to video extractor for fresh URLs
            uuid = playlist.get('uuid')
            if uuid:
                return {
                    '_type': 'url_transparent',
                    'url': f'nzonscreen:video:{video_id}:{uuid}',
                    'ie_key': 'NZOnScreenVideo',
                    'title': strip_or_none(remove_end(
                        self._html_extract_title(webpage, default=None) or self._og_search_title(webpage),
                        ' | NZ On Screen')),
                }

            # Final fallback - extract directly but this may have expired URLs
            return {
                'id': uuid or video_id,
                'display_id': video_id,
                'title': strip_or_none(playlist.get('label')),
                'description': strip_or_none(playlist.get('description')),
                'alt_title': strip_or_none(remove_end(
                    self._html_extract_title(webpage, default=None) or self._og_search_title(webpage),
                    ' | NZ On Screen')),
                'thumbnail': traverse_obj(playlist, ('thumbnail', 'path')),
                'duration': float_or_none(playlist.get('duration')),
                'formats': self._extract_legacy_formats(playlist),
                'http_headers': {
                    'Referer': 'https://www.nzonscreen.com/',
                    'Origin': 'https://www.nzonscreen.com/',
                },
            }

    def _extract_legacy_formats(self, playlist):
        # Legacy format extraction for fallback cases
        formats = []
        for quality, (id_, url) in enumerate(traverse_obj(
                playlist, ('h264', {'lo': 'lo_res', 'hi': 'hi_res'}), expected_type=url_or_none).items()):
            if not url:
                continue
            formats.append({
                'url': url,
                'format_id': id_,
                'ext': 'mp4',
                'quality': quality,
                'height': int_or_none(playlist.get('height')) if id_ == 'hi' else None,
                'width': int_or_none(playlist.get('width')) if id_ == 'hi' else None,
                'filesize_approx': float_or_none(traverse_obj(playlist, ('h264', f'{id_}_res_mb')), invscale=1024**2),
            })
        return formats
