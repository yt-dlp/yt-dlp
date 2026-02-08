from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    format_field,
    int_or_none,
    mimetype2ext,
    orderedSet,
    parse_iso8601,
    truncate_string,
    update_url_query,
    url_basename,
    url_or_none,
    variadic,
)
from ..utils.traversal import traverse_obj


class BlueskyIE(InfoExtractor):
    _VALID_URL = [
        r'https?://(?:www\.)?(?:bsky\.app|main\.bsky\.dev)/profile/(?P<handle>[\w.:%-]+)/post/(?P<id>\w+)',
        r'at://(?P<handle>[\w.:%-]+)/app\.bsky\.feed\.post/(?P<id>\w+)',
    ]
    _TESTS = [{
        'url': 'https://bsky.app/profile/blu3blue.bsky.social/post/3l4omssdl632g',
        'md5': '375539c1930ab05d15585ed772ab54fd',
        'info_dict': {
            'id': '3l4omssdl632g',
            'ext': 'mp4',
            'uploader': 'Blu3Blu3Lilith',
            'uploader_id': 'blu3blue.bsky.social',
            'uploader_url': 'https://bsky.app/profile/blu3blue.bsky.social',
            'channel_id': 'did:plc:pzdr5ylumf7vmvwasrpr5bf2',
            'channel_url': 'https://bsky.app/profile/did:plc:pzdr5ylumf7vmvwasrpr5bf2',
            'thumbnail': r're:https://video.bsky.app/watch/.*\.jpg$',
            'title': 'OMG WE HAVE VIDEOS NOW',
            'description': 'OMG WE HAVE VIDEOS NOW',
            'upload_date': '20240921',
            'timestamp': 1726940605,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'tags': [],
        },
    }, {
        'url': 'https://bsky.app/profile/bsky.app/post/3l3vgf77uco2g',
        'md5': 'b9e344fdbce9f2852c668a97efefb105',
        'info_dict': {
            'id': '3l3vgf77uco2g',
            'ext': 'mp4',
            'uploader': 'Bluesky',
            'uploader_id': 'bsky.app',
            'uploader_url': 'https://bsky.app/profile/bsky.app',
            'channel_id': 'did:plc:z72i7hdynmk6r22z27h6tvur',
            'channel_url': 'https://bsky.app/profile/did:plc:z72i7hdynmk6r22z27h6tvur',
            'thumbnail': r're:https://video.bsky.app/watch/.*\.jpg$',
            'title': 'Bluesky now has video! Update your app to versi...',
            'alt_title': 'Bluesky video feature announcement',
            'description': r're:(?s)Bluesky now has video! .{239}',
            'upload_date': '20240911',
            'timestamp': 1726074716,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'tags': [],
            'subtitles': {
                'en': 'mincount:1',
            },
        },
    }, {
        'url': 'https://main.bsky.dev/profile/souris.moe/post/3l4qhp7bcs52c',
        'md5': '5f2df8c200b5633eb7fb2c984d29772f',
        'info_dict': {
            'id': '3l4qhp7bcs52c',
            'ext': 'mp4',
            'uploader': 'souris',
            'uploader_id': 'souris.moe',
            'uploader_url': 'https://bsky.app/profile/souris.moe',
            'channel_id': 'did:plc:tj7g244gl5v6ai6cm4f4wlqp',
            'channel_url': 'https://bsky.app/profile/did:plc:tj7g244gl5v6ai6cm4f4wlqp',
            'thumbnail': r're:https://video.bsky.app/watch/.*\.jpg$',
            'title': 'Bluesky video #3l4qhp7bcs52c',
            'upload_date': '20240922',
            'timestamp': 1727003838,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'tags': [],
        },
    }, {
        'url': 'https://bsky.app/profile/de1.pds.tentacle.expert/post/3l3w4tnezek2e',
        'md5': 'cc0110ed1f6b0247caac8234cc1e861d',
        'info_dict': {
            'id': '3l3w4tnezek2e',
            'ext': 'mp4',
            'uploader': 'clean',
            'uploader_id': 'de1.pds.tentacle.expert',
            'uploader_url': 'https://bsky.app/profile/de1.pds.tentacle.expert',
            'channel_id': 'did:web:de1.tentacle.expert',
            'channel_url': 'https://bsky.app/profile/did:web:de1.tentacle.expert',
            'thumbnail': r're:https://video.bsky.app/watch/.*\.jpg$',
            'title': 'Bluesky video #3l3w4tnezek2e',
            'upload_date': '20240911',
            'timestamp': 1726098823,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'tags': [],
        },
    }, {
        'url': 'https://bsky.app/profile/yunayuispink.bsky.social/post/3l7gqcfes742o',
        'info_dict': {
            'id': 'XxK3t_5V3ao',
            'ext': 'mp4',
            'uploader': 'yunayu',
            'uploader_id': '@yunayuispink',
            'uploader_url': 'https://www.youtube.com/@yunayuispink',
            'channel': 'yunayu',
            'channel_id': 'UCPLvXnHa7lTyNoR_dGsU14w',
            'channel_url': 'https://www.youtube.com/channel/UCPLvXnHa7lTyNoR_dGsU14w',
            'thumbnail': 'https://i.ytimg.com/vi_webp/XxK3t_5V3ao/maxresdefault.webp',
            'description': r're:Have a good goodx10000day',
            'title': '5min vs 5hours drawing',
            'availability': 'public',
            'live_status': 'not_live',
            'playable_in_embed': True,
            'upload_date': '20241026',
            'timestamp': 1729967784,
            'duration': 321,
            'age_limit': 0,
            'like_count': int,
            'view_count': int,
            'comment_count': int,
            'channel_follower_count': int,
            'categories': ['Entertainment'],
            'tags': [],
            'chapters': list,
            'heatmap': 'count:100',
        },
        'add_ie': ['Youtube'],
    }, {
        'url': 'https://bsky.app/profile/endshark.bsky.social/post/3jzxjkcemae2m',
        'info_dict': {
            'id': '222792849',
            'ext': 'mp3',
            'uploader': 'LASERBAT',
            'uploader_id': 'laserbatx',
            'uploader_url': 'https://laserbatx.bandcamp.com',
            'artists': ['LASERBAT'],
            'album_artists': ['LASERBAT'],
            'album': 'Hari Nezumi [EP]',
            'track': 'Forward to the End',
            'title': 'LASERBAT - Forward to the End',
            'thumbnail': 'https://f4.bcbits.com/img/a2507705510_5.jpg',
            'duration': 228.571,
            'track_id': '222792849',
            'release_date': '20230423',
            'upload_date': '20230423',
            'timestamp': 1682276040.0,
            'release_timestamp': 1682276040.0,
            'track_number': 1,
        },
        'add_ie': ['Bandcamp'],
    }, {
        'url': 'https://bsky.app/profile/dannybhoix.bsky.social/post/3l6oe5mtr2c2j',
        'md5': 'b9e344fdbce9f2852c668a97efefb105',
        'info_dict': {
            'id': '3l3vgf77uco2g',
            'ext': 'mp4',
            'uploader': 'Bluesky',
            'uploader_id': 'bsky.app',
            'uploader_url': 'https://bsky.app/profile/bsky.app',
            'channel_id': 'did:plc:z72i7hdynmk6r22z27h6tvur',
            'channel_url': 'https://bsky.app/profile/did:plc:z72i7hdynmk6r22z27h6tvur',
            'thumbnail': r're:https://video.bsky.app/watch/.*\.jpg$',
            'title': 'Bluesky now has video! Update your app to versi...',
            'alt_title': 'Bluesky video feature announcement',
            'description': r're:(?s)Bluesky now has video! .{239}',
            'upload_date': '20240911',
            'timestamp': 1726074716,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'tags': [],
            'subtitles': {
                'en': 'mincount:1',
            },
        },
    }, {
        'url': 'https://bsky.app/profile/cinny.bun.how/post/3l7rdfxhyds2f',
        'md5': '8775118b235cf9fa6b5ad30f95cda75c',
        'info_dict': {
            'id': '3l7rdfxhyds2f',
            'ext': 'mp4',
            'uploader': 'cinnamon',
            'uploader_id': 'cinny.bun.how',
            'uploader_url': 'https://bsky.app/profile/cinny.bun.how',
            'channel_id': 'did:plc:7x6rtuenkuvxq3zsvffp2ide',
            'channel_url': 'https://bsky.app/profile/did:plc:7x6rtuenkuvxq3zsvffp2ide',
            'thumbnail': r're:https://video.bsky.app/watch/.*\.jpg$',
            'title': 'crazy that i look like this tbh',
            'description': 'crazy that i look like this tbh',
            'upload_date': '20241030',
            'timestamp': 1730332128,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'tags': ['sexual'],
            'age_limit': 18,
        },
    }, {
        'url': 'at://did:plc:ia76kvnndjutgedggx2ibrem/app.bsky.feed.post/3l6zrz6zyl2dr',
        'md5': '71b0eb6d85d03145e6af6642c7fc6d78',
        'info_dict': {
            'id': '3l6zrz6zyl2dr',
            'ext': 'mp4',
            'uploader': 'mary🐇',
            'uploader_id': 'mary.my.id',
            'uploader_url': 'https://bsky.app/profile/mary.my.id',
            'channel_id': 'did:plc:ia76kvnndjutgedggx2ibrem',
            'channel_url': 'https://bsky.app/profile/did:plc:ia76kvnndjutgedggx2ibrem',
            'thumbnail': r're:https://video.bsky.app/watch/.*\.jpg$',
            'title': 'Bluesky video #3l6zrz6zyl2dr',
            'upload_date': '20241021',
            'timestamp': 1729523172,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'tags': [],
        },
    }, {
        'url': 'https://bsky.app/profile/purpleicetea.bsky.social/post/3l7gv55dc2o2w',
        'info_dict': {
            'id': '3l7gv55dc2o2w',
        },
        'playlist': [{
            'info_dict': {
                'id': '3l7gv55dc2o2w',
                'ext': 'mp4',
                'upload_date': '20241026',
                'description': 'One of my favorite videos',
                'comment_count': int,
                'uploader_url': 'https://bsky.app/profile/purpleicetea.bsky.social',
                'uploader': 'Purple.Ice.Tea',
                'thumbnail': r're:https://video.bsky.app/watch/.*\.jpg$',
                'channel_url': 'https://bsky.app/profile/did:plc:bjh5ffwya5f53dfy47dezuwx',
                'like_count': int,
                'channel_id': 'did:plc:bjh5ffwya5f53dfy47dezuwx',
                'repost_count': int,
                'timestamp': 1729973202,
                'tags': [],
                'uploader_id': 'purpleicetea.bsky.social',
                'title': 'One of my favorite videos',
            },
        }, {
            'info_dict': {
                'id': '3l77u64l7le2e',
                'ext': 'mp4',
                'title': 'hearing people on twitter say that bluesky isn\'...',
                'like_count': int,
                'uploader_id': 'thafnine.net',
                'uploader_url': 'https://bsky.app/profile/thafnine.net',
                'upload_date': '20241024',
                'channel_url': 'https://bsky.app/profile/did:plc:6ttyq36rhiyed7wu3ws7dmqj',
                'description': r're:(?s)hearing people on twitter say that bluesky .{93}',
                'tags': [],
                'alt_title': 'md5:9b1ee1937fb3d1a81e932f9ec14d560e',
                'uploader': 'T9',
                'channel_id': 'did:plc:6ttyq36rhiyed7wu3ws7dmqj',
                'thumbnail': r're:https://video.bsky.app/watch/.*\.jpg$',
                'timestamp': 1729731642,
                'comment_count': int,
                'repost_count': int,
            },
        }],
    }]
    _BLOB_URL_TMPL = '{}/xrpc/com.atproto.sync.getBlob'

    def _get_service_endpoint(self, did, video_id):
        if did.startswith('did:web:'):
            url = f'https://{did[8:]}/.well-known/did.json'
        else:
            url = f'https://plc.directory/{did}'
        services = self._download_json(
            url, video_id, 'Fetching service endpoint', 'Falling back to bsky.social', fatal=False)
        return traverse_obj(
            services, ('service', lambda _, x: x['type'] == 'AtprotoPersonalDataServer',
                       'serviceEndpoint', {url_or_none}, any)) or 'https://bsky.social'

    def _extract_post(self, handle, post_id):
        return self._download_json(
            'https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread',
            post_id, query={
                'uri': f'at://{handle}/app.bsky.feed.post/{post_id}',
                'depth': 0,
                'parentHeight': 0,
            })['thread']['post']

    def _real_extract(self, url):
        handle, video_id = self._match_valid_url(url).group('handle', 'id')
        post = self._extract_post(handle, video_id)

        entries = []
        # app.bsky.embed.video.view/app.bsky.embed.external.view
        entries.extend(self._extract_videos(post, video_id))
        # app.bsky.embed.recordWithMedia.view
        entries.extend(self._extract_videos(
            post, video_id, embed_path=('embed', 'media'), record_subpath=('embed', 'media')))
        # app.bsky.embed.record.view
        if nested_post := traverse_obj(post, ('embed', 'record', ('record', None), {dict}, any)):
            entries.extend(self._extract_videos(
                nested_post, video_id, embed_path=('embeds', 0), record_path='value'))

        if not entries:
            raise ExtractorError('No video could be found in this post', expected=True)
        if len(entries) == 1:
            return entries[0]
        return self.playlist_result(entries, video_id)

    @staticmethod
    def _build_profile_url(path):
        return format_field(path, None, 'https://bsky.app/profile/%s', default=None)

    def _extract_videos(self, root, video_id, embed_path='embed', record_path='record', record_subpath='embed'):
        embed_path = variadic(embed_path, (str, bytes, dict, set))
        record_path = variadic(record_path, (str, bytes, dict, set))
        record_subpath = variadic(record_subpath, (str, bytes, dict, set))

        entries = []
        if external_uri := traverse_obj(root, (
                ((*record_path, *record_subpath), embed_path), 'external', 'uri', {url_or_none}, any)):
            entries.append(self.url_result(external_uri))
        if playlist := traverse_obj(root, (*embed_path, 'playlist', {url_or_none})):
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                playlist, video_id, 'mp4', m3u8_id='hls', fatal=False)
        else:
            return entries

        video_cid = traverse_obj(
            root, (*embed_path, 'cid', {str}),
            (*record_path, *record_subpath, 'video', 'ref', '$link', {str}))
        did = traverse_obj(root, ('author', 'did', {str}))

        if did and video_cid:
            endpoint = self._get_service_endpoint(did, video_id)

            formats.append({
                'format_id': 'blob',
                'quality': 1,
                'url': update_url_query(
                    self._BLOB_URL_TMPL.format(endpoint), {'did': did, 'cid': video_cid}),
                **traverse_obj(root, (*embed_path, 'aspectRatio', {
                    'width': ('width', {int_or_none}),
                    'height': ('height', {int_or_none}),
                })),
                **traverse_obj(root, (*record_path, *record_subpath, 'video', {
                    'filesize': ('size', {int_or_none}),
                    'ext': ('mimeType', {mimetype2ext}),
                })),
            })

            for sub_data in traverse_obj(root, (
                    *record_path, *record_subpath, 'captions', lambda _, v: v['file']['ref']['$link'])):
                subtitles.setdefault(sub_data.get('lang') or 'und', []).append({
                    'url': update_url_query(
                        self._BLOB_URL_TMPL.format(endpoint), {'did': did, 'cid': sub_data['file']['ref']['$link']}),
                    'ext': traverse_obj(sub_data, ('file', 'mimeType', {mimetype2ext})),
                })

        entries.append({
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(root, {
                'id': ('uri', {url_basename}),
                'thumbnail': (*embed_path, 'thumbnail', {url_or_none}),
                'alt_title': (*embed_path, 'alt', {str}, filter),
                'uploader': ('author', 'displayName', {str}),
                'uploader_id': ('author', 'handle', {str}),
                'uploader_url': ('author', 'handle', {self._build_profile_url}),
                'channel_id': ('author', 'did', {str}),
                'channel_url': ('author', 'did', {self._build_profile_url}),
                'like_count': ('likeCount', {int_or_none}),
                'repost_count': ('repostCount', {int_or_none}),
                'comment_count': ('replyCount', {int_or_none}),
                'timestamp': ('indexedAt', {parse_iso8601}),
                'tags': ('labels', ..., 'val', {str}, all, {orderedSet}),
                'age_limit': (
                    'labels', ..., 'val', {lambda x: 18 if x in ('sexual', 'porn', 'graphic-media') else None}, any),
                'description': (*record_path, 'text', {str}, filter),
                'title': (*record_path, 'text', {lambda x: x.replace('\n', ' ')}, {truncate_string(left=50)}),
            }),
        })
        return entries
