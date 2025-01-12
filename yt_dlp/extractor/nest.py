from .common import InfoExtractor
from ..utils import ExtractorError
from ..utils.traversal import traverse_obj


class NestIE(InfoExtractor):
    _VALID_URL = r'https?://video\.nest\.com/(?:embedded/)?live/(?P<id>\w+)'
    _EMBED_REGEX = [rf'<iframe[^>]+\bsrc=[\'"](?P<url>{_VALID_URL})']
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
    }, {
        'url': 'https://video.nest.com/live/4fvYdSo8AX',
        'only_matching': True,
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
        data = self._download_json(
            f'https://video.nest.com/api/dropcam/cameras.get_by_public_token?token={video_id}', video_id)
        item = traverse_obj(data, ('items', 0, {dict}))
        uuid = item.get('uuid')
        domain = item.get('live_stream_host')
        if not domain or not uuid:
            raise ExtractorError('Unable to construct playlist URL')
        m3u8 = f'https://{domain}/nexus_aac/{uuid}/playlist.m3u8?public={video_id}'

        thumb_domain = item.get('nexus_api_nest_domain_host')
        return {
            'id': video_id,
            **traverse_obj(item, {
                'description': ('description', {str}),
                'title': (('title', 'name', 'where'), {str}, filter, any),
                'alt_title': ('name', {str}),
                'location': ((('timezone', {lambda x: x.split('/')[1].replace('_', ' ')}), 'where'), {str}, filter, any),
            }),
            'thumbnail': f'https://{thumb_domain}/get_image?uuid={uuid}&public={video_id}' if thumb_domain else None,
            'availability': 'public' if item.get('is_public') else None,
            'formats': self._extract_m3u8_formats(m3u8, video_id, 'mp4', live=True),
            'is_live': True,
        }
