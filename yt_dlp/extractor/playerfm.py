from .common import InfoExtractor
from ..utils import clean_html, clean_podcast_url, int_or_none, str_or_none, url_or_none
from ..utils.traversal import traverse_obj


class PlayerFmIE(InfoExtractor):
    _VALID_URL = r'(?P<url>https?://(?:www\.)?player\.fm/(?:series/)?[\w-]+/(?P<id>[\w-]+))'
    _TESTS = [{
        'url': 'https://player.fm/series/chapo-trap-house/movie-mindset-33-casino-feat-felix',
        'info_dict': {
            'ext': 'mp3',
            'id': '478606546',
            'display_id': 'movie-mindset-33-casino-feat-felix',
            'thumbnail': r're:^https://.*\.(jpg|png)',
            'title': 'Movie Mindset 33 - Casino feat. Felix',
            'creators': ['Chapo Trap House'],
            'description': r're:The first episode of this season of Movie Mindset is free .+ we feel about it\.',
            'duration': 6830,
            'timestamp': 1745406000,
            'upload_date': '20250423',
        },
    }, {
        'url': 'https://player.fm/series/nbc-nightly-news-with-tom-llamas/thursday-april-17-2025',
        'info_dict': {
            'ext': 'mp3',
            'id': '477635490',
            'display_id': 'thursday-april-17-2025',
            'title': 'Thursday, April 17, 2025',
            'thumbnail': r're:^https://.*\.(jpg|png)',
            'duration': 1143,
            'description': 'md5:4890b8cf9a55a787561cd5d59dfcda82',
            'creators': ['NBC News'],
            'timestamp': 1744941374,
            'upload_date': '20250418',
        },
    }, {
        'url': 'https://player.fm/series/soccer-101/ep-109-its-kicking-off-how-have-the-rules-for-kickoff-changed-what-are-the-best-approaches-to-getting-the-game-underway-and-how-could-we-improve-on-the-present-system-ack3NzL3yibvs4pf',
        'info_dict': {
            'ext': 'mp3',
            'id': '481418710',
            'thumbnail': r're:^https://.*\.(jpg|png)',
            'title': r're:#109 It\'s kicking off! How have the rules for kickoff changed, .+ the present system\?',
            'creators': ['TSS'],
            'duration': 1510,
            'display_id': 'md5:b52ecacaefab891b59db69721bfd9b13',
            'description': 'md5:52a39e36d08d8919527454f152ad3c25',
            'timestamp': 1659102055,
            'upload_date': '20220729',
        },
    }]

    def _real_extract(self, url):
        display_id, url = self._match_valid_url(url).group('id', 'url')
        data = self._download_json(f'{url}.json', display_id)

        return {
            'display_id': display_id,
            'vcodec': 'none',
            **traverse_obj(data, {
                'id': ('id', {int}, {str_or_none}),
                'url': ('url', {clean_podcast_url}),
                'title': ('title', {str}),
                'description': ('description', {clean_html}),
                'duration': ('duration', {int_or_none}),
                'thumbnail': (('image', ('series', 'image')), 'url', {url_or_none}, any),
                'filesize': ('size', {int_or_none}),
                'timestamp': ('publishedAt', {int_or_none}),
                'creators': ('series', 'author', {str}, filter, all, filter),
            }),
        }
