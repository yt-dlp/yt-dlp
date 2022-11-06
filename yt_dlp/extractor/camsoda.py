import random

from .common import InfoExtractor
from ..utils import ExtractorError, traverse_obj


class CamsodaIE(InfoExtractor):
    _VALID_URL = r'https?://www\.camsoda\.com/(?P<id>[0-9A-Za-z-]+)'
    _TESTS = [{
        'url': 'https://www.camsoda.com/lizzhopf',
        'info_dict': {
            'id': 'lizzhopf',
            'ext': 'mp4',
            'title': 'lizzhopf (lizzhopf) Nude on Cam. Free Live Sex Chat Room - CamSoda',
            'description': str,
            'is_live': True,
            'age_limit': 18,
        },
        'skip': 'Room is offline',
    }]

    _ROOM_OFFLINE = 'Model is offline.'
    _ROOM_PRIVATE = 'Model is in private show.'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        user_id = 'guest_%u' % random.randrange(10000, 99999)
        webpage = self._download_webpage(url, video_id, headers=self.geo_verification_headers())

        data = self._download_json(
            f'https://camsoda.com/api/v1/video/vtoken/{video_id}?username={user_id}',
            video_id, headers=self.geo_verification_headers())
        if not data:
            raise ExtractorError('Unable to find configuration for stream.')

        private_servers = traverse_obj(data, ('private_servers'), expected_type=list)
        if private_servers:
            raise ExtractorError(self._ROOM_PRIVATE, expected=True)

        stream_name = traverse_obj(data, ('stream_name'), expected_type=str)
        if not stream_name:
            raise ExtractorError(self._ROOM_OFFLINE, expected=True)

        token = traverse_obj(data, ('token'), expected_type=str)

        for server in traverse_obj(data, ('edge_servers'), expected_type=list):
            formats = self._extract_m3u8_formats(
                f'https://{server}/{stream_name}_v1/index.m3u8?token={token}',
                video_id, ext='mp4', m3u8_id='hls', fatal=False, live=True)
            if formats:
                break

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': video_id,
            'description': self._html_search_meta('description', webpage, default=None),
            'is_live': True,
            'formats': formats,
            # Camsoda does not declare the RTA meta-tag
            'age_limit': 18,
        }
