# coding: utf-8
from __future__ import unicode_literals

import json
import re

from ..compat import compat_str
from ..utils import try_get
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
    _VALID_URL = r'https?://(?:www\.)?discoveryplus\.in/show/(?P<show_name>[^/]+)/?(?:[?#]|$)'
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
            'x-disco-client': 'WEB:UNKNOWN:dplus-india:prod',
            'x-disco-params': 'realm=dplusindia',
            'referer': 'https://www.discoveryplus.in/',
        }
        show_url = 'https://ap2-prod-direct.discoveryplus.in/cms/routes/show/{}?include=default'.format(show_name)
        show_json = self._download_json(show_url,
                                        video_id=show_name,
                                        headers=headers)['included'][4]['attributes']['component']
        show_id = show_json['mandatoryParams'].split('=')[-1]
        season_url = 'https://ap2-prod-direct.discoveryplus.in/content/videos?sort=episodeNumber&filter[seasonNumber]={}&filter[show.id]={}&page[size]=100&page[number]={}'
        for season in show_json['filters'][0]['options']:
            season_id = season['id']
            total_pages, page_num = 1, 0
            while page_num < total_pages:
                season_json = self._download_json(season_url.format(season_id, show_id, compat_str(page_num + 1)),
                                                  video_id=show_id, headers=headers,
                                                  note='Downloading JSON metadata%s' % (' page %d' % page_num if page_num else ''))
                if page_num == 0:
                    total_pages = try_get(season_json, lambda x: x['meta']['totalPages'], int) or 1
                episodes_json = season_json['data']
                for episode in episodes_json:
                    video_id = episode['attributes']['path']
                    yield self.url_result(
                        'https://discoveryplus.in/videos/%s' % video_id,
                        ie=DiscoveryPlusIndiaIE.ie_key(), video_id=video_id)
                page_num += 1

    def _real_extract(self, url):
        show_name = re.match(self._VALID_URL, url).group('show_name')
        return self.playlist_result(self._entries(show_name), playlist_id=show_name)
