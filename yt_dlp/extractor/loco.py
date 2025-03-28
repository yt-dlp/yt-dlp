from .common import InfoExtractor
from ..utils import int_or_none, url_or_none
from ..utils.traversal import require, traverse_obj


class LocoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?loco\.com/(?P<type>streamers|stream)/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://loco.com/streamers/teuzinfps',
        'info_dict': {
            'id': 'teuzinfps',
            'ext': 'mp4',
            'title': r're:MS BOLADAO, RESENHA & GAMEPLAY ALTO NIVEL',
            'description': 'bom e novo',
            'uploader_id': 'RLUVE3S9JU',
            'channel': 'teuzinfps',
            'channel_follower_count': int,
            'comment_count': int,
            'view_count': int,
            'concurrent_view_count': int,
            'like_count': int,
            'thumbnail': 'https://static.ivory.getloconow.com/default_thumb/743701a9-98ca-41ae-9a8b-70bd5da070ad.jpg',
            'tags': ['MMORPG', 'Gameplay'],
            'series': 'Tibia',
            'timestamp': int,
            'modified_timestamp': int,
            'live_status': 'is_live',
            'upload_date': str,
            'modified_date': str,
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }, {
        'url': 'https://loco.com/stream/c64916eb-10fb-46a9-9a19-8c4b7ed064e7',
        'md5': '45ebc8a47ee1c2240178757caf8881b5',
        'info_dict': {
            'id': 'c64916eb-10fb-46a9-9a19-8c4b7ed064e7',
            'ext': 'mp4',
            'title': 'PAULINHO LOKO NA LOCO!',
            'description': 'live on na loco',
            'uploader_id': '2MDO7Z1DPM',
            'channel': 'paulinholokobr',
            'channel_follower_count': int,
            'comment_count': int,
            'view_count': int,
            'concurrent_view_count': int,
            'like_count': int,
            'duration': 14491,
            'thumbnail': 'https://static.ivory.getloconow.com/default_thumb/59b5970b-23c1-4518-9e96-17ce341299fe.jpg',
            'tags': ['Gameplay'],
            'series': 'GTA 5',
            'timestamp': 1740612872,
            'modified_timestamp': 1740613037,
            'upload_date': '20250226',
            'modified_date': '20250226',
        },
    }]

    def _real_extract(self, url):
        video_type, video_id = self._match_valid_url(url).group('type', 'id')
        webpage = self._download_webpage(url, video_id)
        stream = traverse_obj(self._search_nextjs_data(webpage, video_id), (
            'props', 'pageProps', ('liveStreamData', 'stream'), {dict}, any, {require('stream info')}))

        return {
            'formats': self._extract_m3u8_formats(stream['conf']['hls'], video_id),
            'id': video_id,
            'is_live': video_type == 'streamers',
            **traverse_obj(stream, {
                'title': ('title', {str}),
                'series': ('game_name', {str}),
                'uploader_id': ('user_uid', {str}),
                'channel': ('alias', {str}),
                'description': ('description', {str}),
                'concurrent_view_count': ('viewersCurrent', {int_or_none}),
                'view_count': ('total_views', {int_or_none}),
                'thumbnail': ('thumbnail_url_small', {url_or_none}),
                'like_count': ('likes', {int_or_none}),
                'tags': ('tags', ..., {str}),
                'timestamp': ('started_at', {int_or_none(scale=1000)}),
                'modified_timestamp': ('updated_at', {int_or_none(scale=1000)}),
                'comment_count': ('comments_count', {int_or_none}),
                'channel_follower_count': ('followers_count', {int_or_none}),
                'duration': ('duration', {int_or_none}),
            }),
        }
