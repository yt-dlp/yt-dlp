from .common import InfoExtractor
from ..utils import UserNotLive, int_or_none, parse_iso8601, url_or_none, urljoin
from ..utils.traversal import require, traverse_obj


class PartiBaseIE(InfoExtractor):
    _RECORDING_BASE_URL = 'https://watch.parti.com'
    _GET_LIVESTREAM_API = 'https://api-backend.parti.com/parti_v2/profile/get_livestream_channel_info'
    _PLAYBACK_VERSION = '1.17.0'

    def _get_formats(self, stream_url, creator, is_live):
        return self._extract_m3u8_formats(stream_url, creator, 'mp4', live=is_live)

    def _build_recording_url(self, path):
        return self._RECORDING_BASE_URL + '/' + path


class PartiVideoIE(PartiBaseIE):
    IE_NAME = 'parti:video'
    IE_DESC = 'Download a video from parti.com'
    _VALID_URL = r'https://parti\.com/video/(?P<id>\d+)'
    _TESTS = [
        {
            'url': 'https://parti.com/video/66284',
            'info_dict': {
                'id': '66284',
                'ext': 'mp4',
                'title': str,
                'upload_date': str,
                'is_live': False,
                'categories': list,
                'thumbnail': str,
                'channel': str,
            },
            'params': {'skip_download': 'm3u8'},
        },
    ]

    def _get_video_info(self, video_id):
        url = self._GET_LIVESTREAM_API + '/recent/' + video_id
        data = self._download_json(url, video_id)
        return traverse_obj(data, {
            'channel': ('user_name', {str}),
            'thumbnail': ('event_file', {str}),
            'categories': ('category', {lambda c: [c]}),
            'url': ('livestream_recording', {str}),
            'title': ('event_title', {str}),
            'upload_date': ('event_start_ts', {lambda ts: datetime.date.fromtimestamp(ts).strftime('%Y%m%d')}),
        })

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_info = self._get_video_info(video_id)
        full_recording_url = self._build_recording_url(video_info['url'])
        formats = self._get_formats(full_recording_url, video_info['channel'], is_live=False)

        return {
            'id': video_id,
            'url': url,
            'formats': formats,
            'is_live': False,
            **video_info,
        }


class PartiLivestreamIE(PartiBaseIE):
    IE_NAME = 'parti:livestream'
    IE_DESC = 'Download a stream from parti.com'
    _VALID_URL = r'https://parti\.com/creator/(parti|discord|telegram)/(?P<id>[\w-]+)'
    _TESTS = [
        {
            'url': 'https://parti.com/creator/parti/SpartanTheDog',
            'info_dict': {
                'id': 'SpartanTheDog',
                'ext': 'mp4',
                'title': str,
                'description': str,
                'upload_date': str,
                'is_live': True,
                'live_status': 'is_live',
            },
            'params': {'skip_download': 'm3u8'},
        },
    ]
    _CREATOR_API = 'https://api-backend.parti.com/parti_v2/profile/get_user_by_social_media/parti'

    def _get_creator_id(self, creator):
        """ The creator ID is a number returned as plain text """
        url = self._CREATOR_API + '/' + creator
        page = self._download_webpage(url, None, 'Fetching creator id')
        return str(page)

    def _get_live_playback_data(self, creator_id):
        """ If the stream is live, we can use this URL to download. """
        url = self._GET_LIVESTREAM_API + '/' + creator_id
        data = self._download_json(url, None, 'Fetching user profile feed')
        if not data:
            raise Exception('No data!')

        extracted = traverse_obj(data, {
            'base_url': ('channel_info', 'channel', 'playback_url', {str}),
            'auth_token': ('channel_info', 'channel', 'playback_auth_token', {str}),
            'viewer_count': ('channel_info', 'stream', 'viewer_count', {int_or_none}),
            'is_live': ('channel_info', 'stream', {lambda x: x is not None}),
        })

        base_url = extracted['base_url']
        auth_token = extracted['auth_token']
        url = None
        if base_url and auth_token:
            url = f'{base_url}?token={auth_token}&player_version={self._PLAYBACK_VERSION}'

        return {
            'url': url,
            **extracted,
        }

    def _real_extract(self, url):
        creator = self._match_id(url)

        creator_id = self._get_creator_id(creator)
        playback_data = self._get_live_playback_data(creator_id)
        if not playback_data['is_live']:
            raise UserNotLive

        formats = self._get_formats(playback_data['url'], creator, is_live=True)

        created_at = datetime.datetime.now()
        streamed_at = created_at.strftime('%Y%m%d')
        return {
            'id': creator,
            'url': url,
            'title': f'{creator}\'s Parti Livestream',
            'description': f'A livestream from {created_at}',
            'upload_date': streamed_at,
            'is_live': True,
            'formats': formats,
        }
