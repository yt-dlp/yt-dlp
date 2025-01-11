from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
    parse_iso8601,
    parse_resolution,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class PlVideoIE(InfoExtractor):
    IE_DESC = 'Платформа'
    _VALID_URL = r'https?://(?:www\.)?plvideo\.ru/(?:watch\?(?:[^#]+&)?v=|shorts/)(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://plvideo.ru/watch?v=Y5JzUzkcQTMK',
        'md5': 'fe8e18aca892b3b31f3bf492169f8a26',
        'info_dict': {
            'id': 'Y5JzUzkcQTMK',
            'ext': 'mp4',
            'thumbnail': 'https://img.plvideo.ru/images/fp-2024-images/v/cover/37/dd/37dd00a4c96c77436ab737e85947abd7/original663a4a3bb713e5.33151959.jpg',
            'title': 'Presidente de Cuba llega a Moscú en una visita de trabajo',
            'channel': 'RT en Español',
            'channel_id': 'ZH4EKqunVDvo',
            'media_type': 'video',
            'comment_count': int,
            'tags': ['rusia', 'cuba', 'russia', 'miguel díaz-canel'],
            'description': 'md5:a1a395d900d77a86542a91ee0826c115',
            'released_timestamp': 1715096124,
            'channel_is_verified': True,
            'like_count': int,
            'timestamp': 1715095911,
            'duration': 44320,
            'view_count': int,
            'dislike_count': int,
            'upload_date': '20240507',
            'modified_date': '20240701',
            'channel_follower_count': int,
            'modified_timestamp': 1719824073,
        },
    }, {
        'url': 'https://plvideo.ru/shorts/S3Uo9c-VLwFX',
        'md5': '7d8fa2279406c69d2fd2a6fc548a9805',
        'info_dict': {
            'id': 'S3Uo9c-VLwFX',
            'ext': 'mp4',
            'channel': 'Romaatom',
            'tags': 'count:22',
            'dislike_count': int,
            'upload_date': '20241130',
            'description': 'md5:452e6de219bf2f32bb95806c51c3b364',
            'duration': 58433,
            'modified_date': '20241130',
            'thumbnail': 'https://img.plvideo.ru/images/fp-2024-11-cover/S3Uo9c-VLwFX/f9318999-a941-482b-b700-2102a7049366.jpg',
            'media_type': 'shorts',
            'like_count': int,
            'modified_timestamp': 1732961458,
            'channel_is_verified': True,
            'channel_id': 'erJyyTIbmUd1',
            'timestamp': 1732961355,
            'comment_count': int,
            'title': 'Белоусов отменил приказы о кадровом резерве на гражданской службе',
            'channel_follower_count': int,
            'view_count': int,
            'released_timestamp': 1732961458,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video_data = self._download_json(
            f'https://api.g1.plvideo.ru/v1/videos/{video_id}?Aud=18', video_id)

        is_live = False
        formats = []
        subtitles = {}
        automatic_captions = {}
        for quality, data in traverse_obj(video_data, ('item', 'profiles', {dict.items}, lambda _, v: url_or_none(v[1]['hls']))):
            formats.append({
                'format_id': quality,
                'ext': 'mp4',
                'protocol': 'm3u8_native',
                **traverse_obj(data, {
                    'url': 'hls',
                    'fps': ('fps', {float_or_none}),
                    'aspect_ratio': ('aspectRatio', {float_or_none}),
                }),
                **parse_resolution(quality),
            })
        if livestream_url := traverse_obj(video_data, ('item', 'livestream', 'url', {url_or_none})):
            is_live = True
            formats.extend(self._extract_m3u8_formats(livestream_url, video_id, 'mp4', live=True))
        for lang, url in traverse_obj(video_data, ('item', 'subtitles', {dict.items}, lambda _, v: url_or_none(v[1]))):
            if lang.endswith('-auto'):
                automatic_captions.setdefault(lang[:-5], []).append({
                    'url': url,
                })
            else:
                subtitles.setdefault(lang, []).append({
                    'url': url,
                })

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'automatic_captions': automatic_captions,
            'is_live': is_live,
            **traverse_obj(video_data, ('item', {
                'id': ('id', {str}),
                'title': ('title', {str}),
                'description': ('description', {str}),
                'thumbnail': ('cover', 'paths', 'original', 'src', {url_or_none}),
                'duration': ('uploadFile', 'videoDuration', {int_or_none}),
                'channel': ('channel', 'name', {str}),
                'channel_id': ('channel', 'id', {str}),
                'channel_follower_count': ('channel', 'stats', 'subscribers', {int_or_none}),
                'channel_is_verified': ('channel', 'verified', {bool}),
                'tags': ('tags', ..., {str}),
                'timestamp': ('createdAt', {parse_iso8601}),
                'released_timestamp': ('publishedAt', {parse_iso8601}),
                'modified_timestamp': ('updatedAt', {parse_iso8601}),
                'view_count': ('stats', 'viewTotalCount', {int_or_none}),
                'like_count': ('stats', 'likeCount', {int_or_none}),
                'dislike_count': ('stats', 'dislikeCount', {int_or_none}),
                'comment_count': ('stats', 'commentCount', {int_or_none}),
                'media_type': ('type', {str}),
            })),
        }
