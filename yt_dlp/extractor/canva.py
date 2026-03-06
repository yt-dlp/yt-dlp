import json
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    traverse_obj,
    url_or_none,
)


class CanvaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?canva\.com/design/(?P<id>[^/]+)/(?P<token>[^/]+)/(?:watch|view|edit)'
    _TESTS = [{
        'url': 'https://www.canva.com/design/DAHCj8E06us/zCnY6t5K6kLGjZbF_ip0Jg/watch',
        'info_dict': {
            'id': 'DAHCj8E06us',
            'ext': 'mp4',
            'title': 'Black and White Simple Animated Photo Collage Frame Mobile Video',
            'thumbnail': r're:^https?://.+/screen',
        },
        'skip': 'Requires cookies',
    }, {
        'url': 'https://www.canva.com/design/DAHCoH4To0w/XUSdhfH274kIWC8SBYGDeQ/watch',
        'info_dict': {
            'id': 'DAHCoH4To0w',
            'ext': 'mp4',
            'title': 'Untitled design',
            'thumbnail': r're:^https?://.+/screen',
        },
        'skip': 'Requires cookies',
    }, {
        'url': 'https://www.canva.com/design/DAHCoEX6EYE/o2rkSSBzqNZFqNCYPUJlQw/watch',
        'info_dict': {
            'id': 'DAHCoEX6EYE',
            'ext': 'mp4',
            'title': 'Light Yellow Light Orange Video-centric Place Video Background',
            'thumbnail': r're:^https?://.+/screen',
        },
        'skip': 'Requires cookies',
    }]

    _JSON_HIJACK_RE = r'''^.*?while\s*\(\s*1\s*\)\s*;\s*</x>//'''
    _POLLING_INTERVAL = 3
    _POLLING_MAX_ATTEMPTS = 30

    def _strip_json_hijack(self, data):
        return re.sub(self._JSON_HIJACK_RE, '', data)

    def _real_extract(self, url):
        video_id, token = self._match_valid_url(url).group('id', 'token')
        webpage = self._download_webpage(url, video_id, impersonate=True)

        if 'permission' in webpage.lower() or 'Request access' in webpage:
            raise ExtractorError(
                'You do not have permission to access this design. '
                'The owner must share it as "Anyone with the link can view"',
                expected=True)

        title = self._og_search_title(webpage, default=None) or self._html_extract_title(webpage)
        thumbnail = self._og_search_thumbnail(webpage, default=None)

        dimensions = self._search_regex(
            r'"C"\s*:\s*\{\s*"A"\s*:\s*(\d+(?:\.\d+)?)\s*,\s*"B"\s*:\s*(\d+(?:\.\d+)?)\s*,\s*"C"\s*:\s*"D"\s*\}',
            webpage, 'dimensions', default=None, group=(1, 2))
        if dimensions:
            width, height = int_or_none(float_or_none(dimensions[0])), int_or_none(float_or_none(dimensions[1]))
        else:
            width, height = 1920, 1080

        # passing version -1 seems to bypass any version conflict errors
        export_data = self._download_json(
            'https://www.canva.com/_ajax/export', video_id,
            'Initiating video export', 'Failed to initiate export',
            query={'version': '2', 'inline': 'false'},
            data=json.dumps({
                'priority': 'HIGH',
                'pollable': True,
                'useSkiaRenderer': True,
                'renderSpec': {
                    'content': {
                        'schema': 'web-2',
                        'type': 'DOCUMENT_REFERENCE',
                        'id': video_id,
                        'version': -1,
                        'prefetch': True,
                        'extension': token,
                    },
                    'mediaQuality': 'PRINT',
                    'mediaDpi': 96,
                    'preferWatermarkedMedia': True,
                    'pages': [1],
                },
                'outputSpecs': [{
                    'destination': {'type': 'DOWNLOAD'},
                    'pages': [1],
                    'type': 'MP4',
                    'width': width,
                    'height': height,
                }],
            }, separators=(',', ':')).encode(),
            headers={'Content-Type': 'application/json'},
            transform_source=self._strip_json_hijack,
            impersonate=True)

        export_id = traverse_obj(export_data, ('export', 'exportIdentifier', {str}))
        if not export_id:
            raise ExtractorError('Failed to get export identifier from Canva API')

        for attempt in range(1, self._POLLING_MAX_ATTEMPTS + 1):
            self._sleep(self._POLLING_INTERVAL, video_id,
                        f'%(video_id)s: Waiting for export to complete (attempt {attempt}/{self._POLLING_MAX_ATTEMPTS})')

            poll_data = self._download_json(
                f'https://www.canva.com/_ajax/export/{export_id}', video_id,
                f'Polling export status (attempt {attempt})',
                query={'attachment': ''},
                transform_source=self._strip_json_hijack,
                impersonate=True)

            status = traverse_obj(poll_data, ('export', 'status', {str}))
            if status == 'COMPLETE':
                video_url = traverse_obj(poll_data, (
                    'export', 'output', 'exportBlobs', 0, 'url', {url_or_none})) or traverse_obj(poll_data, (
                        'export', 'exportBlobs', 0, 'url', {url_or_none}))

                if not video_url:
                    raise ExtractorError('Export completed but no download URL found')

                return {
                    'id': video_id,
                    'title': traverse_obj(poll_data, ('export', 'output', 'title', {str})) or title,
                    'url': video_url,
                    'ext': 'mp4',
                    'thumbnail': thumbnail,
                    'width': width,
                    'height': height,
                }

            if status == 'FAILED':
                raise ExtractorError('Canva export failed on the server side')

        raise ExtractorError(
            f'Export did not complete after {self._POLLING_MAX_ATTEMPTS} attempts')
