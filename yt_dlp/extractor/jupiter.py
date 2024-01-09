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
            'description': 'md5:fa8a2ed0cdccb130211513443ee4d571',
            'upload_date': '20231107',
            'timestamp': 1699380000,
            'series': 'Impulss',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Loteriipilet hooldekodusse',
            'episode_number': 6,
            'series_id': 1609108187,
            'release_year': 2023,
            'episode_id': 1609145945,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        content_url = f"https://services.err.ee/api/v2/vodContent/getContentPageData?contentId={video_id}"
        data = traverse_obj(self._download_json(content_url, video_id), ('data', 'mainContent'))

        formats, subtitles = [], {}
        for url in traverse_obj(data, ('medias', ..., 'src', 'hls')):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(url, video_id, 'mp4')
            formats.extend(fmts)
            subtitles = self._merge_subtitles(subtitles, subs)

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(data, {
                'title': 'subHeading',
                'description': 'lead',
                'release_year': ('year', {int_or_none}),
                'timestamp': 'scheduleStart',
                'series': 'heading',
                'series_id': ('rootContentId', {int_or_none}),
                'episode': 'subHeading',
                'season_number': ('season', {int_or_none}),
                'episode_number': ('episode', {int_or_none}),
                'episode_id': ('id', {int_or_none}),
            }),
        }
