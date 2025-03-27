import datetime

from ..utils import (
    int_or_none,
    traverse_obj,
)
from .common import InfoExtractor


class PartiIE(InfoExtractor):
    IE_DESC = 'Download a stream from parti.com'
    _VALID_URL = r'https://parti\.com/creator/(parti|discord|telegram)/(?P<id>[\w-]+)'
    _TESTS = [
        {
            'url': 'https://parti.com/creator/parti/ItZTMGG',
            'info_dict': {
                'id': 'ItZTMGG',
                'ext': 'mp4',
                'title': str,
                'description': str,
                'upload_date': str,
                'is_live': False,
            },
            'params': {'skip_download': 'm3u8'},
        },
    ]
    _CREATOR_API = 'https://api-backend.parti.com/parti_v2/profile/get_user_by_social_media/parti'
    _GET_LIVESTREAM_API = 'https://api-backend.parti.com/parti_v2/profile/get_livestream_channel_info'
    _GET_USER_FEED_API = 'https://api-backend.parti.com/parti_v2/profile/user_profile_feed/'
    _RECORDING_BASE_URL = 'https://watch.parti.com'
    _PLAYBACK_VERSION = '1.17.0'

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

        is_live = False
        viewer_count = 0
        if 'stream' in data:
            is_live = data['stream'] is not None
            if is_live:
                viewer_count = data['stream']['viewer_count']

        channel = data['channel_info']['channel']
        auth_token = channel['playback_auth_token']
        base_url = channel['playback_url']

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

    def _get_user_feed(self, creator_id):
        """ The user feed are VODs listed below the main stream """
        url = self._GET_USER_FEED_API + '/' + creator_id + '?limit=10'
        vods = self._download_json(url, None, 'Fetching user feed')
        if not vods:
            raise Exception('No vods found!')
        return list(vods)

    def _download_vod(self, url, creator, creator_id):
        """ Download the VOD visible on the creators feed """
        feed = self._get_user_feed(creator_id)
        vod = feed[0]
        vod_url = self._RECORDING_BASE_URL + '/' + vod['livestream_recording']
        created_at = datetime.date.fromtimestamp(vod['created_at'])
        upload_date = str(created_at).replace('-', '')

        formats = self._extract_m3u8_formats(vod_url, creator, 'mp4', live=False)
        return {
            'id': creator,
            'url': url,
            'title': f'{creator}\'s Parti VOD - {upload_date}',
            'description': vod['post_content'],
            'upload_date': upload_date,
            'is_live': False,
            'formats': formats,
        }

    def _download_livestream(self, url, creator, stream_url):
        """ Download a currently active livestream """
        formats = self._extract_m3u8_formats(stream_url, creator, 'mp4', live=True)

        created_at = datetime.datetime.now()
        upload_date = str(created_at.date()).replace('-', '')
        pretty_timestamp = str(created_at).replace(':', '_')
        return {
            'id': creator,
            'url': url,
            'title': f'{creator}\'s Parti Live - {pretty_timestamp}',
            'description': f'A livestream from {pretty_timestamp}',
            'upload_date': upload_date,
            'is_live': True,
            'formats': formats,
        }

    def _real_extract(self, url):
        creator = self._match_id(url)

        creator_id = self._get_creator_id(creator)
        playback_data = self._get_live_playback_data(creator_id)
        if not playback_data['is_live']:
            return self._download_vod(url, creator, creator_id)
        else:
            return self._download_livestream(url, creator, playback_data['url'])

