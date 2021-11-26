# coding: utf-8
from .common import InfoExtractor
from ..utils import int_or_none, parse_iso8601


class StreamFFIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?streamff\.com/v/(?P<id>[a-zA-Z0-9]+)'

    _TESTS = [{
        'url': 'https://streamff.com/v/55cc94',
        'md5': '8745a67bb5e5c570738efe7983826370',
        'info_dict': {
            'id': '55cc94',
            'ext': 'mp4',
            'title': '55cc94',
            'timestamp': 1634764643,
            'upload_date': '20211020',
            'view_count': int,
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        json_data = self._download_json(f'https://streamff.com/api/videos/{video_id}', video_id)
        return {
            'id': video_id,
            'title': json_data.get('name') or video_id,
            'url': 'https://streamff.com/%s' % json_data['videoLink'],
            'view_count': int_or_none(json_data.get('views')),
            'timestamp': parse_iso8601(json_data.get('date')),
        }
