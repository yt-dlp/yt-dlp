from .common import InfoExtractor
from ..utils import UserNotLive, int_or_none, parse_iso8601, url_or_none, urljoin
from ..utils.traversal import traverse_obj


class PartiBaseIE(InfoExtractor):
    def _call_api(self, path, video_id, note=None):
        return self._download_json(
            f'https://prod-api.parti.com/parti_v2/profile/{path}', video_id, note, headers={
                'Origin': 'https://parti.com',
                'Referer': 'https://parti.com/',
            })


class PartiVideoIE(PartiBaseIE):
    IE_NAME = 'parti:video'
    _VALID_URL = r'https?://(?:www\.)?parti\.com/video/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://parti.com/video/66284',
        'info_dict': {
            'id': '66284',
            'ext': 'mp4',
            'title': 'NOW LIVE ',
            'upload_date': '20250327',
            'categories': ['Gaming'],
            'thumbnail': 'https://media.parti.com/351424_eb9e5250-2821-484a-9c5f-ca99aa666c87.png',
            'channel': 'ItZTMGG',
            'timestamp': 1743044379,
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._call_api(f'get_livestream_channel_info/recent/{video_id}', video_id)

        return {
            'id': video_id,
            'formats': self._extract_m3u8_formats(
                urljoin('https://media.parti.com/', data['livestream_recording']), video_id, 'mp4'),
            **traverse_obj(data, {
                'title': ('event_title', {str}),
                'channel': ('user_name', {str}),
                'thumbnail': ('event_file', {url_or_none}),
                'categories': ('category_name', {str}, filter, all),
                'timestamp': ('event_start_ts', {int_or_none}),
            }),
        }


class PartiLivestreamIE(PartiBaseIE):
    IE_NAME = 'parti:livestream'
    _VALID_URL = r'https?://(?:www\.)?parti\.com/(?!video/)(?P<id>[\w/-]+)'
    _TESTS = [{
        'url': 'https://parti.com/247CryptoTracker',
        'info_dict': {
            'ext': 'mp4',
            'id': '247CryptoTracker',
            'description': 'md5:a78051f3d7e66e6a64c6b1eaf59fd364',
            'title': r"re:I'm Live on Parti \d{4}-\d{2}-\d{2} \d{2}:\d{2}",
            'thumbnail': r're:https://media\.parti\.com/stream-screenshots/.+\.png',
            'live_status': 'is_live',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        creator_slug = self._match_id(url)

        encoded_creator_slug = creator_slug.replace('/', '%23')
        creator_id = self._call_api(
            f'user_id_from_name/{encoded_creator_slug}',
            creator_slug, note='Fetching user ID')['user_id']

        data = self._call_api(
            f'get_livestream_channel_info/{creator_id}', creator_id,
            note='Fetching user profile feed')['channel_info']

        if not traverse_obj(data, ('channel', 'is_live', {bool})):
            raise UserNotLive(video_id=creator_id)

        channel_info = data['channel']

        return {
            'id': creator_slug,
            'formats': self._extract_m3u8_formats(channel_info['playback_url'], creator_slug, live=True),
            'is_live': True,
            **traverse_obj(data, {
                'title': ('livestream_event_info', 'event_name', {str}),
                'description': ('livestream_event_info', 'event_description', {str}),
                'thumbnail': ('livestream_event_info', 'livestream_preview_file', {url_or_none}),
                'timestamp': ('stream', 'start_time', {parse_iso8601}),
                'view_count': ('stream', 'viewer_count', {int_or_none}),
            }),
        }
