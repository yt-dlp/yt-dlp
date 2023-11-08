from .common import InfoExtractor
from .. import int_or_none
from ..utils import (
    traverse_obj,
)


class JupiterIE(InfoExtractor):
    _VALID_URL = r'https://jupiter\.err\.ee/(?P<id>\d+)/'
    _TESTS = [{
        'note': 'Siberi võmm S02E12',
        'url': 'https://jupiter.err.ee/1609145945/impulss',
        'md5': '1ff59d535310ac9c5cf5f287d8f91b2d',
        'info_dict': {
            'id': '4312',
            'ext': 'mp4',
            'title': 'Operatsioon "Öö"',
            'thumbnail': r're:https://.+\.jpg(?:\?c=\d+)?$',
            'description': 'md5:8ef98f38569d6b8b78f3d350ccc6ade8',
            'upload_date': '20170523',
            'timestamp': 1495567800,
            'series': 'Siberi võmm',
            'season': 'Season 2',
            'season_number': 2,
            'episode': 'Operatsioon "Öö"',
            'episode_number': 12,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        content_url = f"https://services.err.ee/api/v2/vodContent/getContentPageData?contentId={video_id}&rootId=3905"
        data = traverse_obj(self._download_json(content_url, video_id), 'data')
        formats = []
        for url in traverse_obj(data, ('mainContent', 'medias', ..., 'src', 'hls')):
            formats.extend(self._extract_m3u8_formats(url, video_id, 'mp4'))

        return {
            'id': video_id,
            'title': traverse_obj(data, ('mainContent', 'subHeading')),
            'description': traverse_obj(data, ('mainContent', 'lead')),
            'formats': formats,
            'timestamp': traverse_obj(data, ('mainContent', 'scheduleStart')),
            'series': traverse_obj(data, ('mainContent', 'heading')),
            'season_number': int_or_none(traverse_obj(data, ('mainContent', 'season'))),
            'episode': traverse_obj(data, ('mainContent', 'subHeading')),
            'episode_number': int_or_none(traverse_obj(data, ('mainContent', 'episode'))),
        }
