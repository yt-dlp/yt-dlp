# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor

from ..utils import (
    int_or_none,
    mimetype2ext,
    unified_timestamp,
    url_or_none,
)


class VeoIE(InfoExtractor):
    _VALID_URL = r'https?://app\.veo\.co/matches/(?P<id>[0-9A-Za-z-]+)'

    _TESTS = [{
        'url': 'https://app.veo.co/matches/20201027-last-period/',
        'info_dict': {
            'id': '20201027-last-period',
            'ext': 'mp4',
            'title': 'Akidemy u11s v Bradford Boys u11s (Game 3)',
            'thumbnail': 're:https://c.veocdn.com/.+/thumbnail.jpg',
            'upload_date': '20201028',
            'timestamp': 1603847208,
            'duration': 1916,
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        metadata = self._download_json(
            'https://app.veo.co/api/app/matches/%s' % video_id, video_id)

        video_data = self._download_json(
            'https://app.veo.co/api/app/matches/%s/videos' % video_id, video_id, 'Downloading video data')

        title = metadata.get('title')
        thumbnail = url_or_none(metadata.get('thumbnail'))

        timestamp = unified_timestamp(metadata.get('created'))
        duration = int_or_none(metadata.get('duration'))
        view_count = int_or_none(metadata.get('view_count'))

        formats = []
        for fmt in video_data:
            mimetype = fmt.get('mime_type')
            # skip configuration file for panoramic video
            if mimetype == 'video/mp2t':
                continue
            height = int_or_none(fmt.get('height'))
            bitrate = int_or_none(fmt.get('bit_rate'), scale=1000)
            render_type = fmt.get('render_type')
            formats.append({
                'url': url_or_none(fmt.get('url')),
                'format_id': '%s-%sp' % (render_type, height),
                'ext': mimetype2ext(mimetype),
                'width': int_or_none(fmt.get('width')),
                'height': height,
                'vbr': bitrate
            })

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': thumbnail,
            'timestamp': timestamp,
            'view_count': view_count,
            'duration': duration
        }
