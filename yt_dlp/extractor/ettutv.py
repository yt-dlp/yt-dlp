from .common import InfoExtractor
from ..utils import bool_or_none, traverse_obj, unified_timestamp, url_or_none


class EttuTvIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ettu\.tv/[^?#]+/playerpage/(?P<id>[0-9]+)'

    _TESTS = [{
        'url': 'https://www.ettu.tv/en-int/playerpage/1573849',
        'md5': '5874b7639a2aa866d1f6c3a4037c7c09',
        'info_dict': {
            'id': '1573849',
            'title': 'Ni Xia Lian - Shao Jieni',
            'description': 'ITTF Europe Top 16 Cup',
            'timestamp': 1677348600,
            'upload_date': '20230225',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'ext': 'mp4',
        },
    }, {
        'url': 'https://www.ettu.tv/en-int/playerpage/1573753',
        'md5': '1fc094bf96cf2d5ec0f434d3a6dec9aa',
        'info_dict': {
            'id': '1573753',
            'title': 'Qiu Dang - Jorgic Darko',
            'description': 'ITTF Europe Top 16 Cup',
            'timestamp': 1677423600,
            'upload_date': '20230226',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'ext': 'mp4',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        player_settings = self._download_json(
            f'https://www.ettu.tv/api/v3/contents/{video_id}/player-settings', video_id, query={
                'language': 'en',
                'showTitle': 'true',
                'device': 'desktop',
            })

        stream_response = self._download_json(player_settings['streamAccess'], video_id, data=b'')

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            stream_response['data']['stream'], video_id, 'mp4')

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(player_settings, {
                'title': 'title',
                'description': ('metaInformation', 'competition'),
                'thumbnail': ('image', {url_or_none}),
                'timestamp': ('date', {unified_timestamp}),
                'is_live': ('isLivestream', {bool_or_none}),
            }),
        }
