from .common import InfoExtractor
from ..utils import url_or_none
from ..utils.traversal import traverse_obj


class SenIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?sen\.com/video/(?P<id>[0-9a-f-]+)'
    _TEST = {
        'url': 'https://www.sen.com/video/eef46eb1-4d79-4e28-be9d-bd937767f8c4',
        'md5': 'ff615aca9691053c94f8f10d96cd7884',
        'info_dict': {
            'id': 'eef46eb1-4d79-4e28-be9d-bd937767f8c4',
            'ext': 'mp4',
            'description': 'Florida, 28 Sep 2022',
            'title': 'Hurricane Ian',
            'tags': ['North America', 'Storm', 'Weather'],
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        api_data = self._download_json(f'https://api.sen.com/content/public/video/{video_id}', video_id)
        m3u8_url = (traverse_obj(api_data, (
            'data', 'nodes', lambda _, v: v['id'] == 'player', 'video', 'url', {url_or_none}, any))
            or f'https://vod.sen.com/videos/{video_id}/manifest.m3u8')

        return {
            'id': video_id,
            'formats': self._extract_m3u8_formats(m3u8_url, video_id, 'mp4'),
            **traverse_obj(api_data, ('data', 'nodes', lambda _, v: v['id'] == 'details', any, 'content', {
                'title': ('title', 'text', {str}),
                'description': ('descriptions', 0, 'text', {str}),
                'tags': ('badges', ..., 'text', {str}),
            })),
        }
