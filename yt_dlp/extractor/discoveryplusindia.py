# coding: utf-8
from __future__ import unicode_literals

import re

from .dplay import DPlayIE

class DiscoveryPlusIndiaIE(DPlayIE):
    _VALID_URL = r'https?://(?:www\.)?discoveryplus\.in/videos?' + DPlayIE._PATH_REGEX
    _TESTS = [{
        'url': 'https://www.discoveryplus.in/videos/how-do-they-do-it/fugu-and-more?seasonId=8&type=EPISODE',
        'info_dict': {
            'id': '27104',
            'ext': 'mp4',
            'display_id': 'how-do-they-do-it/fugu-and-more',
            'title': 'Fugu and More',
            'description': 'The Japanese catch, prepare and eat the deadliest fish on the planet.',
            'duration': 1319,
            'timestamp': 1582309800,
            'upload_date': '20200221',
            'series': 'How Do They Do It?',
            'season_number': 8,
            'episode_number': 2,
            'creator': 'Discovery Channel',
        },
        'params': {
            'format': 'bestvideo',
            'skip_download': True,
        },
        'skip': 'Cookies (not necessarily logged in) are needed'
    }]

    def _update_disco_api_headers(self, headers, disco_base, display_id, realm):
        headers['x-disco-params'] = 'realm=%s' % realm
        headers['x-disco-client'] = 'WEB:UNKNOWN:dplus-india:17.0.0'

    def _download_video_playback_info(self, disco_base, video_id, headers):
        return self._download_json(
            disco_base + 'playback/v3/videoPlaybackInfo',
            video_id, headers=headers, data=json.dumps({
                'deviceInfo': {
                    'adBlocker': False,
                },
                'videoId': video_id,
            }).encode('utf-8'))['data']['attributes']['streaming']

    def _real_extract(self, url):
        display_id = self._match_id(url)
        return self._get_disco_api_info(
            url, display_id, 'ap2-prod-direct.discoveryplus.in', 'dplusindia', 'in')
