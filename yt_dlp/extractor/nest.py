import datetime as dt

from .common import InfoExtractor
from ..utils import ExtractorError


class NestIE(InfoExtractor):
    _VALID_URL = r'^https?://video\.nest\.com/embedded/live/(?P<id>[A-Za-z0-9]+)'
    _EMBED_REGEX = [r'<iframe[^>]+?src=(["\'])(?P<url>(?:https?:)?//video\.nest\.com/embedded/live/.+)\1']
    _TESTS = [{
        'url': 'https://video.nest.com/embedded/live/4fvYdSo8AX?autoplay=0',
        'info_dict': {
            'id': '4fvYdSo8AX',
            'ext': 'mp4',
            'title': 'startswith:Outside ',
            'alt_title': 'Outside',
            'description': '<null>',
            'location': 'Los Angeles',
            'availability': 'public',
            'thumbnail': r're:https?://',
            'live_status': 'is_live',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://www.pacificblue.biz/noyo-harbor-webcam/',
        'info_dict': {
            'id': '4fvYdSo8AX',
            'ext': 'mp4',
            'title': 'startswith:Outside ',
            'alt_title': 'Outside',
            'description': '<null>',
            'location': 'Los Angeles',
            'availability': 'public',
            'thumbnail': r're:https?://',
            'live_status': 'is_live',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        now = dt.datetime.now().strftime('%s')
        api = f'https://video.nest.com/api/dropcam/cameras.get_by_public_token?token={video_id}&_={now}'
        data = self._download_json(api, video_id)
        items = data.get('items')
        item = items[0] if items else {}
        titles = [item.get('title'), item.get('name'), item.get('where')]
        titles = [title for title in titles if title]
        title = titles.pop(0) if titles else None
        alt_title = titles.pop(0) if titles else None
        timezone = item.get('timezone', '')
        timezone = timezone.split('/')
        timezone = timezone[1] if len(timezone) > 1 else None
        timezone = timezone.replace('_', ' ')
        location = timezone or item.get('where')
        uuid = item.get('uuid')
        domain = item.get('live_stream_host')
        if not domain or not uuid:
            raise ExtractorError('Unable to construct playlist URL')
        m3u8 = f'https://{domain}/nexus_aac/{uuid}/playlist.m3u8?public={video_id}'
        domain = item.get('nexus_api_nest_domain_host')
        thumb = f'https://{domain}/get_image?uuid={uuid}&width=540&public={video_id}' if domain else None
        return {
            'id': video_id,
            'title': title,
            'alt_title': alt_title,
            'description': item.get('description'),
            'location': location,
            'thumbnail': thumb,
            'availability': 'public' if item.get('is_public') else None,
            'formats': self._extract_m3u8_formats(m3u8, video_id, 'mp4', live=True),
            'is_live': True,
        }
