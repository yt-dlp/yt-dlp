from .common import InfoExtractor
from ..utils import (
    traverse_obj,
    unified_strdate,
)


class CrazyGamesIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)crazygames\.com/game/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.crazygames.com/game/cut-the-rope-ebx',
        'info_dict': {
            'id': 'cut-the-rope-ebx',
            'ext': 'mp4',
            'title': 'Cut the Rope',
            'description': 'Cut the Rope to feed large pieces of candy to a hungry creature called Om Nom. Collect all the stars for the highest rating and progress to more challenging levels with new puzzles.',
            'uploader': 'Famobi',
            'upload_date': '20240530',
            'like_count': int,
            'dislike_count': int,
            'average_rating': float,
            'categories': ['Puzzle'],
            'tags': ['Mobile', 'Physics', '2D', 'Logic', 'Mouse', 'Collect', 'Brain'],
        },
    }]

    def _real_extract(self, url):
        game_id = self._match_id(url)
        url_prefix = 'https://videos.crazygames.com/'

        metadata = self._download_json(
            f'https://api.crazygames.com/v4/en_US/page/game/{game_id}',
            game_id,
        )

        category = traverse_obj(metadata, ('game', 'category', 'name'))
        categories = [category] if category else None

        sizes = traverse_obj(metadata, ('game', 'videos', 'sizes', ...), default=[])
        blurred = traverse_obj(metadata, ('game', 'videos', 'blurredVideo'))
        original = traverse_obj(metadata, ('game', 'videos', 'original'))

        formats = []
        if original:
            formats.append({
                'url': f'{url_prefix}{original}',
                'format_note': 'Original',
            })

        for video in sizes:
            if not video.get('location'):
                continue
            formats.append({
                'url': f'{url_prefix}{video["location"]}',
                'width': video.get('width'),
                'height': video.get('height'),
                'preference': -2,
            })

        if blurred and blurred.get('location'):
            formats.append({
                'url': f'{url_prefix}{blurred["location"]}',
                'width': blurred.get('width'),
                'height': blurred.get('height'),
                'format_note': 'Blurred',
                'preference': -3,
            })

        return {
            'id': game_id,
            'title': traverse_obj(metadata, ('game', 'name')),
            'formats': formats,
            'description': traverse_obj(metadata, ('game', 'metaDescription')),
            'uploader': traverse_obj(metadata, ('game', 'developer')),
            'upload_date': unified_strdate(traverse_obj(metadata, ('game', 'addedOn'))),
            'like_count': traverse_obj(metadata, ('game', 'upvotes')),
            'dislike_count': traverse_obj(metadata, ('game', 'downvotes')),
            'average_rating': traverse_obj(metadata, ('game', 'rating')),
            'categories': categories,
            'tags': traverse_obj(metadata, ('game', 'tags', ..., 'name'), default=[]),
        }
