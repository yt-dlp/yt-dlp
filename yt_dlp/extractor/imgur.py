import functools
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    float_or_none,
    int_or_none,
    js_to_json,
    mimetype2ext,
    parse_iso8601,
    str_or_none,
    strip_or_none,
    traverse_obj,
    url_or_none,
)


class ImgurBaseIE(InfoExtractor):
    _CLIENT_ID = '546c25a59c58ad7'

    @classmethod
    def _imgur_result(cls, item_id):
        return cls.url_result(f'https://imgur.com/{item_id}', ImgurIE, item_id)

    def _call_api(self, endpoint, video_id, **kwargs):
        return self._download_json(
            f'https://api.imgur.com/post/v1/{endpoint}/{video_id}?client_id={self._CLIENT_ID}&include=media,account',
            video_id, **kwargs)

    @staticmethod
    def get_description(s):
        if 'Discover the magic of the internet at Imgur' in s:
            return None
        return s or None


class ImgurIE(ImgurBaseIE):
    _VALID_URL = r'https?://(?:i\.)?imgur\.com/(?!(?:a|gallery|t|topic|r)/)(?:[^/?#]+-)?(?P<id>[a-zA-Z0-9]+)'

    _TESTS = [{
        'url': 'https://imgur.com/A61SaA1',
        'info_dict': {
            'id': 'A61SaA1',
            'ext': 'mp4',
            'title': 'MRW gifv is up and running without any bugs',
            'timestamp': 1416446068,
            'upload_date': '20141120',
            'dislike_count': int,
            'comment_count': int,
            'release_timestamp': 1416446068,
            'release_date': '20141120',
            'like_count': int,
            'thumbnail': 'https://i.imgur.com/A61SaA1h.jpg',
        },
    }, {
        # Test with URL slug
        'url': 'https://imgur.com/mrw-gifv-is-up-running-without-any-bugs-A61SaA1',
        'info_dict': {
            'id': 'A61SaA1',
            'ext': 'mp4',
            'title': 'MRW gifv is up and running without any bugs',
            'timestamp': 1416446068,
            'upload_date': '20141120',
            'dislike_count': int,
            'comment_count': int,
            'release_timestamp': 1416446068,
            'release_date': '20141120',
            'like_count': int,
            'thumbnail': 'https://i.imgur.com/A61SaA1h.jpg',
        },
    }, {
        'url': 'https://i.imgur.com/A61SaA1.gifv',
        'only_matching': True,
    }, {
        'url': 'https://i.imgur.com/crGpqCV.mp4',
        'only_matching': True,
    }, {
        'url': 'https://i.imgur.com/jxBXAMC.gifv',
        'info_dict': {
            'id': 'jxBXAMC',
            'ext': 'mp4',
            'title': 'Fahaka puffer feeding',
            'timestamp': 1533835503,
            'upload_date': '20180809',
            'release_date': '20180809',
            'like_count': int,
            'duration': 30.0,
            'comment_count': int,
            'release_timestamp': 1533835503,
            'thumbnail': 'https://i.imgur.com/jxBXAMCh.jpg',
            'dislike_count': int,
        },
    }, {
        # needs Accept header, ref: https://github.com/yt-dlp/yt-dlp/issues/9458
        'url': 'https://imgur.com/zV03bd5',
        'md5': '59df97884e8ba76143ff6b640a0e2904',
        'info_dict': {
            'id': 'zV03bd5',
            'ext': 'mp4',
            'title': 'Ive - Liz',
            'timestamp': 1710491255,
            'upload_date': '20240315',
            'like_count': int,
            'dislike_count': int,
            'duration': 56.92,
            'comment_count': int,
            'release_timestamp': 1710491255,
            'release_date': '20240315',
            'thumbnail': 'https://i.imgur.com/zV03bd5h.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._call_api('media', video_id)
        if not traverse_obj(data, ('media', 0, (
                ('type', {lambda t: t == 'video' or None}),
                ('metadata', 'is_animated'))), get_all=False):
            raise ExtractorError(f'{video_id} is not a video or animated image', expected=True)
        webpage = self._download_webpage(
            f'https://i.imgur.com/{video_id}.gifv', video_id, fatal=False) or ''
        formats = []

        media_fmt = traverse_obj(data, ('media', 0, {
            'url': ('url', {url_or_none}),
            'ext': ('ext', {str}),
            'width': ('width', {int_or_none}),
            'height': ('height', {int_or_none}),
            'filesize': ('size', {int_or_none}),
            'acodec': ('metadata', 'has_sound', {lambda b: None if b else 'none'}),
        }))
        media_url = media_fmt.get('url')
        if media_url:
            if not media_fmt.get('ext'):
                media_fmt['ext'] = mimetype2ext(traverse_obj(
                    data, ('media', 0, 'mime_type'))) or determine_ext(media_url)
            if traverse_obj(data, ('media', 0, 'type')) == 'image':
                media_fmt['acodec'] = 'none'
                media_fmt.setdefault('preference', -10)
            formats.append(media_fmt)

        video_elements = self._search_regex(
            r'(?s)<div class="video-elements">(.*?)</div>',
            webpage, 'video elements', default=None)

        if video_elements:
            def og_get_size(media_type):
                return {
                    p: int_or_none(self._og_search_property(f'{media_type}:{p}', webpage, default=None))
                    for p in ('width', 'height')
                }

            size = og_get_size('video')
            if not any(size.values()):
                size = og_get_size('image')

            formats = traverse_obj(
                re.finditer(r'<source\s+src="(?P<src>[^"]+)"\s+type="(?P<type>[^"]+)"', video_elements),
                (..., {
                    'format_id': ('type', {lambda s: s.partition('/')[2]}),
                    'url': ('src', {self._proto_relative_url}),
                    'ext': ('type', {mimetype2ext}),
                }))
            for f in formats:
                f.update(size)

            # We can get the original gif format from the webpage as well
            gif_json = traverse_obj(self._search_json(
                r'var\s+videoItem\s*=', webpage, 'GIF info', video_id,
                transform_source=js_to_json, fatal=False), {
                    'url': ('gifUrl', {self._proto_relative_url}),
                    'filesize': ('size', {int_or_none}),
            })
            if gif_json:
                gif_json.update(size)
                gif_json.update({
                    'format_id': 'gif',
                    'preference': -10,  # gifs < videos
                    'ext': 'gif',
                    'acodec': 'none',
                    'vcodec': 'gif',
                    'container': 'gif',
                })
                formats.append(gif_json)

        search = functools.partial(self._html_search_meta, html=webpage, default=None)

        twitter_fmt = {
            'format_id': 'twitter',
            'url': url_or_none(search('twitter:player:stream')),
            'ext': mimetype2ext(search('twitter:player:stream:content_type')),
            'width': int_or_none(search('twitter:width')),
            'height': int_or_none(search('twitter:height')),
        }
        if twitter_fmt['url']:
            formats.append(twitter_fmt)

        if not formats:
            self.raise_no_formats(
                f'No sources found for video {video_id}. Maybe a plain image?', expected=True)
        self._remove_duplicate_formats(formats)

        return {
            'title': self._og_search_title(webpage, default=None),
            'description': self.get_description(self._og_search_description(webpage, default='')),
            **traverse_obj(data, {
                'uploader_id': ('account_id', {lambda a: str(a) if int_or_none(a) else None}),
                'uploader': ('account', 'username', {lambda x: strip_or_none(x) or None}),
                'uploader_url': ('account', 'avatar_url', {url_or_none}),
                'like_count': ('upvote_count', {int_or_none}),
                'dislike_count': ('downvote_count', {int_or_none}),
                'comment_count': ('comment_count', {int_or_none}),
                'age_limit': ('is_mature', {lambda x: 18 if x else None}),
                'timestamp': (('updated_at', 'created_at'), {parse_iso8601}),
                'release_timestamp': ('created_at', {parse_iso8601}),
            }, get_all=False),
            **traverse_obj(data, ('media', 0, 'metadata', {
                'title': ('title', {lambda x: strip_or_none(x) or None}),
                'description': ('description', {self.get_description}),
                'duration': ('duration', {float_or_none}),
                'timestamp': (('updated_at', 'created_at'), {parse_iso8601}),
                'release_timestamp': ('created_at', {parse_iso8601}),
            }), get_all=False),
            'id': video_id,
            'formats': formats,
            'thumbnails': [{
                'url': thumbnail_url,
                'http_headers': {'Accept': '*/*'},
            }] if (thumbnail_url := search(['thumbnailUrl', 'twitter:image', 'og:image'])) else None,
            'http_headers': {'Accept': '*/*'},
        }


class ImgurGalleryBaseIE(ImgurBaseIE):
    _GALLERY = True

    def _real_extract(self, url):
        gallery_id = self._match_id(url)

        data = self._call_api('albums', gallery_id, fatal=False, expected_status=404)

        info = traverse_obj(data, {
            'title': ('title', {lambda x: strip_or_none(x) or None}),
            'description': ('description', {self.get_description}),
        })

        if traverse_obj(data, 'is_album'):

            items = traverse_obj(data, (
                'media', lambda _, v: v.get('type') == 'video' or v['metadata']['is_animated'],
                'id', {lambda x: str_or_none(x) or None}))

            # if a gallery with exactly one video, apply album metadata to video
            media_id = None
            if self._GALLERY and len(items) == 1:
                media_id = items[0]

            if not media_id:
                result = self.playlist_result(
                    map(self._imgur_result, items), gallery_id)
                result.update(info)
                return result
            gallery_id = media_id

        result = self._imgur_result(gallery_id)
        info['_type'] = 'url_transparent'
        result.update(info)
        return result


class ImgurGalleryIE(ImgurGalleryBaseIE):
    IE_NAME = 'imgur:gallery'
    _VALID_URL = r'https?://(?:i\.)?imgur\.com/(?:gallery|(?:t(?:opic)?|r)/[^/?#]+)/(?:[^/?#]+-)?(?P<id>[a-zA-Z0-9]+)'

    _TESTS = [{
        # TODO: static images - replace with animated/video gallery
        'url': 'http://imgur.com/topic/Aww/ll5Vk',
        'only_matching': True,
    }, {
        'url': 'https://imgur.com/gallery/YcAQlkx',
        'add_ies': ['Imgur'],
        'info_dict': {
            'id': 'YcAQlkx',
            'ext': 'mp4',
            'title': 'Classic Steve Carell gif...cracks me up everytime....damn the repost downvotes....',
            'timestamp': 1358554297,
            'upload_date': '20130119',
            'uploader_id': '1648642',
            'uploader': 'wittyusernamehere',
            'release_timestamp': 1358554297,
            'thumbnail': 'https://i.imgur.com/YcAQlkxh.jpg',
            'release_date': '20130119',
            'uploader_url': 'https://i.imgur.com/N5Flb2v_d.png?maxwidth=290&fidelity=grand',
            'comment_count': int,
            'dislike_count': int,
            'like_count': int,
        },
    }, {
        # Test with slug
        'url': 'https://imgur.com/gallery/classic-steve-carell-gif-cracks-me-up-everytime-repost-downvotes-YcAQlkx',
        'add_ies': ['Imgur'],
        'info_dict': {
            'id': 'YcAQlkx',
            'ext': 'mp4',
            'title': 'Classic Steve Carell gif...cracks me up everytime....damn the repost downvotes....',
            'timestamp': 1358554297,
            'upload_date': '20130119',
            'uploader_id': '1648642',
            'uploader': 'wittyusernamehere',
            'release_timestamp': 1358554297,
            'release_date': '20130119',
            'thumbnail': 'https://i.imgur.com/YcAQlkxh.jpg',
            'uploader_url': 'https://i.imgur.com/N5Flb2v_d.png?maxwidth=290&fidelity=grand',
            'comment_count': int,
            'dislike_count': int,
            'like_count': int,
        },
    }, {
        # TODO: static image - replace with animated/video gallery
        'url': 'http://imgur.com/topic/Funny/N8rOudd',
        'only_matching': True,
    }, {
        'url': 'http://imgur.com/r/aww/VQcQPhM',
        'add_ies': ['Imgur'],
        'info_dict': {
            'id': 'VQcQPhM',
            'ext': 'mp4',
            'title': 'The boss is here',
            'timestamp': 1476494751,
            'upload_date': '20161015',
            'uploader_id': '19138530',
            'uploader': 'thematrixcam',
            'comment_count': int,
            'dislike_count': int,
            'uploader_url': 'https://i.imgur.com/qCjr5Pi_d.png?maxwidth=290&fidelity=grand',
            'release_timestamp': 1476494751,
            'like_count': int,
            'release_date': '20161015',
            'thumbnail': 'https://i.imgur.com/VQcQPhMh.jpg',
        },
    },
        # from https://github.com/ytdl-org/youtube-dl/pull/16674
        {
        'url': 'https://imgur.com/t/unmuted/6lAn9VQ',
        'info_dict': {
            'id': '6lAn9VQ',
            'title': 'Penguins !',
        },
        'playlist_count': 3,
    }, {
        'url': 'https://imgur.com/t/unmuted/penguins-penguins-6lAn9VQ',
        'info_dict': {
            'id': '6lAn9VQ',
            'title': 'Penguins !',
        },
        'playlist_count': 3,
    }, {
        'url': 'https://imgur.com/t/unmuted/kx2uD3C',
        'add_ies': ['Imgur'],
        'info_dict': {
            'id': 'ZVMv45i',
            'ext': 'mp4',
            'title': 'Intruder',
            'timestamp': 1528129683,
            'upload_date': '20180604',
            'release_timestamp': 1528129683,
            'release_date': '20180604',
            'like_count': int,
            'dislike_count': int,
            'comment_count': int,
            'duration': 30.03,
            'thumbnail': 'https://i.imgur.com/ZVMv45ih.jpg',
        },
    }, {
        'url': 'https://imgur.com/t/unmuted/wXSK0YH',
        'add_ies': ['Imgur'],
        'info_dict': {
            'id': 'JCAP4io',
            'ext': 'mp4',
            'title': 're:I got the blues$',
            'description': 'Luka’s vocal stylings.\n\nFP edit: don’t encourage me. I’ll never stop posting Luka and friends.',
            'timestamp': 1527809525,
            'upload_date': '20180531',
            'like_count': int,
            'dislike_count': int,
            'duration': 30.03,
            'comment_count': int,
            'release_timestamp': 1527809525,
            'thumbnail': 'https://i.imgur.com/JCAP4ioh.jpg',
            'release_date': '20180531',
        },
    }]


class ImgurAlbumIE(ImgurGalleryBaseIE):
    IE_NAME = 'imgur:album'
    _VALID_URL = r'https?://(?:i\.)?imgur\.com/a/(?:[^/?#]+-)?(?P<id>[a-zA-Z0-9]+)'
    _GALLERY = False
    _TESTS = [{
        # TODO: only static images - replace with animated/video gallery
        'url': 'http://imgur.com/a/j6Orj',
        'only_matching': True,
    },
        # from https://github.com/ytdl-org/youtube-dl/pull/21693
        {
        'url': 'https://imgur.com/a/iX265HX',
        'info_dict': {
            'id': 'iX265HX',
            'title': 'enen-no-shouboutai',
        },
        'playlist_count': 2,
    }, {
        # Test with URL slug
        'url': 'https://imgur.com/a/enen-no-shouboutai-iX265HX',
        'info_dict': {
            'id': 'iX265HX',
            'title': 'enen-no-shouboutai',
        },
        'playlist_count': 2,
    }, {
        'url': 'https://imgur.com/a/8pih2Ed',
        'info_dict': {
            'id': '8pih2Ed',
        },
        'playlist_mincount': 1,
    }]
