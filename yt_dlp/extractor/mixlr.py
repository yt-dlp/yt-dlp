import re

from .common import InfoExtractor


class MixlrIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?P<username>[\w-]+)\.mixlr\.com/events/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://suncity-104-9fm.mixlr.com/events/4261962',
        'info_dict': {
            'id': '4261962',
            'title': re.compile(r'.+'),
            'description': re.compile(r'.+'),
            'ext': 'mp3',
            'is_live': True,
            'uploader': 'suncity-104-9fm',
        },
        'skip': 'Live broadcast may not be available',
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        username = mobj.group('username')
        event_id = mobj.group('id')

        api_url = f'https://apicdn.mixlr.com/v3/channel_view/{username}'
        channel_info = self._download_json(api_url, event_id)
        user_data = channel_info.get('data', {}).get('attributes', {})

        broadcast_data = None
        event_data = None
        included = channel_info.get('included', [])
        for item in included:
            if item.get('type') == 'broadcast':
                broadcast_data = item.get('attributes', {})
            elif item.get('type') == 'event' and item.get('id') == event_id:
                event_data = item.get('attributes', {})

            if broadcast_data and event_data:
                break

        if not broadcast_data or not broadcast_data.get('live', False):
            self.raise_no_formats('No active broadcast found', expected=True)
        if not event_data:
            self.raise_no_formats('No event data found', expected=True)

        streaming_url = broadcast_data.get('progressive_stream_url')
        title = event_data.get('title') or f'Mixlr broadcast by {username}'
        description = event_data.get('description') or broadcast_data.get('description') or ''

        formats = []
        if streaming_url:
            formats.append({
                'url': streaming_url,
                'format_id': 'http',
                'ext': 'mp3',
                'vcodec': 'none',
            })

        if not formats:
            self.raise_no_formats('No formats found', expected=True)

        return {
            'id': event_id,
            'title': title,
            'description': description,
            'uploader': username,
            'uploader_id': user_data.get('id'),
            'uploader_url': f'https://{username}.mixlr.com',
            'thumbnail': user_data.get('avatar_full_url') or user_data.get('avatar_url'),
            'is_live': broadcast_data.get('live', True),
            'formats': formats,
        }
