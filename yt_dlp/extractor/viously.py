import base64
import re

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    int_or_none,
    parse_iso8601,
)
from ..utils.traversal import traverse_obj


class ViouslyIE(InfoExtractor):
    _VALID_URL = False
    _WEBPAGE_TESTS = [{
        'url': 'http://www.turbo.fr/videos-voiture/454443-turbo-du-07-09-2014-renault-twingo-3-bentley-continental-gt-speed-ces-guide-achat-dacia.html',
        'md5': '37a6c3381599381ff53a7e1e0575c0bc',
        'info_dict': {
            'id': 'F_xQzS2jwb3',
            'ext': 'mp4',
            'title': 'Turbo du 07/09/2014\xa0: Renault Twingo 3, Bentley Continental GT Speed, CES, Guide Achat Dacia...',
            'description': 'Turbo du 07/09/2014\xa0: Renault Twingo 3, Bentley Continental GT Speed, CES, Guide Achat Dacia...',
            'age_limit': 0,
            'upload_date': '20230328',
            'timestamp': 1680037507,
            'duration': 3716,
            'categories': ['motors'],
        }
    }]

    def _extract_from_webpage(self, url, webpage):
        viously_players = re.findall(r'<div[^>]*class="(?:[^"]*\s)?v(?:iou)?sly-player(?:\s[^"]*)?"[^>]*>', webpage)
        if not viously_players:
            return

        def custom_decode(text):
            STANDARD_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/='
            CUSTOM_ALPHABET = 'VIOUSLYABCDEFGHJKMNPQRTWXZviouslyabcdefghjkmnpqrtwxz9876543210+/='
            data = base64.b64decode(text.translate(str.maketrans(CUSTOM_ALPHABET, STANDARD_ALPHABET)))
            return data.decode('utf-8').strip('\x00')

        for video_id in traverse_obj(viously_players, (..., {extract_attributes}, 'id')):
            formats = self._extract_m3u8_formats(
                f'https://www.viously.com/video/hls/{video_id}/index.m3u8', video_id, fatal=False)
            if not formats:
                continue
            data = self._download_json(
                f'https://www.viously.com/export/json/{video_id}', video_id,
                transform_source=custom_decode, fatal=False)
            yield {
                'id': video_id,
                'formats': formats,
                **traverse_obj(data, ('video', {
                    'title': ('title', {str}),
                    'description': ('description', {str}),
                    'duration': ('duration', {int_or_none}),
                    'timestamp': ('iso_date', {parse_iso8601}),
                    'categories': ('category', 'name', {str}, {lambda x: [x] if x else None}),
                })),
            }
