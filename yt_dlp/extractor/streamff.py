# coding: utf-8
from .common import InfoExtractor
from ..utils import int_or_none, parse_iso8601


class StreamFFIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?streamff\.com/v/(?P<id>[a-zA-Z0-9]+)'
    _API_URL = 'https://streamff.com/api'

    _TESTS = [{
        'url': 'https://streamff.com/v/55cc94',
        'md5': '8745a67bb5e5c570738efe7983826370',
        'info_dict': {
            'id': '55cc94',
            'ext': 'mp4',
            'title': '55cc94',
            'timestamp': 1634764643,
            'upload_date': '20211020'
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        api_path = f'/videos/{video_id}'

        """"
        {
            'views': 94,
            'uploaded': True,
            'publicURl': '55cc94',
            'date': '2021-10-20T21:17:23.887Z',
            'name': '55cc94',
            'videoLink': '/uploads/55cc94.mp4'
        }
        """
        json_data = self._download_json(self._API_URL + api_path, video_id)
        return {
            'id': video_id,
            'title': json_data.get('name') or video_id,
            'url': 'https://streamff.com/%s' % json_data['videoLink'],
            'view_count': int_or_none(json_data.get('views')),
            'timestamp': parse_iso8601(json_data.get('date')),
        }
