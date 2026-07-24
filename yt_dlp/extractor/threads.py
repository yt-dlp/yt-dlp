import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    remove_end,
    strip_or_none,
    traverse_obj,
)


class ThreadsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?threads\.(?:net|com)/(?:@[^/]+/)?(?:post|t)/(?P<id>[^/?#&]+)'
    _NETRC_MACHINE = 'threads'
    _TESTS = [
        {
            'note': 'Post with single video, with username and post',
            'url': 'https://www.threads.com/@zuck/post/DHV7vTivqWD',
            'info_dict': {
                'channel': 'zuck',
                'channel_is_verified': True,
                'channel_url': 'https://www.threads.com/@zuck',
                'description': 'Me finding out Llama hit 1 BILLION downloads.',
                'ext': 'mp4',
                'id': 'DHV7vTivqWD',
                'like_count': int,
                'thumbnail': str,
                'timestamp': 1742305717,
                'title': 'Me finding out Llama hit 1 BILLION downloads.',
                'upload_date': '20250318',
                'uploader': 'zuck',
                'uploader_id': '63055343223',
                'uploader_url': 'https://www.threads.com/@zuck',
            },
        },
        {
            'note': 'Post with single video, without username and with t',
            'url': 'https://www.threads.com/t/DHV7vTivqWD',
            'info_dict': {
                'channel': 'zuck',
                'channel_is_verified': True,
                'channel_url': 'https://www.threads.com/@zuck',
                'description': 'Me finding out Llama hit 1 BILLION downloads.',
                'ext': 'mp4',
                'id': 'DHV7vTivqWD',
                'like_count': int,
                'thumbnail': str,
                'timestamp': 1742305717,
                'title': 'Me finding out Llama hit 1 BILLION downloads.',
                'upload_date': '20250318',
                'uploader': 'zuck',
                'uploader_id': '63055343223',
                'uploader_url': 'https://www.threads.com/@zuck',
            },
        },
        {
            'note': 'Post with carousel 2 images and 1 video',
            'url': 'https://www.threads.com/@zuck/post/DJDhoQfxb43',
            'info_dict': {
                'channel': 'zuck',
                'channel_is_verified': True,
                'channel_url': 'https://www.threads.com/@zuck',
                'description': 'md5:9146c2c42fd53aba9090f61ccfd64fc8',
                'id': 'DJDhoQfxb43',
                'like_count': int,
                'timestamp': 1745982529,
                'title': 'md5:9146c2c42fd53aba9090f61ccfd64fc8',
                'upload_date': '20250430',
                'uploader': 'zuck',
                'uploader_id': '63055343223',
                'uploader_url': 'https://www.threads.com/@zuck',
            },
            'playlist_count': 3,
        },
        {
            'note': 'Post with 1 image',
            'url': 'https://www.threads.com/@zuck/post/DI3mC0GxkYA',
            'info_dict': {
                'channel': 'zuck',
                'channel_is_verified': True,
                'channel_url': 'https://www.threads.com/@zuck',
                'description': 'md5:e292006574f5deb5552c1ad677cee8dd',
                'ext': 'webp',
                'id': 'DI3mC0GxkYA',
                'like_count': int,
                'timestamp': 1745582191,
                'title': 'md5:e292006574f5deb5552c1ad677cee8dd',
                'upload_date': '20250425',
                'uploader': 'zuck',
                'uploader_id': '63055343223',
                'uploader_url': 'https://www.threads.com/@zuck',
            },
        },
        {
            'note': 'Private Post',
            'url': 'https://www.threads.com/@enucatl/post/DLIrVcmPuFA7g5tn9OzPjsA-R8qU2HPJv_FzCo0',
            'info_dict': {
                'channel': 'enucatl',
                'channel_is_verified': False,
                'channel_url': 'https://www.threads.com/@enucatl',
                'description': '',
                'ext': 'mp4',
                'id': 'DLIrVcmPuFA7g5tn9OzPjsA-R8qU2HPJv_FzCo0',
                'like_count': int,
                'timestamp': 1745582191,
                'title': '',
                'upload_date': '20250620',
                'uploader': 'enucatl',
                'uploader_id': '63055343223',
                'uploader_url': 'https://www.threads.com/@enucatl',
            },
            'skip': 'private account, requires authentication',
        },
    ]

    def _perform_login(self, username, password):
        # We are not implementing direct login. Cookies are preferred.
        self.raise_login_required(
            'Login with username/password is not supported. '
            'Use --cookies or --cookies-from-browser to provide authentication.',
            method='cookies',
        )

    def _real_extract(self, url):
        post_id = self._match_id(url)
        webpage = self._download_webpage(url, post_id, note='Downloading post page')

        json_data = None

        json_scripts = re.findall(
            r'<script type="application/json"[^>]*?\sdata-sjs[^>]*?>(.*?)<\s*/script\s*>',
            webpage,
            re.DOTALL | re.IGNORECASE,
        )
        for script in json_scripts:
            if post_id not in script or 'RelayPrefetchedStreamCache' not in script:
                continue
            # This script is a candidate. Try to parse it.
            # We use fatal=False because we expect some candidates to fail parsing.
            candidate_json = self._search_json(r'"result":', script, 'result data', post_id, fatal=False)

            if not candidate_json:
                continue

            post_data = traverse_obj(
                candidate_json,
                (
                    'data',
                    'data',
                    'edges',
                ),
            )

            if post_data is not None:
                json_data = post_data
                break

        if not json_data:
            self.raise_no_formats(
                'Could not extract post data. The post may be private or deleted. You may need to log in.',
                expected=True,
            )

        main_post = None
        for node in json_data:
            for item in traverse_obj(node, ('node', 'thread_items'), default=[]):
                post_candidate = item.get('post')
                if traverse_obj(post_candidate, 'code') == post_id:
                    main_post = post_candidate
                    break
            if main_post:
                break

        if not main_post:
            self.raise_no_formats('Could not find post data matching the post ID.', expected=True)

        # This metadata applies to the whole post (the playlist).
        uploader = traverse_obj(main_post, ('user', 'username'))
        caption = traverse_obj(main_post, ('caption', 'text'))
        title = (
            caption
            or strip_or_none(remove_end(self._html_extract_title(webpage), '• Threads'))
            or f'Post by {uploader}'
        )

        playlist_metadata = {
            'id': post_id,
            'title': title,
            'description': caption or self._og_search_description(webpage),
            'uploader': uploader,
            'uploader_id': traverse_obj(main_post, ('user', 'pk')),
            'uploader_url': f'https://www.threads.com/@{uploader}',
            'channel': uploader,
            'channel_url': f'https://www.threads.com/@{uploader}',
            'channel_is_verified': traverse_obj(main_post, ('user', 'is_verified')),
            'timestamp': int_or_none(main_post.get('taken_at')),
            'like_count': int_or_none(main_post.get('like_count')),
        }

        media_list = main_post.get('carousel_media') or [main_post]
        playlist_entries = []

        for i, media in enumerate(media_list):
            entry_id = f'{post_id}_{i + 1}' if len(media_list) > 1 else post_id

            # --- VIDEO ---
            if media.get('video_versions'):
                formats = []
                for video in media.get('video_versions'):
                    formats.append({
                        # 'format_id' is optional, yt-dlp can generate it
                        'url': video.get('url'),
                        'width': int_or_none(video.get('width')),
                        'height': int_or_none(video.get('height')),
                    })

                # Create a dictionary for THIS video entry
                playlist_entries.append({
                    'id': entry_id,
                    'title': title,  # The title is shared by all entries
                    'formats': formats,
                    'thumbnail': traverse_obj(media, ('image_versions2', 'candidates', 0, 'url')),
                    # Add any media-specific metadata here
                })
                continue  # Move to the next media item

            # --- IMAGE ---
            image_candidates = traverse_obj(media, ('image_versions2', 'candidates'))
            if image_candidates:
                best_image = image_candidates[0]
                playlist_entries.append({
                    'id': entry_id,
                    'title': title,
                    'url': best_image.get('url'),
                    'ext': determine_ext(best_image.get('url'), 'jpg'),
                    'width': int_or_none(best_image.get('width')),
                    'height': int_or_none(best_image.get('height')),
                    'vcodec': 'none',  # This tells yt-dlp it's an image
                })

        if not playlist_entries:
            self.raise_no_formats('This post contains no downloadable video or images.', expected=True)

        if len(playlist_entries) == 1:
            return {**playlist_entries[0], **playlist_metadata}

        return self.playlist_result(playlist_entries, **playlist_metadata)


class ThreadsIOSIE(InfoExtractor):
    IE_DESC = 'IOS barcelona:// URL'
    _VALID_URL = r'barcelona://media\?shortcode=(?P<id>[^/?#&]+)'
    _TESTS = [
        {
            'url': 'barcelona://media?shortcode=C6fDehepo5D',
            'info_dict': {
                'channel': 'saopaulofc',
                'channel_is_verified': bool,
                'channel_url': 'https://www.threads.com/@saopaulofc',
                'description': 'md5:0c36a7e67e1517459bc0334dba932164',
                'ext': 'mp4',
                'id': 'C6fDehepo5D',
                'like_count': int,
                'thumbnail': r're:^https?://.*\.jpg',
                'timestamp': 1714694014,
                'title': 'md5:be7fe42330e2e78e969ca30254535d0b',
                'upload_date': '20240502',
                'uploader': 'saopaulofc',
                'uploader_id': '63360239523',
                'uploader_url': 'https://www.threads.com/@saopaulofc',
            },
            'add_ie': ['Threads'],
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        # Threads doesn't care about the user url, it redirects to the right one
        # So we use ** instead so that we don't need to find it
        return self.url_result(f'https://www.threads.net/t/{video_id}', ThreadsIE, video_id)
