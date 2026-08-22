import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    UserNotLive,
    bool_or_none,
    int_or_none,
    parse_iso8601,
    traverse_obj,
    url_or_none,
)


class WTVBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'wtv'

    def _perform_login(self, username, password):
        login_payload = {
            'signInId': username,
            'password': password,
        }
        try:
            _ = self._download_webpage(
                'https://auth-service.w.tv/api/v1/signin',
                video_id=None,
                note='Logging in',
                data=json.dumps(login_payload).encode('utf-8'),
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                expected_status=(400, 401, 403),
            )
        except ExtractorError as e:
            raise ExtractorError('Login failed. Please check your credentials.', expected=True) from e

        cookies = self._get_cookies('https://w.tv')
        if 't_cookie' not in cookies:
            raise ExtractorError(
                'Login failed: Server did not set authentication cookies (t_cookie). '
                'Please check your username and password.',
                expected=True)


class WTVVodIE(WTVBaseIE):
    IE_NAME = 'wtv:vod'

    # Video ID part is a UUID v7 (case-sensitive on w.tv)
    # The [A-Za-z0-9_]{1,25} part is from username validation login found in https://w.tv/_nuxt/CNQ95Wgc.js
    _VALID_URL = r'https?://(?:www\.)?w\.tv/(?P<channel>[A-Za-z0-9_]{1,25})/videos/(?P<id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'

    _TESTS = [{
        'url': 'https://w.tv/ncs/videos/01a005c9-1c1b-73ba-850e-38cb161e8d0a',
        'md5': 'c37a25715cd75227264f29e149708f63',
        'info_dict': {
            'id': '01a005c9-1c1b-73ba-850e-38cb161e8d0a',
            'title': '24/7 Live NCS - No Copyright Songs Radio',
            'description': '',
            'ext': 'mp4',
            'thumbnail': 'https://streams.w.tv/ivs/v1/061051251131/IYjEZPH3zof6/2026/8/15/14/17/KRceMs90P2Wx/media/latest_thumbnail/thumb.jpg',
            'timestamp': 1786803461,
            'upload_date': '20260815',
            'channel': 'NCS',
            'channel_id': '019febc1-8340-770e-9dbe-c0447d36d16a',
            'channel_url': 'https://w.tv/ncs',
            'channel_follower_count': int,
            'channel_is_verified': bool,
            'duration': 172797,
            'view_count': int,
            'is_live': False,
            'live_status': 'was_live',
            'categories': ['Music'],
            'tags': ['ru', 'Music'],
        },
    }, {
        'url': 'https://w.tv/crazyapproach/videos/01a0243c-ec7d-75ac-85eb-45bf46f42979',
        'md5': 'd1289403ede9d9fc993be1b496dc41fc',
        'info_dict': {
            'id': '01a0243c-ec7d-75ac-85eb-45bf46f42979',
            'title': 'Astroneer #S2-03 in COOP',
            'description': '',
            'ext': 'mp4',
            'thumbnail': 'https://streams.w.tv/ivs/v1/061051251131/JaPl5ru6isfu/2026/8/21/12/12/8toVAGJHdHX9/media/latest_thumbnail/thumb.jpg',
            'timestamp': 1787314367,
            'upload_date': '20260821',
            'channel': 'CrazyApproach',
            'channel_id': '019e7d1c-5b7c-74a9-8091-3b54d93ba70a',
            'channel_url': 'https://w.tv/crazyapproach',
            'channel_follower_count': int,
            'channel_is_verified': False,  # unlikely to be verified
            'duration': 12519,
            'view_count': 1,
            'is_live': False,
            'live_status': 'was_live',
            'categories': ['Astroneer'],
            'tags': ['ru', '18+', 'Astroneer'],
        },
    }, {
        'url': 'https://w.tv/abcdefABCDEF012345_/videos/01234567-abcd-ef00-1111-fe0123456789',
        'only_matching': True,
    }, {
        'url': 'http://www.w.tv/a/videos/12345678-1234-1234-1234-123456789abc',
        'only_matching': True,
    }, {
        'url': 'https://w.tv/abcdefghijklmnopqrstuvwxy/videos/abcdef12-3456-7890-abcd-ef1234567890',
        'only_matching': True,
    }, {
        'url': 'https://w.tv/User_Name_123/videos/11111111-2222-3333-4444-555555555555',
        'only_matching': True,
    }, {
        'url': 'https://w.tv/testchannel/videos/00000000-0000-0000-0000-000000000000/?query1=string2&query2=string3#fragment',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        channel_name, video_id = self._match_valid_url(url).group('channel', 'id')

        metadata = self._download_json(
            f'https://streams-search-service.w.tv/api/v1/streams/{video_id}',
            video_id,
            note='Downloading stream metadata',
        )
        stream_data = metadata.get('stream') or {}

        stream_id_from_api = stream_data.get('streamId')
        if stream_id_from_api is not None and stream_id_from_api != video_id:
            self.report_warning('Inconsistent stream ID between provided in the URL and received from API, using the one from the API...')
            video_id = stream_id_from_api

        channel_data = stream_data.get('channel') or {}

        stream_state = stream_data.get('state')
        if stream_state == 'started':
            live_status = 'is_live'
        elif stream_state == 'finished':
            live_status = 'was_live'
        elif bool_or_none(channel_data.get('live')):  # Fallback
            live_status = 'is_live'
        else:
            live_status = 'was_live'

        is_live = live_status == 'is_live'
        if is_live:
            self.report_warning('This VOD URL points to a currently live stream')

        m3u8_master_url = url_or_none(stream_data.get('playbackUrl'))
        if m3u8_master_url is not None:
            formats = self._extract_m3u8_formats(m3u8_master_url, video_id, 'mp4', m3u8_id='hls', live=is_live)
        else:
            self.report_warning('No playback URL found')
            formats = []

        start_ts = parse_iso8601(stream_data.get('startedAt'))
        end_ts = parse_iso8601(stream_data.get('finishedAt'))  # finishedAt is null when stream is live
        if start_ts is not None and end_ts is not None:
            duration = end_ts - start_ts
        elif not is_live and len(formats) >= 1:  # Fallback
            video_format = next((f for f in formats if f.get('vcodec', 'none') != 'none'), formats[0])
            duration = self._extract_m3u8_vod_duration(
                video_format['url'],
                video_id,
                note='Extracting VOD duration from HLS manifest',
            )
        else:
            duration = None

        category = traverse_obj(stream_data, ('subcategory', 'name'), expected_type=str)

        return {
            'id': video_id,
            'title': stream_data.get('title'),
            'description': stream_data.get('description'),
            'thumbnail': url_or_none(stream_data.get('thumbnailUrl')),
            'timestamp': start_ts,
            'channel': channel_data.get('name'),
            'channel_id': channel_data.get('channelId'),
            'channel_url': f'https://w.tv/{channel_name}',
            'channel_follower_count': int_or_none(channel_data.get('followers')),
            'channel_is_verified': bool_or_none(channel_data.get('verified')),
            'duration': duration,
            'view_count': int_or_none(stream_data.get('views')),
            'is_live': is_live,
            'live_status': live_status,
            'categories': [category] if category is not None else None,
            'tags': traverse_obj(stream_data, ('tags', ..., 'text'), expected_type=str),
            'formats': formats,
        }


class WTVStreamIE(WTVBaseIE):
    IE_NAME = 'wtv:stream'
    # The [A-Za-z0-9_]{1,25} part is from username validation login found in https://w.tv/_nuxt/CNQ95Wgc.js
    _VALID_URL = r'https?://(?:www\.)?w\.tv/(?P<channel>[A-Za-z0-9_]{1,25})/?(?:[?#].*)?$'

    _TESTS = [{
        'url': 'https://w.tv/ncs',
        'info_dict': {
            'id': '01a024af-d9e7-73db-9ca0-1f6ac0ee6f50',
            'title': r're:^24/7 Live NCS - No Copyright Songs Radio [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'ext': 'mp4',
            'description': '',
            'thumbnail': r're:^https://streams.w.tv/ivs/.*?/media/latest_thumbnail/thumb.jpg$',
            'timestamp': int,
            'upload_date': str,
            'channel': 'NCS',
            'channel_id': '019febc1-8340-770e-9dbe-c0447d36d16a',
            'channel_url': 'https://w.tv/ncs',
            'channel_follower_count': int,
            'channel_is_verified': bool,
            'view_count': int,
            'concurrent_view_count': int,
            'is_live': True,
            'live_status': 'is_live',
            'categories': ['Music'],
            'tags': ['ru', 'Music'],
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://w.tv/guitarnationlive',
        'info_dict': {
            'id': '01a02879-62da-77e9-9abb-6c96348e1148',
            'title': r're:^Rock 24/7 Music Channel [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'ext': 'mp4',
            'description': '',
            'thumbnail': r're:^https://streams.w.tv/ivs/.*?/media/latest_thumbnail/thumb.jpg$',
            'timestamp': int,
            'upload_date': str,
            'channel': 'GuitarNationLive',
            'channel_id': '019ff762-6a70-766e-a67e-d735442b8028',
            'channel_url': 'https://w.tv/guitarnationlive',
            'channel_follower_count': int,
            'channel_is_verified': False,  # unlikely to be verified
            'view_count': int,
            'concurrent_view_count': int,
            'is_live': True,
            'live_status': 'is_live',
            'categories': ['Music'],
            'tags': ['en', 'Music'],
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.w.tv/a',
        'only_matching': True,
    }, {
        'url': 'https://w.tv/abcdefghijklmnopqrstuvwxy',
        'only_matching': True,
    }, {
        'url': 'https://w.tv/User_Name_123',
        'only_matching': True,
    }, {
        'url': 'https://w.tv/testchannel/?query1=string2&query2=string3#fragment',
        'only_matching': True,
    }]

    # List of paths that don't correspond to a user page, but to a special webpage
    # Note that for some reserved paths there are actually exists valid users that only accesable with API
    _RESERVED_PATHS = {
        'navigation',
        'doc',
        'following',
        'search',
        'cabinet',
        'oauth',
        'settings',
        'tg-privacy-en',
        'tg-privacy-ru',
        'referrals',
    }

    def _real_extract(self, url):
        channel_name = self._match_valid_url(url).group('channel')

        if channel_name.lower() in self._RESERVED_PATHS:
            raise ExtractorError(f'"/{channel_name}" is a reserved path', expected=True)

        profile_data = self._download_json(
            f'https://profiles-service.w.tv/api/v1/profiles/by-nickname/{channel_name}',
            channel_name,
            note='Downloading channel profile information',
            expected_status=404,
        )
        if traverse_obj(profile_data, ('errors', 0, 'code')) == 'NICKNAME_NOT_FOUND':
            raise ExtractorError(f'User "{channel_name}" does not exist', expected=True)

        channel_id = traverse_obj(profile_data, ('profile', 'userId'), expected_type=str)
        if not channel_id:
            raise ExtractorError('Unable to extract channel ID from API response')

        channel_metadata = self._download_json(
            f'https://streams-search-service.w.tv/api/v1/channels/{channel_id}',
            channel_name,
            note='Downloading stream info',
        )
        outer_channel_data = channel_metadata.get('channel') or {}
        stream_data = outer_channel_data.get('liveStream') or {}
        channel_data = stream_data.get('channel') or {}

        # There exists multiple ways to extract the same data so we're trying all
        stream_id = outer_channel_data.get('liveStreamId') or stream_data.get('streamId') or channel_data.get('liveStreamId')

        stream_state = stream_data.get('state')
        if stream_state == 'started':
            is_live = True
        elif stream_state == 'finished':
            is_live = False
        elif outer_channel_data.get('live') or channel_data.get('live'):  # Fallback
            is_live = True
        else:
            is_live = False

        m3u8_master_url = url_or_none(stream_data.get('playbackUrl'))
        if not is_live or m3u8_master_url is None:
            raise UserNotLive(video_id=channel_name)

        formats = self._extract_m3u8_formats(m3u8_master_url, stream_id, 'mp4', m3u8_id='hls', live=True)

        category = traverse_obj(stream_data, ('subcategory', 'name'), expected_type=str)

        followers = int_or_none(outer_channel_data.get('followers'))
        if followers is None:
            followers = int_or_none(channel_data.get('followers'))

        return {
            'id': stream_id,
            'title': stream_data.get('title'),
            'description': stream_data.get('description'),
            'thumbnail': url_or_none(stream_data.get('thumbnailUrl')),
            'timestamp': parse_iso8601(stream_data.get('startedAt')),
            'channel': outer_channel_data.get('name') or channel_data.get('name'),
            'channel_id': channel_id,
            'channel_url': f'https://w.tv/{channel_name}',
            'channel_follower_count': followers,
            'channel_is_verified': bool_or_none(channel_data.get('verified')),
            'view_count': int_or_none(stream_data.get('views')),
            'concurrent_view_count': int_or_none(stream_data.get('viewers')),
            'is_live': True,
            'live_status': 'is_live',
            'categories': [category] if category is not None else None,
            'tags': traverse_obj(stream_data, ('tags', ..., 'text'), expected_type=str),
            'formats': formats,
        }
