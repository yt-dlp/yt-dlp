from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_iso8601,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class ErocastIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?erocast\.me/track/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://erocast.me/track/9787/f',
        'md5': 'af63b91f5f231096aba54dd682abea3b',
        'info_dict': {
            'id': '9787',
            'title': '[F4M] Your roommate, who is definitely not possessed by an alien, suddenly wants to fuck you',
            'url': 'https://erocast.s3.us-east-2.wasabisys.com/1220419/track.m3u8',
            'ext': 'm4a',
            'age_limit': 18,
            'release_timestamp': 1696178652,
            'release_date': '20231001',
            'modified_timestamp': int,
            'modified_date': str,
            'description': 'ExtraTerrestrial Tuesday!',
            'uploader': 'clarissaisshy',
            'uploader_id': '8113',
            'uploader_url': 'https://erocast.me/clarissaisshy',
            'thumbnail': 'https://erocast.s3.us-east-2.wasabisys.com/1220418/conversions/1696179247-lg.jpg',
            'duration': 2307,
            'view_count': int,
            'comment_count': int,
            'webpage_url': 'https://erocast.me/track/9787/f4m-your-roommate-who-is-definitely-not-possessed-by-an-alien-suddenly-wants-to-fuck-you',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        data = self._search_json(
            rf'<script>\s*var song_data_{video_id}\s*=', webpage, 'data', video_id, end_pattern=r'</script>')

        return {
            'id': video_id,
            'formats': self._extract_m3u8_formats(
                data.get('file_url') or data['stream_url'], video_id, 'm4a', m3u8_id='hls'),
            'age_limit': 18,
            **traverse_obj(data, {
                'title': ('title', {str}),
                'description': ('description', {str}),
                'release_timestamp': ('created_at', {parse_iso8601}),
                'modified_timestamp': ('updated_at', {parse_iso8601}),
                'uploader': ('user', 'name', {str}),
                'uploader_id': ('user', 'id', {str_or_none}),
                'uploader_url': ('user', 'permalink_url', {url_or_none}),
                'thumbnail': ('artwork_url', {url_or_none}),
                'duration': ('duration', {int_or_none}),
                'view_count': ('plays', {int_or_none}),
                'comment_count': ('comment_count', {int_or_none}),
                'webpage_url': ('permalink_url', {url_or_none}),
            }),
        }
