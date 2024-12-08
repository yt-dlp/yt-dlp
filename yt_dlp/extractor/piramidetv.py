from .common import InfoExtractor
from ..utils import unified_timestamp
from ..utils.traversal import traverse_obj


class PiramideTVIE(InfoExtractor):
    _VALID_URL = [
        r'https?://piramide\.tv/video/(?P<video_id>[^/]+)',
    ]
    _TESTS = [{
        'url': 'https://piramide.tv/video/wcYn6li79NgN',
        'info_dict': {
            'id': 'wcYn6li79NgN',
            'ext': 'mp4',
            'channel': 'ARTA GAME',
            'channel_id': 'arta_game',
            'thumbnail_url': 'https://cdn.jwplayer.com/v2/media/cnEdGp5X/thumbnails/rHAaWfP7.jpg',
            'title': 'ACEPTO TENER UN BEBE CON MI NOVIA…? | Parte 1',
            'timestamp': 1703434976,
            'upload_date': '20231224',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_valid_url(url).group('video_id')
        json_data = self._download_json(
            f'https://hermes.piramide.tv/video/data/{video_id}', video_id)['video']

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            f'https://cdn.piramide.tv/video/{video_id}/manifest.m3u8', video_id,
        )

        return {
            'id': video_id,
            'display_id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(json_data, {
                'title': 'title',
                'thumbnail_url': ('media', 'thumbnail'),
                'channel': ('channel', 'name'),
                'channel_id': ('channel', 'id'),
                'timestamp': ('date', {unified_timestamp}),
            }),
        }
