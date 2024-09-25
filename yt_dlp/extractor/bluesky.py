from .common import InfoExtractor
from ..utils import int_or_none, mimetype2ext, parse_iso8601, traverse_obj, url_or_none


class BlueskyIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?bsky\.app/profile/(?P<handle>[^/]+)/post/(?P<id>[0-9a-zA-Z]+)'
    _TESTS = [{
        'url': 'https://bsky.app/profile/blu3blue.bsky.social/post/3l4omssdl632g',
        'md5': '375539c1930ab05d15585ed772ab54fd',
        'info_dict': {
            'id': '3l4omssdl632g',
            'ext': 'mp4',
            'title': 'Blu3Blu3Lilith: "OMG WE HAVE VIDEOS NOW"',
            'upload_date': '20240921',
            'description': 'OMG WE HAVE VIDEOS NOW',
            'thumbnail': r're:^https://video.bsky.app/watch/.*\.jpg$',
            'alt-title': None,
            'uploader': 'Blu3Blu3Lilith',
            'channel': 'blu3blue.bsky.social',
            'uploader_id': 'did:plc:pzdr5ylumf7vmvwasrpr5bf2',
            'channel_id': 'did:plc:pzdr5ylumf7vmvwasrpr5bf2',
            'uploader_url': 'https://bsky.app/profile/blu3blue.bsky.social',
            'channel_url': 'https://bsky.app/profile/blu3blue.bsky.social',
            'timestamp': 1726940605,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'webpage_url': 'https://bsky.app/profile/blu3blue.bsky.social/post/3l4omssdl632g',
            'tags': 'count:1',
            'subtitles': dict,
            'comments': list,
        },
    }, {
        'url': 'https://bsky.app/profile/bsky.app/post/3l3vgf77uco2g',
        'md5': 'b9e344fdbce9f2852c668a97efefb105',
        'info_dict': {
            'id': '3l3vgf77uco2g',
            'ext': 'mp4',
            'title': r're:^Bluesky: "Bluesky now has video!',
            'upload_date': '20240911',
            'description': r're:^Bluesky now has video!',
            'thumbnail': r're:^https://video.bsky.app/watch/.*\.jpg$',
            'alt-title': 'Bluesky video feature announcement',
            'uploader': 'Bluesky',
            'channel': 'bsky.app',
            'uploader_id': 'did:plc:z72i7hdynmk6r22z27h6tvur',
            'channel_id': 'did:plc:z72i7hdynmk6r22z27h6tvur',
            'uploader_url': 'https://bsky.app/profile/bsky.app',
            'channel_url': 'https://bsky.app/profile/bsky.app',
            'timestamp': 1726074716,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'webpage_url': 'https://bsky.app/profile/bsky.app/post/3l3vgf77uco2g',
            'tags': 'count:2',
            'subtitles': dict,
            'comments': list,
        },
    }, {
        'url': 'https://bsky.app/profile/did:plc:3tndo2mqg2vgpxnpyrxiol6p/post/3l45kdlktfe2o',
        'md5': 'a426d7b0fc52bc89fc8f59668be3496e',
        'info_dict': {
            'id': '3l45kdlktfe2o',
            'ext': 'mp4',
            'title': r're:^clockwork banana: "alright.',
            'upload_date': '20240914',
            'description': r're:^alright.\nthis was .. a tiny bit of a pain.',
            'thumbnail': r're:^https://video.bsky.app/watch/.*\.jpg$',
            'alt-title': r're:^me making a goofy little test video',
            'uploader': 'clockwork banana',
            'channel': 'clockworkbanana.fun',
            'uploader_id': 'did:plc:3tndo2mqg2vgpxnpyrxiol6p',
            'channel_id': 'did:plc:3tndo2mqg2vgpxnpyrxiol6p',
            'uploader_url': 'https://bsky.app/profile/clockworkbanana.fun',
            'channel_url': 'https://bsky.app/profile/clockworkbanana.fun',
            'timestamp': 1726353835,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'webpage_url': 'https://bsky.app/profile/did:plc:3tndo2mqg2vgpxnpyrxiol6p/post/3l45kdlktfe2o',
            'tags': 'count:1',
            'subtitles': dict,
            'comments': list,
        },
    }, {
        'url': 'https://bsky.app/profile/souris.moe/post/3l4qhp7bcs52c',
        'md5': '5f2df8c200b5633eb7fb2c984d29772f',
        'info_dict': {
            'id': '3l4qhp7bcs52c',
            'ext': 'mp4',
            'title': 'maeve: ""',
            'upload_date': '20240922',
            'description': '',
            'thumbnail': r're:^https://video.bsky.app/watch/.*\.jpg$',
            'alt-title': None,
            'uploader': 'maeve',
            'channel': 'souris.moe',
            'uploader_id': 'did:plc:tj7g244gl5v6ai6cm4f4wlqp',
            'channel_id': 'did:plc:tj7g244gl5v6ai6cm4f4wlqp',
            'uploader_url': 'https://bsky.app/profile/souris.moe',
            'channel_url': 'https://bsky.app/profile/souris.moe',
            'timestamp': 1727003838,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'webpage_url': 'https://bsky.app/profile/souris.moe/post/3l4qhp7bcs52c',
            'tags': 'count:1',
            'subtitles': 'count:0',
            'comments': list,
        },
    }]

    def _get_comments(self, meta):
        yield self.traverse_replies(
            meta.get('thread'),
            (traverse_obj(meta, ('thread', 'post', 'record', 'reply', 'root', 'uri'))
             or traverse_obj(meta, ('thread', 'post', 'uri'))))

    def traverse_replies(self, thread_node, root_uri):
        parent_uri = traverse_obj(thread_node, ('post', 'record', 'reply', 'parent', 'uri'))
        parent_id = 'root' if parent_uri == root_uri else parent_uri
        author_handle = traverse_obj(thread_node, ('post', 'author', 'handle'))
        author_did = traverse_obj(thread_node, ('post', 'author', 'did'))
        yield {
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
        }
        if replies := thread_node.get('replies'):
            for reply in replies:
                yield from self.traverse_replies(reply, root_uri)
        if parent := thread_node.get('parent'):
            yield from self.traverse_replies(parent, root_uri)

    def _real_extract(self, url):
        handle, video_id = self._match_valid_url(url).groups()
        did = handle if handle.startswith('did:') else self._download_json(
            (f'https://bsky.social/xrpc/com.atproto.identity.resolveHandle?handle={handle}'),
            video_id, expected_status=200).get('did')

        getcomments = self.get_param('getcomments', False)
        meta = self._download_json(
            'https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread',
            video_id, headers={'Content-Type': 'application/json'},
            query={'uri': f'at://{did}/app.bsky.feed.post/{video_id}',
                   'depth': 1000 if getcomments else 0,
                   'parentHeight': 1000 if getcomments else 0},
            expected_status=200)

        formats, subs = self._extract_m3u8_formats_and_subtitles(
            traverse_obj(meta, ('thread', 'post', 'embed', 'playlist')),
            video_id, 'mp4', 'm3u8_native', m3u8_id='hls', fatal=False,
            note='Downloading HD m3u8 information', errnote='Unable to download HD m3u8 information')
        blob_cid = (traverse_obj(meta, ('thread', 'post', 'embed', 'cid'))
                    or traverse_obj(meta, ('thread', 'post', 'record', 'embed', 'video', 'ref', '$link')))
        formats.append({
            'format_id': 'blob',
            'url': f'https://bsky.social/xrpc/com.atproto.sync.getBlob?did={did}&cid={blob_cid}',
            'ext': mimetype2ext(traverse_obj(meta, ('thread', 'post', 'record', 'embed', 'video', 'mimeType')), 'mp4'),
            'width': traverse_obj(meta, ('thread', 'post', 'record', 'embed', 'aspectRatio', 'width'), expected_type=int_or_none),
            'height': traverse_obj(meta, ('thread', 'post', 'record', 'embed', 'aspectRatio', 'height'), expected_type=int_or_none),
            'filesize': traverse_obj(meta, ('thread', 'post', 'record', 'embed', 'video', 'size'), expected_type=int_or_none),
        })

        handle = traverse_obj(meta, ('thread', 'post', 'author', 'handle'))
        uploader = traverse_obj(meta, ('thread', 'post', 'author', 'displayName'))
        description = traverse_obj(meta, ('thread', 'post', 'record', 'text'))
        extractor = self.extract_comments(meta)

        return {
            'id': video_id,
            'title': f'{uploader}: "{description}"',
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
            'comments': [] if not extractor else [*(extractor().get('comments'))[0]][1:],
            'subtitles': self._merge_subtitles(subs),
        }
