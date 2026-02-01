import functools

from .common import InfoExtractor
from ..utils import (
    InAdvancePagedList,
    clean_html,
    int_or_none,
    join_nonempty,
    unified_strdate,
    unified_timestamp,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class ForendorsBaseIE(InfoExtractor):
    _API_BASE = 'https://api.forendors.cz'
    _BASE_URL = 'https://www.forendors.cz'

    def _call_api(self, endpoint, video_id, note='Downloading API JSON', query=None):
        return self._download_json(
            f'{self._API_BASE}/{endpoint}', video_id, note=note,
            headers={
                'Accept': 'application/json, text/plain, */*',
                'Referer': f'{self._BASE_URL}/',
            }, query=query)

    def _extract_post(self, post_id, post):
        if post.get('is_accessible') is False:
            self.raise_login_required(
                'This video is not available. Authentication may be required.',
                metadata_available=True)

        # Description is only for entries, not for playlist
        description = join_nonempty(*traverse_obj(
            post, ('components', lambda _, v: v.get('type') == 'text', 'text', {clean_html}),
        ), delim='\n\n') or None

        common_metadata = {
            # Thumbnails location differs by endpoint:
            # - Post detail (/v2/detail/post/): cover is in components[].cover (extracted per-entry below)
            # - Channel posts (/v2/detail/user/.../posts): cover is at post level (extracted here)
            **traverse_obj(post, {
                'title': ('title', {str}),
                'thumbnails': ('cover', ({
                    'url': ('desktop', {url_or_none}),
                    'width': ('width', {int_or_none}),
                    'height': ('height', {int_or_none}),
                }, {
                    'url': ('mobile', {url_or_none}),
                })),
                'modified_timestamp': ('published_at', {unified_timestamp}),
                'modified_date': ('published_at', {unified_strdate}),
                'channel': ('author_info', 'name'),
                'channel_id': ('author_info', 'handle'),
                'channel_url': ('author_info', 'handle', {lambda x: f'{self._BASE_URL}/{x}'}),
                'like_count': ('likes_count', {int_or_none}),
                'comment_count': ('comments_count', {int_or_none}),
            }),
        }

        entries = []
        for idx, component in enumerate(
                traverse_obj(post, ('components', lambda _, v: v.get('detail_id') and v['type'] in ('video', 'audio'))),
                start=1):
            media_type = component['type']
            detail_id = component['detail_id']

            component_data = self._call_api(
                f'post/video/{detail_id}?type=url',
                post_id, note=f'Downloading {media_type} playback info')

            playback_url = component_data.get('playback_url')
            if not playback_url:
                continue

            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                playback_url, post_id, 'mp4', m3u8_id=f'hls-{media_type}')

            if not formats:
                continue

            entries.append({
                'id': f'{post_id}-{idx}-{detail_id}',
                'formats': formats,
                'subtitles': subtitles,
                'description': description,
                **common_metadata,
                **traverse_obj(component, {
                    'duration': ('length', {int_or_none}),
                    'thumbnails': ('cover', ({
                        'url': ('desktop', {url_or_none}),
                        'width': ('width', {int_or_none}),
                        'height': ('height', {int_or_none}),
                    }, {
                        'url': ('mobile', {url_or_none}),
                    })),
                }),
            })

        if not entries:
            self.raise_no_formats('The post does not have any audio or video', expected=True, video_id=post_id)

        if len(entries) == 1:
            return {**entries[0], 'id': post_id}

        return self.playlist_result(entries, post_id, **common_metadata)


