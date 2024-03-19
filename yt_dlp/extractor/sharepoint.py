import json
import urllib.parse

from .common import InfoExtractor
from .utils import determine_ext, int_or_none, url_or_none
from ..utils.traversal import traverse_obj


class SharePointIE(InfoExtractor):
    _VALID_URL = r'https?://[\w-]+\.sharepoint\.com/:v:/g/(?:[^/?#]+/){2}(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://lut-my.sharepoint.com/:v:/g/personal/juha_eerola_student_lab_fi/EUrAmrktb4ZMhUcY9J2PqMEBD_9x_l0DyYWVgAvp-TTOMw?e=ZpQOOw',
        'md5': '2950821d0d4937a0a76373782093b435',
        'info_dict': {
            'id': 'EUrAmrktb4ZMhUcY9J2PqMEBD_9x_l0DyYWVgAvp-TTOMw',
            'ext': 'mp4',
            'title': 'CmvpJST',
            'display_id': 'CmvpJST.mp4',
            'duration': 54.567,
            'thumbnail': r're:https://.+/thumbnail',
            'uploader_id': '8dcec565-a956-4b91-95e5-bacfb8bc015f',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        video = self._search_json(r'g_fileInfo\s*=', webpage, 'player config', video_id)

        parsed_url = urllib.parse.urlparse(video['.transformUrl'])
        base_media_url = urllib.parse.urlunparse(parsed_url._replace(
            path=urllib.parse.urljoin(f'{parsed_url.path}/', '../videomanifest'),
            query=urllib.parse.urlencode({
                **urllib.parse.parse_qs(parsed_url.query),
                'cTag': video['.ctag'],
                'action': 'Access',
                'part': 'index',
            }, doseq=True)))

        # Web player adds more params to the format URLs but we still get all formats without them
        formats = self._extract_mpd_formats(
            base_media_url, video_id, mpd_id='dash', query={'format': 'dash'}, fatal=False)
        for hls_type in ('hls', 'hls-vnext'):
            formats.extend(self._extract_m3u8_formats(
                base_media_url, video_id, 'mp4', m3u8_id=hls_type,
                query={'format': hls_type}, fatal=False, quality=-2))

        video_filename = video.get('name')
        if video_url := traverse_obj(video, ('downloadUrl', {url_or_none})):
            formats.append({
                'url': video_url,
                'ext': determine_ext(video.get('extension') or video_filename),
                'quality': 1,
                'format_id': 'source',
                'filesize': int_or_none(video.get('size')),
                'vcodec': 'none' if video.get('isAudio') is True else None,
            })

        return {
            'id': video_id,
            'formats': formats,
            'title': video.get('title') or video.get('displayName'),
            'display_id': video_filename,
            'uploader_id': video.get('authorId'),
            'duration': traverse_obj(
                video, ('MediaServiceFastMetadata', {json.loads}, 'media', 'duration', {lambda x: x / 10000000})),
            'thumbnail': url_or_none(video.get('thumbnailUrl')),
        }
