from .common import InfoExtractor
from ..utils import parse_iso8601, traverse_obj, url_or_none


class BlueskyIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?bsky\.app/profile/(?P<handle>[^/]+)/post/(?P<id>[0-9a-zA-Z]+)'
    _TESTS = [{
        'url': 'https://bsky.app/profile/blu3blue.bsky.social/post/3l4omssdl632g',
        'md5': '067838923631f1ab63b3148b808920cc',
        'info_dict': {
            'id': '3l4omssdl632g',
            'ext': 'mp4',
            'title': str,
            'upload_date': str,
            'description': str,
            'thumbnail': r're:^https?://.*\.jpg$',
            'alt-title': None,
            'uploader': str,
            'channel': str,
            'uploader_id': str,
            'channel_id': str,
            'uploader_url': r're:^https?://.*',
            'channel_url': r're:^https?://.*',
            'timestamp': int,
            'like_count': int,
            'repost_count': 0,
            'comment_count': int,
            'webpage_url': r're:^https?://.*',
            'tags': 'count:1',
            'subtitles': dict,
            'comments': list,
        },
    }, {
        'url': 'https://bsky.app/profile/bsky.app/post/3l3wdzzedvv2y',
        'md5': '66b0881d1f7798a5d6c4df428ef9e0fa',
        'info_dict': {
            'id': '3l3wdzzedvv2y',
            'ext': 'mp4',
            'title': str,
            'upload_date': str,
            'description': str,
            'thumbnail': r're:^https?://.*\.jpg$',
            'alt-title': str,
            'uploader': str,
            'channel': str,
            'uploader_id': str,
            'channel_id': str,
            'uploader_url': r're:^https?://.*',
            'channel_url': r're:^https?://.*',
            'timestamp': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'webpage_url': r're:^https?://.*',
            'tags': 'count:2',
            'subtitles': dict,
            'comments': list,
        },
    }, {
        'url': 'https://bsky.app/profile/bsky.app/post/3l3vgf77uco2g',
        'md5': '0246a55553a2aac33745bd409ddba653',
        'info_dict': {
            'id': '3l3vgf77uco2g',
            'ext': 'mp4',
            'title': str,
            'upload_date': str,
            'description': str,
            'thumbnail': r're:^https?://.*\.jpg$',
            'alt-title': str,
            'uploader': str,
            'channel': str,
            'uploader_id': str,
            'channel_id': str,
            'uploader_url': r're:^https?://.*',
            'channel_url': r're:^https?://.*',
            'timestamp': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'webpage_url': r're:^https?://.*',
            'tags': 'count:2',
            'subtitles': dict,
            'comments': list,
        },
    }, {
        'url': 'https://bsky.app/profile/souris.moe/post/3l4qhp7bcs52c',
        'md5': 'bf2c5ab58f67993dc06c7a29cbc447cd',
        'info_dict': {
            'id': '3l4qhp7bcs52c',
            'ext': 'mp4',
            'title': str,
            'upload_date': str,
            'description': str,
            'thumbnail': r're:^https?://.*\.jpg$',
            'alt-title': None,
            'uploader': str,
            'channel': str,
            'uploader_id': str,
            'channel_id': str,
            'uploader_url': r're:^https?://.*',
            'channel_url': r're:^https?://.*',
            'timestamp': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'webpage_url': r're:^https?://.*',
            'tags': list,
            'subtitles': dict,
            'comments': list,
        },
    }]

    def traverse_replies(self, thread_node, root_uri):
        parent_uri = traverse_obj(thread_node, ('post', 'record', 'reply', 'parent', 'uri'))
        parent_id = 'root' if parent_uri == root_uri else parent_uri
        author_handle = traverse_obj(thread_node, ('post', 'author', 'handle'))
        author_did = traverse_obj(thread_node, ('post', 'author', 'did'))

        formatted_comments = [{
            'id': traverse_obj(thread_node, ('post', 'uri')),
            'text': traverse_obj(thread_node, ('post', 'record', 'text')),
            'timestamp': parse_iso8601(traverse_obj(thread_node, ('post', 'record', 'createdAt'))),
            'parent': parent_id,
            'like_count': traverse_obj(thread_node, ('post', 'likeCount')),
            'author': traverse_obj(thread_node, ('post', 'author', 'displayName')),
            'author_id': author_did,
            'author_thumbnail': traverse_obj(thread_node, ('post', 'author', 'avatar'), expected_type=url_or_none),
            'author_url': f'https://bsky.app/profile/{author_handle}',
            'author_is_uploader': 'Yes' if author_did in root_uri else 'No',
        }]

        if replies := thread_node.get('replies'):
            for reply in replies:
                formatted_comments.extend(self.traverse_replies(reply, root_uri))
        return formatted_comments

    def _real_extract(self, url):
        handle, video_id = self._match_valid_url(url).groups()
        did = self._download_json(
            'https://bsky.social/xrpc/com.atproto.identity.resolveHandle',
            video_id, query={'handle': handle}, expected_status=200).get('did')

        meta = self._download_json(
            'https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread',
            video_id, headers={'Content-Type': 'application/json'},
            query={'uri': f'at://{did}/app.bsky.feed.post/{video_id}',
                   'depth': 6 if self.get_param('write_comments') else 0, 'parentHeight': 0},
            expected_status=200)

        formats, subs = self._extract_m3u8_formats_and_subtitles(
            traverse_obj(meta, ('thread', 'post', 'embed', 'playlist')),
            video_id, 'mp4', 'm3u8_native', m3u8_id='hls', fatal=False,
            note='Downloading HD m3u8 information', errnote='Unable to download HD m3u8 information')

        formatted_replies = self.traverse_replies(
            meta.get('thread'), (traverse_obj(meta, ('thread', 'post', 'record', 'reply', 'root', 'uri'))
                                 or traverse_obj(meta, ('thread', 'post', 'uri'))))

        uploader = traverse_obj(meta, ('thread', 'post', 'author', 'displayName'))
        description = traverse_obj(meta, ('thread', 'post', 'record', 'text'))

        return {
            'id': video_id,
            'title': f'{uploader}: {description}',
            'formats': formats,
            'description': description,
            'thumbnail': traverse_obj(meta, ('thread', 'post', 'embed', 'thumbnail'), expected_type=url_or_none),
            'alt-title': traverse_obj(meta, ('thread', 'post', 'record', 'alt'), ('thread', 'post', 'embed', 'alt')),
            'uploader': uploader,
            'channel': handle,
            'uploader_id': did,
            'channel_id': did,
            'uploader_url': f'https://bsky.app/profile/{handle}',
            'channel_url': f'https://bsky.app/profile/{handle}',
            'timestamp': parse_iso8601(traverse_obj(meta, ('thread', 'post', 'record', 'createdAt'))),
            'like_count': traverse_obj(meta, ('thread', 'post', 'likeCount')),
            'repost_count': traverse_obj(meta, ('thread', 'post', 'repostCount')),
            'comment_count': traverse_obj(meta, ('thread', 'post', 'replyCount')),
            'webpage_url': url,
            'tags': (traverse_obj(meta, ('thread', 'post', 'labels'), expected_type=list)
                     + traverse_obj(meta, ('thread', 'post', 'record', 'langs'), expected_type=list)),
            'comments': [] if len(formatted_replies) < 2 else formatted_replies[1:],
            'subtitles': self._merge_subtitles(subs),
        }
