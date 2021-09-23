# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class ThetaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?theta\.tv/(?P<id>[a-z0-9]+)'
    _TESTS = [{
        'url': 'https://www.theta.tv/davirus',
        'info_dict': {
            'id': 'DaVirus',
            'ext': 'mp4',
            'title': r're:.+',
            'thumbnail': r're:https://live-thumbnails-prod-theta-tv\.imgix\.net/thumbnail/.+\.jpg',
        }
    }, {
        'url': 'https://www.theta.tv/mst3k',
        'info_dict': {
            'id': 'MST3K',
            'ext': 'mp4',
            'title': r're:.+',
            'thumbnail': r're:https://user-prod-theta-tv\.imgix\.net/.+\.jpg',
        }
    }]

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        info = self._download_json('https://api.theta.tv/v1/channel?alias={}'.format(channel_id), channel_id)['body']

        for data in info.get('live_stream').get('video_urls'):
            if (data.get('type') != 'embed') and ((data.get('resolution') == 'master') or (data.get('resolution') == 'source')):
                m3u8_playlist = data.get('url')

        formats = self._extract_m3u8_formats(m3u8_playlist, channel_id, 'mp4', m3u8_id='hls', live=True)
        self._sort_formats(formats)

        return {
            'id': info.get('user').get('username'),  # using this field instead of channel_id due to capitalization
            'title': info.get('live_stream').get('title'),
            'is_live': True,
            'formats': formats,
            'thumbnail': info.get('live_stream').get('thumbnail_url'),
        }
