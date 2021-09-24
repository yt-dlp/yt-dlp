# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import try_get


class ThetaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?theta\.tv/(?P<id>[a-z0-9]+)'
    _TESTS = [{
        'url': 'https://www.theta.tv/davirus',
        'skip': 'The live may have ended',
        'info_dict': {
            'id': 'DaVirus',
            'ext': 'mp4',
            'title': 'I choose you - My Community is King -👀 - YO HABLO ESPANOL - CODE DAVIRUS',
            'thumbnail': r're:https://live-thumbnails-prod-theta-tv\.imgix\.net/thumbnail/.+\.jpg',
        }
    }, {
        'url': 'https://www.theta.tv/mst3k',
        'note': 'This channel is live 24/7',
        'info_dict': {
            'id': 'MST3K',
            'ext': 'mp4',
            'title': 'Mystery Science Theatre 3000 24/7 Powered by the THETA Network.',
            'thumbnail': r're:https://user-prod-theta-tv\.imgix\.net/.+\.jpg',
        }
    }]

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        info = self._download_json(f'https://api.theta.tv/v1/channel?alias={channel_id}', channel_id)['body']

        m3u8_playlist = next(
            data['url'] for data in info['live_stream']['video_urls']
            if data.get('type') != 'embed' and data.get('resolution') in ('master', 'source'))

        formats = self._extract_m3u8_formats(m3u8_playlist, channel_id, 'mp4', m3u8_id='hls', live=True)
        self._sort_formats(formats)

        channel = try_get(info, lambda x: x['user']['username'])  # using this field instead of channel_id due to capitalization

        return {
            'id': channel,
            'title': try_get(info, lambda x: x['live_stream']['title']),
            'channel': channel,
            'view_count': try_get(info, lambda x: x['live_stream']['view_count']),
            'is_live': True,
            'formats': formats,
            'thumbnail': try_get(info, lambda x: x['live_stream']['thumbnail_url']),
        }