class ForendorsIE(ForendorsBaseIE):
    _VALID_URL = r'https?://(?:www\.)?forendors\.cz/p/(?P<id>[\da-f]+)'
    _TESTS = [{
        'url': 'https://www.forendors.cz/p/733045644230530172',
        'info_dict': {
            'id': '733045644230530172',
            'title': 'Představujeme vám nový editor příspěvků!',
            'channel': 'Forendors',
            'channel_id': 'forendors',
            'channel_url': 'https://www.forendors.cz/forendors',
            'comment_count': int,
            'like_count': int,
            'modified_timestamp': int,
            'modified_date': str,
        },
        'playlist_count': 2,
        'playlist': [{
            'info_dict': {
                'id': '733045644230530172-1-18084',
                'ext': 'mp4',
                'title': 'Představujeme vám nový editor příspěvků!',
                'description': 'md5:1acbacd98f526d4599a30c073bb3d595',
                'thumbnail': r're:https://.*\.jpg',
                'channel': 'Forendors',
                'channel_id': 'forendors',
                'channel_url': 'https://www.forendors.cz/forendors',
                'duration': 61,
                'comment_count': int,
                'like_count': int,
                'modified_timestamp': int,
                'modified_date': str,
            },
        }, {
            # Note: audio component has no cover/thumbnail in API response
            'info_dict': {
                'id': '733045644230530172-2-18085',
                'ext': 'mp4',
                'title': 'Představujeme vám nový editor příspěvků!',
                'description': 'md5:1acbacd98f526d4599a30c073bb3d595',
                'channel': 'Forendors',
                'channel_id': 'forendors',
                'channel_url': 'https://www.forendors.cz/forendors',
                'duration': 13,
                'comment_count': int,
                'like_count': int,
                'modified_timestamp': int,
                'modified_date': str,
            },
        }],
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
        'url': 'https://www.forendors.cz/p/b76594c2ec7d23f47d61df1fe5526ec4',
        'only_matching': True,
    }, {
        'url': 'https://www.forendors.cz/p/0e111e7be34de04a8b2cfdd254eecfb9',
        'info_dict': {
            'id': '0e111e7be34de04a8b2cfdd254eecfb9',
        },
        'skip': 'The post does not have any audio or video',
    }]

    def _real_extract(self, url):
        post_id = self._match_id(url)

        post = self._call_api(
            f'v2/detail/post/{post_id}',
            post_id, note='Downloading post metadata')

        return self._extract_post(post_id, post)


class ForendorsChannelIE(ForendorsBaseIE):
    IE_NAME = 'forendors:channel'
    _VALID_URL = r'https?://(?:www\.)?forendors\.cz/(?!p/)(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.forendors.cz/forendors',
        'info_dict': {
            'id': 'forendors',
        },
        'playlist_mincount': 1,
        'playlist': [{
            'info_dict': {
                'id': '733045644230530172',
                'ext': 'mp4',
                'title': 'Představujeme vám nový editor příspěvků!',
                'thumbnail': r're:https://.*\.jpg',
            },
        }],
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

    def _fetch_page(self, slug, first_page_data, page_num):
        # Reuse first page data if available to avoid duplicate API call
        if page_num == 0 and first_page_data:
            page_data = first_page_data
        else:
            page_data = self._call_api(
                f'v2/detail/user/{slug}/posts',
                slug, note=f'Downloading page {page_num + 1}',
                query={'page': page_num + 1})

        for post in page_data.get('data', []):
            post_id = post.get('hash')
            if not post_id:
                continue

            # Yield url_result for each post to preserve page size for InAdvancePagedList
            # Individual post extraction will handle non-media posts and failures
            yield self.url_result(
                f'{self._BASE_URL}/p/{post_id}',
                ForendorsIE, post_id,
                post.get('title'))

    def _real_extract(self, url):
        slug = self._match_id(url)

        first_page = self._call_api(
            f'v2/detail/user/{slug}/posts',
            slug, note='Downloading page 1',
            query={'page': 1})

        page_count = first_page.get('last_page', 1)
        per_page = first_page.get('per_page', 10)

        # Return channel with InAdvancePagedList for proper playlist parameter handling
        return self.playlist_result(
            InAdvancePagedList(
                functools.partial(self._fetch_page, slug, first_page),
                page_count, per_page),
            playlist_id=slug)
