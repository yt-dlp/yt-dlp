# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class CAM4IE(InfoExtractor):
    _VALID_URL = r'https?://(?:[^/]+\.)?cam4\.com/(?P<id>[a-z0-9_]+)'
    _TEST = {
        'url': 'https://www.cam4.com/foxynesss',
        'info_dict': {
            'id': 'foxynesss',
            'ext': 'mp4',
            'title': 're:^foxynesss [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'age_limit': 18,
            'live_status': 'is_live',
            'thumbnail': 'https://snapshots.xcdnpro.com/thumbnails/foxynesss',
        }
    }

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        m3u8_playlist = self._download_json('https://www.cam4.com/rest/v1.0/profile/{}/streamInfo'.format(channel_id), channel_id).get('cdnURL')

        formats = self._extract_m3u8_formats(m3u8_playlist, channel_id, 'mp4', m3u8_id='hls', live=True)
        self._sort_formats(formats)

        return {
            'id': channel_id,
            'title': channel_id,
            'is_live': True,
            'age_limit': 18,
            'formats': formats,
            'thumbnail': f'https://snapshots.xcdnpro.com/thumbnails/{channel_id}',
        }
