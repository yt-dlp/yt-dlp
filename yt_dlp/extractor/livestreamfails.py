# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import parse_iso8601


class LivestreamFailsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?livestreamfails\.com/(?:post|clip)/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'https://livestreamfails.com/clip/18645',
        'md5': '4438ab40c35a0df2553ae30f941d6cd4',
        'info_dict': {
            'id': '18645',
            'ext': 'mp4',
            'title': 'Zuckerberg gets Jebaited',
            'thumbnail': r're:^https?://.*\.(jpe?g|png|webp)$',
            'timestamp': 1523391367,
            'upload_date': '20180410'
        }
    }

    _DEFAULT_API_URL = 'https://api.livestreamfails.com'
    _DEFAULT_VIDEO_SERVER = 'https://livestreamfails-video-prod.b-cdn.net'
    _DEFAULT_IMAGE_SERVER = 'https://livestreamfails-image-prod.b-cdn.net'

    def _extract_config_url(self, prop, script, name, default):
        url = self._search_regex(fr'(["\']?){prop}\1:\s*(["\'])(?P<url>.+?)\2', script, name, fatal=False, group='url')

        if url is None:
            self.report_warning(f'Falling back to default {name}')
            return default

        return url.strip('/')

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        script_url = self._search_regex(r'<script[^>]+src=(["\'])/(?P<script>.+?/2\.[a-zA-Z0-9]+\.chunk\.js)\1',
                                        webpage, 'config script URL', fatal=False, group='script')

        if script_url is not None:
            script = self._download_webpage(f'https://livestreamfails.com/{script_url}', video_id, 'Downloading config script')
            api_url = self._extract_config_url('REACT_APP_API_URL', script, 'base API URL', self._DEFAULT_API_URL)
            video_server = self._extract_config_url('REACT_APP_MEDIA_VIDEO_URL', script, 'video server URL', self._DEFAULT_VIDEO_SERVER)
            image_server = self._extract_config_url('REACT_APP_MEDIA_IMAGE_URL', script, 'image server URL', self._DEFAULT_IMAGE_SERVER)
        else:
            self.report_warning('Falling back to default API and media server URLs')
            api_url = self._DEFAULT_API_URL
            video_server = self._DEFAULT_VIDEO_SERVER
            image_server = self._DEFAULT_IMAGE_SERVER

        metadata = self._download_json(f'{api_url}/clip/{video_id}', video_id)
        video_name = metadata.get('videoId')
        thumbnail_name = metadata.get('imageId')

        return {
            'id': video_id,
            'url': f'{video_server}/video/{video_name}',
            'title': metadata.get('label'),
            'thumbnail': f'{image_server}/image/{thumbnail_name}',
            'timestamp': parse_iso8601(metadata.get('createdAt'))
        }
