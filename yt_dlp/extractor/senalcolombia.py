from .common import InfoExtractor
from ..utils import traverse_obj


class SenalColombiaLiveIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?senalcolombia\.tv/(?P<id>senal-en-vivo)'

    _TESTS = [{
        'url': 'https://www.senalcolombia.tv/senal-en-vivo',
        'info_dict': {
            'id': 'senal-en-vivo',
            'title': 're:^Señal Colombia',
            'description': 'md5:799f16a401d97f40c33a2c6a3e2a507b',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'live_status': 'is_live',
            'ext': 'mp4',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        api_response = self._download_json(
            'https://cms.rtvcplay.co/api/v1/taxonomy_term/streaming/68', video_id)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            api_response['channel']['hls'], video_id, 'mp4')

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'is_live': True,
            **traverse_obj(api_response, {
                'title': 'title',
                'description': 'description',
                'thumbnail': ('channel', 'image', 'logo', 'path'),
            }),
        }
