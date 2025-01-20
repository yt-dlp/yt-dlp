from .common import InfoExtractor
from ..utils import ExtractorError, float_or_none, update_url_query, url_or_none
from ..utils.traversal import traverse_obj


class NestIE(InfoExtractor):
    _VALID_URL = r'https?://video\.nest\.com/(?:embedded/)?live/(?P<id>\w+)'
    _EMBED_REGEX = [rf'<iframe [^>]*\bsrc=[\'"](?P<url>{_VALID_URL})']
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
        item = self._download_json(
            'https://video.nest.com/api/dropcam/cameras.get_by_public_token',
            video_id, query={'token': video_id})['items'][0]
        uuid = item.get('uuid')
        stream_domain = item.get('live_stream_host')
        if not stream_domain or not uuid:
            raise ExtractorError('Unable to construct playlist URL')

        thumb_domain = item.get('nexus_api_nest_domain_host')
        return {
            'id': video_id,
            **traverse_obj(item, {
                'description': ('description', {str}),
                'title': (('title', 'name', 'where'), {str}, filter, any),
                'alt_title': ('name', {str}),
                'location': ((('timezone', {lambda x: x.split('/')[1].replace('_', ' ')}), 'where'), {str}, filter, any),
            }),
            'thumbnail': update_url_query(
                f'https://{thumb_domain}/get_image',
                {'uuid': uuid, 'public': video_id}) if thumb_domain else None,
            'availability': self._availability(is_private=item.get('is_public') is False),
            'formats': self._extract_m3u8_formats(
                f'https://{stream_domain}/nexus_aac/{uuid}/playlist.m3u8',
                video_id, 'mp4', live=True, query={'public': video_id}),
            'is_live': True,
        }


class NestClipIE(InfoExtractor):
    _VALID_URL = r'https?://video\.nest\.com/(?:embedded/)?clip/(?P<id>\w+)'
    _EMBED_REGEX = [rf'<iframe [^>]*\bsrc=[\'"](?P<url>{_VALID_URL})']
    _TESTS = [{
        'url': 'https://video.nest.com/clip/f34c9dd237a44eca9a0001af685e3dff',
        'info_dict': {
            'id': 'f34c9dd237a44eca9a0001af685e3dff',
            'ext': 'mp4',
            'title': 'NestClip video #f34c9dd237a44eca9a0001af685e3dff',
            'thumbnail': 'https://clips.dropcam.com/f34c9dd237a44eca9a0001af685e3dff.jpg',
            'timestamp': 1735413474.468,
            'upload_date': '20241228',
        },
    }, {
        'url': 'https://video.nest.com/embedded/clip/34e0432adc3c46a98529443d8ad5aa76',
        'info_dict': {
            'id': '34e0432adc3c46a98529443d8ad5aa76',
            'ext': 'mp4',
            'title': 'Shootout at Veterans Boulevard at Fleur De Lis Drive',
            'thumbnail': 'https://clips.dropcam.com/34e0432adc3c46a98529443d8ad5aa76.jpg',
            'upload_date': '20230817',
            'timestamp': 1692262897.191,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._download_json(
            'https://video.nest.com/api/dropcam/videos.get_by_filename', video_id,
            query={'filename': f'{video_id}.mp4'})
        return {
            'id': video_id,
            **traverse_obj(data, ('items', 0, {
                'title': ('title', {str}),
                'thumbnail': ('thumbnail_url', {url_or_none}),
                'url': ('download_url', {url_or_none}),
                'timestamp': ('start_time', {float_or_none}),
            })),
        }
