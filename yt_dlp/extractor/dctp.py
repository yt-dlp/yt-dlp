# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    float_or_none,
    int_or_none,
    unified_timestamp,
    url_or_none,
)


class DctpTvIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?dctp\.tv/(?:#/)?filme/(?P<id>[^/?#&]+)'
    _TESTS = [{
        # 4x3
        'url': 'http://www.dctp.tv/filme/videoinstallation-fuer-eine-kaufhausfassade/',
        'md5': '3ffbd1556c3fe210724d7088fad723e3',
        'info_dict': {
            'id': '95eaa4f33dad413aa17b4ee613cccc6c',
            'display_id': 'videoinstallation-fuer-eine-kaufhausfassade',
            'ext': 'm4v',
            'title': 'Videoinstallation für eine Kaufhausfassade',
            'description': 'Kurzfilm',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 71.24,
            'timestamp': 1302172322,
            'upload_date': '20110407',
        },
    }, {
        # 16x9
        'url': 'http://www.dctp.tv/filme/sind-youtuber-die-besseren-lehrer/',
        'only_matching': True,
    }]

    _BASE_URL = 'http://dctp-ivms2-restapi.s3.amazonaws.com'

    def _real_extract(self, url):
        display_id = self._match_id(url)

        version = self._download_json(
            '%s/version.json' % self._BASE_URL, display_id,
            'Downloading version JSON')

        restapi_base = '%s/%s/restapi' % (
            self._BASE_URL, version['version_name'])

        info = self._download_json(
            '%s/slugs/%s.json' % (restapi_base, display_id), display_id,
            'Downloading video info JSON')

        media = self._download_json(
            '%s/media/%s.json' % (restapi_base, compat_str(info['object_id'])),
            display_id, 'Downloading media JSON')

        uuid = media['uuid']
        title = media['title']
        is_wide = media.get('is_wide')
        formats = []

        def add_formats(suffix):
            templ = 'https://%%s/%s_dctp_%s.m4v' % (uuid, suffix)
            formats.extend([{
                'format_id': 'hls-' + suffix,
                'url': templ % 'cdn-segments.dctp.tv' + '/playlist.m3u8',
                'protocol': 'm3u8_native',
            }, {
                'format_id': 's3-' + suffix,
                'url': templ % 'completed-media.s3.amazonaws.com',
            }, {
                'format_id': 'http-' + suffix,
                'url': templ % 'cdn-media.dctp.tv',
            }])

        add_formats('0500_' + ('16x9' if is_wide else '4x3'))
        if is_wide:
            add_formats('720p')

        thumbnails = []
        images = media.get('images')
        if isinstance(images, list):
            for image in images:
                if not isinstance(image, dict):
                    continue
                image_url = url_or_none(image.get('url'))
                if not image_url:
                    continue
                thumbnails.append({
                    'url': image_url,
                    'width': int_or_none(image.get('width')),
                    'height': int_or_none(image.get('height')),
                })

        return {
            'id': uuid,
            'display_id': display_id,
            'title': title,
            'alt_title': media.get('subtitle'),
            'description': media.get('description') or media.get('teaser'),
            'timestamp': unified_timestamp(media.get('created')),
            'duration': float_or_none(media.get('duration_in_ms'), scale=1000),
            'thumbnails': thumbnails,
            'formats': formats,
        }
