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
            'repost_count': None,
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
            'repost_count': None,
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
            'repost_count': None,
            'comment_count': int,
            'webpage_url': r're:^https?://.*',
            'tags': 'count:2',
            'subtitles': dict,
            'comments': list,
        },
    }]

    def _real_extract(self, url):
        handle, video_id = self._match_valid_url(url).groups()

        resolve_url = 'https://bsky.social/xrpc/com.atproto.identity.resolveHandle'
        did = self._download_json(resolve_url, video_id, query={'handle': handle}, expected_status=200).get('did')

        api_url = 'https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread'
        headers = {'Content-Type': 'application/json'}
        depth = 80 if self.get_param('write_comments') else 0  # getPostThread default
        params = {'uri': f'at://{did}/app.bsky.feed.post/{video_id}', 'depth': depth}
        meta = self._download_json(api_url, video_id, headers=headers, query=params, expected_status=200)

        m3u8_url = traverse_obj(meta, ('thread', 'post', 'embed', 'playlist'))
        formats, subs = self._extract_m3u8_formats_and_subtitles(
            m3u8_url, video_id, 'mp4', 'm3u8_native', m3u8_id='hls', fatal=False,
            note='Downloading HD m3u8 information', errnote='Unable to download HD m3u8 information')
        subtitles = self._merge_subtitles(subs)
        uploader = traverse_obj(meta, ('thread', 'post', 'author', 'displayName'))
        description = traverse_obj(meta, ('thread', 'post', 'record', 'text'))

        formatted_replies = []
        replies = traverse_obj(meta, ('thread', 'replies'), expected_type=list)
        if replies:
            for reply in replies:

                parent_uri = traverse_obj(reply, ('post', 'record', 'reply', 'parent', 'uri'))
                root_uri = traverse_obj(reply, ('post', 'record', 'reply', 'root', 'uri'))
                parent = 'root' if parent_uri == root_uri else parent_uri

                author_handle = traverse_obj(reply, ('post', 'author', 'handle'))
                author_did = traverse_obj(reply, ('post', 'author', 'did'))

                formatted_comment = {
                    'id': traverse_obj(reply, ('post', 'uri')),
                    'text': traverse_obj(reply, ('post', 'record', 'text')),
                    'timestamp': parse_iso8601(traverse_obj(reply, ('post', 'record', 'createdAt'))),
                    'parent': parent,
                    'like_count': traverse_obj(reply, ('post', 'likeCount')),
                    'author': traverse_obj(reply, ('post', 'author', 'displayName')),
                    'author_id': author_did,
                    'author_thumbnail': traverse_obj(reply, ('post', 'author', 'avatar'), expected_type=url_or_none),
                    'author_url': f'https://bsky.app/profile/{author_handle}',
                    'author_is_uploader': 'Yes' if author_did in root_uri else 'No',
                }

                formatted_replies.append(formatted_comment)

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
            'repost_count': traverse_obj(meta, ('thread', 'post', 'respostCount')),
            'comment_count': traverse_obj(meta, ('thread', 'post', 'replyCount')),
            'webpage_url': url,
            'tags': traverse_obj(meta, ('thread', 'post', 'labels'), expected_type=list) + traverse_obj(meta, ('thread', 'post', 'record', 'langs'), expected_type=list),
            'comments': formatted_replies,
            'subtitles': subtitles,
        }
