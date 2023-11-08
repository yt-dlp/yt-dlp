from .common import InfoExtractor
from .. import int_or_none
from ..utils import (
    traverse_obj,
)


class JupiterIE(InfoExtractor):
    _VALID_URL = r'https://jupiter\.err\.ee/(?P<id>\d+)/'
    _TESTS = [{
        'note': 'S01E06: Impulss',
        'url': 'https://jupiter.err.ee/1609145945/impulss',
        'md5': '1ff59d535310ac9c5cf5f287d8f91b2d',
        'info_dict': {
            'id': '1609145945',
            'ext': 'mp4',
            'title': 'Loteriipilet hooldekodusse',
            'description': 'md5:d1770e868afffd5d42b886283574941e',
            'upload_date': '20231107',
            'timestamp': 1699380000,
            'series': 'Impulss',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Loteriipilet hooldekodusse',
            'episode_number': 6,
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
