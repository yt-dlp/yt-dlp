import json

from .common import InfoExtractor
from ..utils import (
    float_or_none,
    traverse_obj,
)


class SharePointIE(InfoExtractor):
    _VALID_URL = r'https?://[^\.]+\.sharepoint\.com/:v:/g/[^/]+/[^/]+/(?P<id>[^/?]+)'

    _TESTS = [
        {
            'url': 'https://lut-my.sharepoint.com/:v:/g/personal/juha_eerola_student_lab_fi/EUrAmrktb4ZMhUcY9J2PqMEBD_9x_l0DyYWVgAvp-TTOMw?e=ZpQOOw',
            'info_dict': {
                'id': 'EUrAmrktb4ZMhUcY9J2PqMEBD_9x_l0DyYWVgAvp-TTOMw',
                'ext': 'mp4',
                'title': 'CmvpJST.mp4',
                'duration': 54.567,
            },
            'params': {'skip_download': 'm3u8'}
        },
    ]

    def _parse_mediapackage(self, video, video_id):
        formats = []

        base_media_url = video['.transformUrl'].replace('/thumbnail?', '/videomanifest?')
        base_media_url += f"&cTag={video['.ctag']}&action=Access&part=index"

        metadata = json.loads(video.get('MediaServiceFastMetadata'))

        # Normally the player is configured with all possible options added to the format URLs,
        # but we always get all formats back no matter what settings you send
        formats.extend(self._extract_mpd_formats(
            f"{base_media_url}&format=dash", video_id, mpd_id='dash', fatal=False
        ))
        formats.extend(self._extract_m3u8_formats(
            f"{base_media_url}&format=hls", video_id, m3u8_id='hls', entry_protocol='m3u8_native',
            fatal=False
        ))
        # HLSv6
        formats.extend(self._extract_m3u8_formats(
            f"{base_media_url}&format=hls-vnext", video_id, m3u8_id='hls-vnext',
            entry_protocol='m3u8_native', fatal=False
        ))

        # Most formats are found multiple times, we remove the occurrences without metadata
        formats = [x for x in formats if x.get('ext') is not None]

        return {
            'id': video_id,
            'formats': formats,
            'title': video.get('name'),
            'duration': float_or_none(traverse_obj(metadata, ('media', 'duration')), scale=10000000),
        }

    def _real_extract(self, url):
        video_id = self._match_valid_url(url).group('id')
        webpage = self._download_webpage(url, video_id)

        player_config = self._search_json(r'g_fileInfo\s*=', webpage, 'player config', video_id)

        return self._parse_mediapackage(player_config, video_id)
