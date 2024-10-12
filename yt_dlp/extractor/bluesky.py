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
            'thumbnail': r're:https://video.bsky.app/watch/.*\.jpg$',
            'alt_title': None,
            'uploader': 'Blu3Blu3Lilith',
            'channel': 'blu3blue.bsky.social',
            'uploader_id': 'did:plc:pzdr5ylumf7vmvwasrpr5bf2',
            'channel_id': 'did:plc:pzdr5ylumf7vmvwasrpr5bf2',
            'uploader_url': 'https://bsky.app/profile/blu3blue.bsky.social',
            'channel_url': 'https://bsky.app/profile/did:plc:pzdr5ylumf7vmvwasrpr5bf2',
            'timestamp': 1726940605,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'webpage_url': 'https://bsky.app/profile/blu3blue.bsky.social/post/3l4omssdl632g',
            'tags': 'count:1',
            'subtitles': dict,
            'comments': None,  # 'count:29' if getcomments
        },
    }, {
        'url': 'https://bsky.app/profile/bsky.app/post/3l3vgf77uco2g',
        'md5': 'b9e344fdbce9f2852c668a97efefb105',
        'info_dict': {
            'id': '3l3vgf77uco2g',
            'ext': 'mp4',
            'title': r're:Bluesky: "Bluesky now has video!',
            'upload_date': '20240911',
            'description': r're:Bluesky now has video!',
            'thumbnail': r're:https://video.bsky.app/watch/.*\.jpg$',
            'alt_title': 'Bluesky video feature announcement',
            'uploader': 'Bluesky',
            'channel': 'bsky.app',
            'uploader_id': 'did:plc:z72i7hdynmk6r22z27h6tvur',
            'channel_id': 'did:plc:z72i7hdynmk6r22z27h6tvur',
            'uploader_url': 'https://bsky.app/profile/bsky.app',
            'channel_url': 'https://bsky.app/profile/did:plc:z72i7hdynmk6r22z27h6tvur',
            'timestamp': 1726074716,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'webpage_url': 'https://bsky.app/profile/bsky.app/post/3l3vgf77uco2g',
            'tags': 'count:2',
            'subtitles': dict,
            'comments': None,
        },
    }, {
        'url': 'https://bsky.app/profile/did:plc:3tndo2mqg2vgpxnpyrxiol6p/post/3l45kdlktfe2o',
        'md5': 'a426d7b0fc52bc89fc8f59668be3496e',
        'info_dict': {
            'id': '3l45kdlktfe2o',
            'ext': 'mp4',
            'title': r're:clockwork boo-nana 👻: "alright.',
            'upload_date': '20240914',
            'description': r're:alright.\nthis was .. a tiny bit of a pain.',
            'thumbnail': r're:https://video.bsky.app/watch/.*\.jpg$',
            'alt_title': r're:me making a goofy little test video',
            'uploader': 'clockwork boo-nana 👻',
            'channel': 'clockworkbanana.fun',
            'uploader_id': 'did:plc:3tndo2mqg2vgpxnpyrxiol6p',
            'channel_id': 'did:plc:3tndo2mqg2vgpxnpyrxiol6p',
            'uploader_url': 'https://bsky.app/profile/clockworkbanana.fun',
            'channel_url': 'https://bsky.app/profile/did:plc:3tndo2mqg2vgpxnpyrxiol6p',
            'timestamp': 1726353835,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'webpage_url': 'https://bsky.app/profile/did:plc:3tndo2mqg2vgpxnpyrxiol6p/post/3l45kdlktfe2o',
            'tags': 'count:1',
            'subtitles': dict,
            'comments': None,
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
            'thumbnail': r're:https://video.bsky.app/watch/.*\.jpg$',
            'alt_title': None,
            'uploader': 'maeve',
            'channel': 'souris.moe',
            'uploader_id': 'did:plc:tj7g244gl5v6ai6cm4f4wlqp',
            'channel_id': 'did:plc:tj7g244gl5v6ai6cm4f4wlqp',
            'uploader_url': 'https://bsky.app/profile/souris.moe',
            'channel_url': 'https://bsky.app/profile/did:plc:tj7g244gl5v6ai6cm4f4wlqp',
            'timestamp': 1727003838,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'webpage_url': 'https://bsky.app/profile/souris.moe/post/3l4qhp7bcs52c',
            'tags': 'count:1',
            'subtitles': 'count:0',
            'comments': None,
        },
    }, {
        'url': 'https://bsky.app/profile/de1.pds.tentacle.expert/post/3l3w4tnezek2e',
        'md5': '1af9c7fda061cf7593bbffca89e43d1c',
        'info_dict': {
            'id': '3l3w4tnezek2e',
            'ext': 'mp4',
            'title': 'clean: ""',
            'upload_date': '20240911',
            'description': '',
            'thumbnail': r're:https://video.bsky.app/watch/.*\.jpg$',
            'alt_title': None,
            'uploader': 'clean',
            'channel': 'de1.pds.tentacle.expert',
            'uploader_id': 'did:web:de1.tentacle.expert',
            'channel_id': 'did:web:de1.tentacle.expert',
            'uploader_url': 'https://bsky.app/profile/de1.pds.tentacle.expert',
            'channel_url': 'https://bsky.app/profile/did:web:de1.tentacle.expert',
            'timestamp': 1726098823,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'webpage_url': 'https://bsky.app/profile/de1.pds.tentacle.expert/post/3l3w4tnezek2e',
            'tags': 'count:1',
            'subtitles': 'count:0',
            'comments': None,
        },
    }]

    def _get_comments(self, meta):
        yield from self.traverse_replies(meta, traverse_obj(meta, ('post', 'uri'), default=''))

    def traverse_replies(self, thread_node, root_uri):
        post_uri = traverse_obj(thread_node, ('post', 'uri'))
        if post_uri != root_uri:
            post = thread_node.get('post')
            parent_uri = traverse_obj(post, ('record', 'reply', 'parent', 'uri'))
            author_handle = traverse_obj(post, ('author', 'handle'))
            author_did = traverse_obj(post, ('author', 'did'), default='')
            yield {
                'id': post_uri,
                'text': traverse_obj(post, ('record', 'text')),
                'timestamp': parse_iso8601(traverse_obj(post, ('record', 'createdAt'))),
                'parent': 'root' if parent_uri == root_uri else parent_uri,
                'like_count': post.get('likeCount'),
                'author': traverse_obj(post, ('author', 'displayName')),
                'author_id': author_did,
                'author_thumbnail': traverse_obj(post, ('author', 'avatar'), expected_type=url_or_none),
                'author_url': f'https://bsky.app/profile/{author_handle}',
                'author_is_uploader': author_did in root_uri,
            }
        if replies := thread_node.get('replies'):
            for reply in replies:
                yield from self.traverse_replies(reply, root_uri)
        if parent := thread_node.get('parent'):
            yield from self.traverse_replies(parent, root_uri)

    def _real_extract(self, url):
        handle, video_id = self._match_valid_url(url).groups()
        did = handle if handle.startswith('did:') else self._download_json(
            'https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle',
            video_id, query={'handle': handle}).get('did')

        getcomments = self.get_param('getcomments', False)
        meta = self._download_json(
            'https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread',
            video_id, headers={'Content-Type': 'application/json'}, query={
                'uri': f'at://{did}/app.bsky.feed.post/{video_id}',
                'depth': 1000 if getcomments else 0,
                'parentHeight': 1000 if getcomments else 0,
            }).get('thread')
        post, record_embed = meta.get('post'), traverse_obj(meta, ('post', 'record', 'embed'))

        formats, subs = self._extract_m3u8_formats_and_subtitles(
            traverse_obj(post, ('embed', 'playlist')),
            video_id, 'mp4', 'm3u8_native', m3u8_id='hls', fatal=False,
            note='Downloading HD m3u8 information', errnote='Unable to download HD m3u8 information')
        blob_cid = traverse_obj(post, ('embed', 'cid'), ('record', 'embed', 'video', 'ref', '$link'))
        formats.append({
            'format_id': 'blob',
            'url': f'https://bsky.social/xrpc/com.atproto.sync.getBlob?did={did}&cid={blob_cid}',
            'ext': mimetype2ext(traverse_obj(record_embed, ('video', 'mimeType')), 'mp4'),
            'width': traverse_obj(record_embed, ('aspectRatio', 'width'), expected_type=int_or_none),
            'height': traverse_obj(record_embed, ('aspectRatio', 'height'), expected_type=int_or_none),
            'filesize': traverse_obj(record_embed, ('video', 'size'), expected_type=int_or_none),
        })

        handle = traverse_obj(post, ('author', 'handle'))
        uploader = traverse_obj(post, ('author', 'displayName'))
        description = traverse_obj(post, ('record', 'text'))

        return {
            'id': video_id,
            'title': f'{uploader}: "{description}"',
            'formats': formats,
            'description': description,
            'thumbnail': traverse_obj(post, ('embed', 'thumbnail'), expected_type=url_or_none),
            'alt_title': traverse_obj(post, ('embed', 'alt'), ('record', 'embed', 'alt')),
            'uploader': uploader,
            'channel': handle,
            'uploader_id': did,
            'channel_id': did,
            'uploader_url': f'https://bsky.app/profile/{handle}',
            'channel_url': f'https://bsky.app/profile/{did}',
            'timestamp': parse_iso8601(traverse_obj(post, ('record', 'createdAt'))),
            'like_count': post.get('likeCount'),
            'repost_count': post.get('repostCount'),
            'comment_count': post.get('replyCount'),
            'tags': post.get('labels', []) + traverse_obj(post, ('record', 'langs'), default=[]),
            '__post_extractor': self.extract_comments(meta),
            'subtitles': subs,
        }
