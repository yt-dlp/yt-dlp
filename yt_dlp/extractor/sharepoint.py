import json

from urllib.parse import (
    parse_qs,
    urlencode,
    urljoin,
    urlparse,
    urlunparse,
)

from .common import InfoExtractor
from ..utils.traversal import traverse_obj


class SharePointIE(InfoExtractor):
    _VALID_URL = r'https?://[\w-]+\.sharepoint\.com/:v:/g/(?:[^/?#]+/){2}(?P<id>[^/?#]+)'

    _TESTS = [
        {
            'url': 'https://lut-my.sharepoint.com/:v:/g/personal/juha_eerola_student_lab_fi/EUrAmrktb4ZMhUcY9J2PqMEBD_9x_l0DyYWVgAvp-TTOMw?e=ZpQOOw',
            'info_dict': {
                'id': 'EUrAmrktb4ZMhUcY9J2PqMEBD_9x_l0DyYWVgAvp-TTOMw',
                'ext': 'unknown_video',
                'title': 'CmvpJST.mp4',
                'duration': 54.567,
            },
            'params': {'skip_download': 'm3u8'},
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        video = self._search_json(r'g_fileInfo\s*=', webpage, 'player config', video_id)

        parsed_url = urlparse(video['.transformUrl'])
        base_media_url = urlunparse(parsed_url._replace(
            path=urljoin(f'{parsed_url.path}/', '../videomanifest'),
            query=urlencode(
                {
                    **parse_qs(parsed_url.query),
                    'cTag': video['.ctag'],
                    'action': 'Access',
                    'part': 'index',
                }, doseq=True,
            ),
        ))

        # The player is configured with a number of options that are then added to the format URLs,
        # but we always get all formats back no matter what options we send
        hls_formats = self._extract_m3u8_formats(
            f'{base_media_url}&format=hls', video_id, m3u8_id='hls', fatal=False)
        hls_formats.extend(self._extract_m3u8_formats(
            f'{base_media_url}&format=hls-vnext', video_id, m3u8_id='hls-vnext', fatal=False))
        for hls_format in hls_formats:
            hls_format['quality'] = -2
        formats = self._extract_mpd_formats(
            f'{base_media_url}&format=dash', video_id, mpd_id='dash', fatal=False)
        formats.extend(hls_formats)

        return {
            'id': video_id,
            'formats': formats,
            'title': video.get('name'),
            'duration': traverse_obj(
                video, ('MediaServiceFastMetadata', {json.loads}, 'media', 'duration', {lambda x: x / 10000000})
            ),
        }
