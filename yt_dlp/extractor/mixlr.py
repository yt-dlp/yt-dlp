from .common import InfoExtractor
from ..networking import HEADRequest
from ..utils import int_or_none, parse_iso8601, url_or_none, urlhandle_detect_ext
from ..utils.traversal import traverse_obj


class MixlrIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?P<username>[\w-]+)\.mixlr\.com/events/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://suncity-104-9fm.mixlr.com/events/4387115',
        'info_dict': {
            'id': '4387115',
            'ext': 'mp3',
            'title': r're:SUNCITY 104.9FM\'s live audio \d{4}-\d{2}-\d{2} \d{2}:\d{2}',
            'uploader': 'suncity-104-9fm',
            'like_count': int,
            'thumbnail': r're:https://imagecdn\.mixlr\.com/cdn-cgi/image/[^/?#]+/cd5b34d05fa2cee72d80477724a2f02e.png',
            'timestamp': 1751943773,
            'upload_date': '20250708',
            'release_timestamp': 1751943764,
            'release_date': '20250708',
            'live_status': 'is_live',
        },
    }, {
        'url': 'https://brcountdown.mixlr.com/events/4395480',
        'info_dict': {
            'id': '4395480',
            'ext': 'aac',
            'title': r're:Beats Revolution Countdown Episodio 461 \d{4}-\d{2}-\d{2} \d{2}:\d{2}',
            'description': 'md5:5cacd089723f7add3f266bd588315bb3',
            'uploader': 'brcountdown',
            'like_count': int,
            'thumbnail': r're:https://imagecdn\.mixlr\.com/cdn-cgi/image/[^/?#]+/c48727a59f690b87a55d47d123ba0d6d.jpg',
            'timestamp': 1752354007,
            'upload_date': '20250712',
            'release_timestamp': 1752354000,
            'release_date': '20250712',
            'live_status': 'is_live',
        },
    }, {
        'url': 'https://www.brcountdown.mixlr.com/events/4395480',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        username, event_id = self._match_valid_url(url).group('username', 'id')

        broadcast_info = self._download_json(
            f'https://api.mixlr.com/v3/channels/{username}/events/{event_id}', event_id)

        formats = []
        format_url = traverse_obj(
            broadcast_info, ('included', 0, 'attributes', 'progressive_stream_url', {url_or_none}))
        if format_url:
            urlh = self._request_webpage(
                HEADRequest(format_url), event_id, fatal=False, note='Checking stream')
            if urlh and urlh.status == 200:
                ext = urlhandle_detect_ext(urlh)
                if ext == 'octet-stream':
                    self.report_warning(
                        'The server did not return a valid file extension for the stream URL. '
                        'Assuming an mp3 stream; postprocessing may fail if this is incorrect')
                    ext = 'mp3'
                formats.append({
                    'url': format_url,
                    'ext': ext,
                    'vcodec': 'none',
                })

        release_timestamp = traverse_obj(
            broadcast_info, ('data', 'attributes', 'starts_at', {str}))
        if not formats and release_timestamp:
            self.raise_no_formats(f'This event will start at {release_timestamp}', expected=True)

        return {
            'id': event_id,
            'uploader': username,
            'formats': formats,
            'release_timestamp': parse_iso8601(release_timestamp),
            **traverse_obj(broadcast_info, ('included', 0, 'attributes', {
                'title': ('title', {str}),
                'timestamp': ('started_at', {parse_iso8601}),
                'concurrent_view_count': ('concurrent_view_count', {int_or_none}),
                'like_count': ('heart_count', {int_or_none}),
                'is_live': ('live', {bool}),
            })),
            **traverse_obj(broadcast_info, ('data', 'attributes', {
                'title': ('title', {str}),
                'description': ('description', {str}),
                'timestamp': ('started_at', {parse_iso8601}),
                'concurrent_view_count': ('concurrent_view_count', {int_or_none}),
                'like_count': ('heart_count', {int_or_none}),
                'thumbnail': ('artwork_url', {url_or_none}),
                'uploader_id': ('broadcaster_id', {str}),
            })),
        }


class MixlrRecoringIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?P<username>[\w-]+)\.mixlr\.com/recordings/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://biblewayng.mixlr.com/recordings/2375193',
        'info_dict': {
            'id': '2375193',
            'ext': 'mp3',
            'title': "God's Jewels and Their Resting Place Bro. Adeniji",
            'description': 'Preached February 21, 2024 in the evening',
            'uploader_id': '8659190',
            'duration': 10968,
            'thumbnail': r're:https://imagecdn\.mixlr\.com/cdn-cgi/image/[^/?#]+/ceca120ef707f642abeea6e29cd74238.jpg',
            'timestamp': 1708544542,
            'upload_date': '20240221',
        },
    }]

    def _real_extract(self, url):
        username, recording_id = self._match_valid_url(url).group('username', 'id')

        recording_info = self._download_json(
            f'https://api.mixlr.com/v3/channels/{username}/recordings/{recording_id}', recording_id)

        return {
            'id': recording_id,
            **traverse_obj(recording_info, ('data', 'attributes', {
                'ext': ('file_format', {str}),
                'url': ('url', {url_or_none}),
                'title': ('title', {str}),
                'description': ('description', {str}),
                'timestamp': ('created_at', {parse_iso8601}),
                'duration': ('duration', {int_or_none}),
                'thumbnail': ('artwork_url', {url_or_none}),
                'uploader_id': ('user_id', {str}),
            })),
        }
