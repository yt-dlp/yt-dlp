# coding: utf-8
from __future__ import unicode_literals

import json
import re

from .common import InfoExtractor
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


class DiscoveryPlusIndiaShowIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?discoveryplus\.in/show/(?P<show_name>\S*)'
    _TESTS = [{
        'url': 'https://www.discoveryplus.in/show/how-do-they-do-it',
        'playlist_mincount': 140,
        'info_dict': {
            'id': 'how-do-they-do-it',
        },
    }
    ]

    def _entries(self, show_name):
        headers = {
            'authority': 'ap2-prod-direct.discoveryplus.in',
            'x-disco-client': 'WEB:UNKNOWN:dplus-india:prod',
            'x-disco-params': 'realm=dplusindia',
            'origin': 'https://www.discoveryplus.in',
            'referer': 'https://www.discoveryplus.in/',
        }
        show_url = 'https://ap2-prod-direct.discoveryplus.in/cms/routes/show/{}?include=default'.format(show_name)
        show_json = self._download_json(show_url,
                                        video_id=show_name,
                                        headers=headers).get('included')[4].get('attributes').get('component')
        show_id = show_json.get('mandatoryParams').split('=')[-1]
        season_url = 'https://ap2-prod-direct.discoveryplus.in/content/videos?sort=episodeNumber&filter[seasonNumber]={}&filter[show.id]={}&page[size]=100&page[number]={}'
        for season in show_json.get('filters')[0].get('options'):
            season_id = season.get('id')
            season_json = self._download_json(season_url.format(season_id, show_id, '1'), video_id=show_id, headers=headers)
            total_pages = int(season_json.get('meta').get('totalPages')) + 1
            for page in range(1, total_pages + 1):
                episode_url = season_url.format(season_id, show_id, str(page))
                episodes_json = self._download_json(
                    episode_url, video_id=show_id, headers=headers,
                    note='Downloading JSON metadata page %s' % page).get('data')
                for episode in episodes_json:

                    video_id = episode.get('attributes').get('path')
                    yield self.url_result(
                        'https://discoveryplus.in/videos/%s' % video_id,
                        ie=DiscoveryPlusIndiaIE.ie_key(), video_id=video_id)

    def _real_extract(self, url):
        show_name = re.match(self._VALID_URL, url).group('show_name')
        return self.playlist_result(self._entries(show_name), playlist_id=show_name)
