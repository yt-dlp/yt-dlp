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
    _VALID_URL = r'https?://(?:www\.)?plvideo\.ru/(?:watch\?(?:[^#]+&)?v=|shorts/)(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://plvideo.ru/watch?v=owo7vk1sTqzA',
        'md5': 'be768d1d4c44462f180ca39927ad07f2',
        'info_dict': {
            'id': 'owo7vk1sTqzA',
            'ext': 'mp4',
            'thumbnail': 'https://img.plvideo.ru/images/fp-2024-images/v/cover/d9/e9/d9e9a78134c01ca56e9e795244e1ba95/original6753a778ab7fe1.79895808.jpg',
            'title': 'Две угрозы для ВСУ на Донбассе, интервью Лаврова Карлсону, что означают для Украины события в Сирии.',
            'channel': 'Страна.ua',
            'channel_id': 'hX0oxkAgBfaK',
            'media_type': 'video',
            'comment_count': int,
            'tags': ['политика', 'путин', 'зеленский', 'украина', 'война', 'новости', 'сша', 'такеркарлсон', 'интервью'],
            'description': 'md5:52e3cb3cf9deac3a0d9c3b6523a1c1ff',
            'released_timestamp': 1733535609,
            'channel_is_verified': False,
            'like_count': int,
            'timestamp': 1733535474,
            'duration': 1112011,
            'view_count': int,
            'dislike_count': int,
            'upload_date': '20241207',
            'modified_date': '20241207',
            'channel_follower_count': int,
            'modified_timestamp': 1733535710,
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
