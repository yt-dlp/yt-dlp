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
            'title': str,
            'upload_date': '20240921',
            'description': 'OMG WE HAVE VIDEOS NOW',
            'thumbnail': r're:https://video.bsky.app/watch/.*\.jpg$',
            'uploader': str,
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
            'comments': 'mincount:29',
        },
        'params': {'getcomments': True},
    }, {
        'url': 'https://bsky.app/profile/bsky.app/post/3l3vgf77uco2g',
        'md5': 'b9e344fdbce9f2852c668a97efefb105',
        'info_dict': {
            'id': '3l3vgf77uco2g',
            'ext': 'mp4',
            'title': str,
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
            'subtitles': {
                'en': 'mincount:1',
            },
        },
    }, {
        'url': 'https://bsky.app/profile/souris.moe/post/3l4qhp7bcs52c',
        'md5': '5f2df8c200b5633eb7fb2c984d29772f',
        'info_dict': {
            'id': '3l4qhp7bcs52c',
            'ext': 'mp4',
            'title': str,
            'upload_date': '20240922',
            'description': '',
            'thumbnail': r're:https://video.bsky.app/watch/.*\.jpg$',
            'uploader': str,
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
        },
    }, {
        'url': 'https://bsky.app/profile/de1.pds.tentacle.expert/post/3l3w4tnezek2e',
        'md5': '1af9c7fda061cf7593bbffca89e43d1c',
        'info_dict': {
            'id': '3l3w4tnezek2e',
            'ext': 'mp4',
            'title': str,
            'upload_date': '20240911',
            'description': '',
            'thumbnail': r're:https://video.bsky.app/watch/.*\.jpg$',
            'uploader': str,
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
        },
    }, {
        'url': 'https://bsky.app/profile/yunayuispink.bsky.social/post/3l7gqcfes742o',
        'md5': 'd4dfae6a3e6e31b130e728b5b84258c4',
        'info_dict': {
            'id': 'XxK3t_5V3ao',
            'ext': 'webm',
            'uploader_id': '@yunayuispink',
            'live_status': 'not_live',
            'view_count': int,
            'channel_url': 'https://www.youtube.com/channel/UCPLvXnHa7lTyNoR_dGsU14w',
            'thumbnail': 'https://i.ytimg.com/vi_webp/XxK3t_5V3ao/maxresdefault.webp',
            'upload_date': '20241026',
            'uploader_url': 'https://www.youtube.com/@yunayuispink',
            'description': 'md5:7d474e6ab76a88c84eb0f294e18ed828',
            'categories': ['Entertainment'],
            'tags': [],
            'title': '5min vs 5hours drawing',
            'duration': 321,
            'uploader': 'yunayu',
            'channel_follower_count': int,
            'channel': 'yunayu',
            'playable_in_embed': True,
            'timestamp': 1729967784,
            'like_count': int,
            'channel_id': 'UCPLvXnHa7lTyNoR_dGsU14w',
            'availability': 'public',
            'age_limit': 0,
            'comment_count': int,
        },
        'add_ie': ['Youtube'],
    }, {
        'url': 'https://bsky.app/profile/endshark.bsky.social/post/3jzxjkcemae2m',
        'md5': 'd5c8fbc8f72b9f6ef160c150c420bb55',
        'info_dict': {
            'id': '222792849',
            'ext': 'mp3',
            'track': 'Forward to the End',
            'thumbnail': 'https://f4.bcbits.com/img/a2507705510_5.jpg',
            'album': 'Hari Nezumi [EP]',
            'uploader_id': 'laserbatx',
            'uploader': 'LASERBAT',
            'duration': 228.571,
            'album_artists': ['LASERBAT'],
            'timestamp': 1682276040.0,
            'uploader_url': 'https://laserbatx.bandcamp.com',
            'track_id': '222792849',
            'release_date': '20230423',
            'upload_date': '20230423',
            'release_timestamp': 1682276040.0,
            'track_number': 1,
            'artists': ['LASERBAT'],
            'title': 'LASERBAT - Forward to the End',
        },
        'add_ie': ['Bandcamp'],
    }, {
        'url': 'https://bsky.app/profile/dannybhoix.bsky.social/post/3l6oe5mtr2c2j',
        'md5': 'b9e344fdbce9f2852c668a97efefb105',
        'info_dict': {
            'id': '3l6oe5mtr2c2j',
            'ext': 'mp4',
            'description': 'this looks like a 2012 announcement video. i love it.',
            'uploader_url': 'https://bsky.app/profile/dannybhoix.bsky.social',
            'uploader': 'Danny',
            'title': str,
            'repost_count': int,
            'comment_count': int,
            'channel': 'dannybhoix.bsky.social',
            'timestamp': 1729130330,
            'uploader_id': 'did:plc:ng7fhshaed7assvhkq7cxxnw',
            'upload_date': '20241017',
            'channel_url': 'https://bsky.app/profile/did:plc:ng7fhshaed7assvhkq7cxxnw',
            'tags': ['en'],
            'like_count': int,
            'channel_id': 'did:plc:ng7fhshaed7assvhkq7cxxnw',
            'thumbnail': r're:https://video.bsky.app/watch/.*\.jpg$',
            'alt_title': 'Bluesky video feature announcement',
            'subtitles': {
                'en': 'mincount:1',
            },
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
                **traverse_obj(post, {
                    'text': ('record', 'text'),
                    'timestamp': ('record', 'createdAt', {parse_iso8601}),
                    'author': ('author', 'displayName'),
                    'author_thumbnail': ('author', 'avatar', {url_or_none}),
                }),
                'parent': 'root' if parent_uri == root_uri else parent_uri,
                'like_count': post.get('likeCount'),
                'author_id': author_did,
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

        getcomments = self.get_param('getcomments', False)
        meta = self._download_json(
            'https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread',
            video_id, headers={'Content-Type': 'application/json'}, query={
                'uri': f'at://{handle}/app.bsky.feed.post/{video_id}',
                'depth': 1000 if getcomments else 0,
                'parentHeight': 1000 if getcomments else 0,
            })['thread']
        post = meta.get('post')

        did = traverse_obj(post, ('author', 'did'))
        record_embed = traverse_obj(post, ('record', 'embed', ('media', None)), get_all=False)
        post_type = record_embed.get('$type') if record_embed else None
        quoted_post = traverse_obj(post, ('embed', 'record', ('record', None)), get_all=False)
        quoted_type = traverse_obj(quoted_post, ('value', 'embed', ('media', None), '$type'), get_all=False)
        quoted_media = traverse_obj(quoted_post, ('embeds', 0, ('media', None)), get_all=False)

        if post_type == 'app.bsky.embed.external':
            return self.url_result(traverse_obj(
                post, ('embed', ('media', None), 'external', 'uri'), get_all=False)
                or traverse_obj(record_embed, ('external', 'uri')))
        elif post_type == 'app.bsky.embed.video':
            formats, subs = self._extract_m3u8_formats_and_subtitles(
                traverse_obj(post, ('embed', ('media', None), 'playlist'), get_all=False),
                video_id, 'mp4', 'm3u8_native', m3u8_id='hls', fatal=False,
                note='Downloading m3u8 information', errnote='Unable to download m3u8 information')
            if blob_cid := traverse_obj(record_embed, ('video', 'ref', '$link'), ('video', 'cid')):
                formats.append({
                    'format_id': 'blob',
                    'url': f'https://bsky.social/xrpc/com.atproto.sync.getBlob?did={did}&cid={blob_cid}',
                    **traverse_obj(record_embed, {
                        'ext': ('video', 'mimeType', {mimetype2ext}),
                        'width': ('aspectRatio', 'width', {int_or_none}),
                        'height': ('aspectRatio', 'height', {int_or_none}),
                        'filesize': ('video', 'size', {int_or_none}),
                    }),
                })
            video_info = {
                'formats': formats,
                'subtitles': subs,
                **traverse_obj(post, {
                    'thumbnail': ('embed', 'thumbnail', {url_or_none}),
                    'alt_title': ('embed', 'alt'),
                }),
            }
        elif quoted_type == 'app.bsky.embed.external':
            return self.url_result(traverse_obj(quoted_media, ('external', 'uri')))
        elif quoted_type == 'app.bsky.embed.video':
            formats, subs = self._extract_m3u8_formats_and_subtitles(
                quoted_media.get('playlist'), video_id, 'mp4', 'm3u8_native', m3u8_id='hls', fatal=False,
                note='Downloading m3u8 information', errnote='Unable to download m3u8 information')
            if blob_cid := quoted_media.get('cid'):
                quoted_did = traverse_obj(quoted_post, ('author', 'did'))
                quoted_embed = traverse_obj(quoted_post, ('value', 'embed', ('media', None)), get_all=False)
                formats.append({
                    'format_id': 'blob',
                    'url': f'https://bsky.social/xrpc/com.atproto.sync.getBlob?did={quoted_did}&cid={blob_cid}',
                    **traverse_obj(quoted_embed, {
                        'ext': ('video', 'mimeType', {mimetype2ext}),
                        'width': ('aspectRatio', 'width', {int_or_none}),
                        'height': ('aspectRatio', 'height', {int_or_none}),
                        'filesize': ('video', 'size', {int_or_none}),
                    }),
                })
            video_info = {
                'formats': formats,
                'subtitles': subs,
                'thumbnail': url_or_none(quoted_media.get('thumbnail')),
                'alt_title': quoted_embed.get('alt') or quoted_media.get('alt'),
            }
        else:
            self.raise_no_formats('No video could be found in this post', expected=True)

        handle = traverse_obj(post, ('author', 'handle'))
        uploader = traverse_obj(post, ('author', 'displayName')) or handle

        return {
            'id': video_id,
            'title': f'{uploader} on Bluesky',
            **video_info,
            'uploader': uploader,
            'channel': handle,
            'uploader_id': did,
            'channel_id': did,
            'uploader_url': f'https://bsky.app/profile/{handle}',
            'channel_url': f'https://bsky.app/profile/{did}',
            'like_count': post.get('likeCount'),
            'repost_count': post.get('repostCount'),
            'comment_count': post.get('replyCount'),
            'tags': post.get('labels', []) + traverse_obj(post, ('record', 'langs'), default=[]),
            '__post_extractor': self.extract_comments(meta),
            **traverse_obj(post, {
                'timestamp': ('record', 'createdAt', {parse_iso8601}),
                'description': ('record', 'text'),
            }),
        }
