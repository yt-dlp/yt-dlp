from .common import InfoExtractor
from ..utils import int_or_none, parse_iso8601, traverse_obj


class IVXPlayerIE(InfoExtractor):
    _VALID_URL = r'ivxplayer:(v(?P<video_id>\d+))?(w(?P<widget_id>[\w-]+))?(k(?P<player_key>\w+))'
    _TESTS = [{
        'url': 'ivxplayer:v2366065w372d6c4c-8260k4a89dfe6bc8f002596b1dfbd600730b1',
        'info_dict': {
            'id': '2366065',
            'ext': 'mp4',
            'duration': 112,
            'upload_date': '20221204',
            'title': 'Film Indonesia di Disney Content Showcase Asia Pacific 2022',
            'timestamp': 1670151746,
        }
    }]

    # TODO: set change tempo.py to use this extractor
    # TODO: only use video_id and player key
    def _real_extract(self, url):
        video_id, widget_id, player_key = self._match_valid_url(url).group('video_id', 'widget_id', 'player_key')
        if (video_id is not None):
            json_data = self._download_json(
                f'https://ivxplayer.ivideosmart.com/prod/video/{video_id}?key={player_key}', video_id)
            
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                json_data['player']['video_url'], video_id) 

            return {
                'id': str(json_data['ivx']['id']),
                'title': traverse_obj(json_data, ('ivx', 'name')),
                'duration': int_or_none(traverse_obj(json_data, ('ivx', 'duration'))),
                'timestamp': parse_iso8601(traverse_obj(json_data, ('ivx', 'published_at'))),
                'formats': formats,
                'subtitles': subtitles,
            }