# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class RTVSIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rtvs\.sk/(?:radio|televizia)/archiv/\d+/(?P<id>\d+)'
    _TESTS = [{
        # radio archive
        'url': 'http://www.rtvs.sk/radio/archiv/11224/414872',
        'md5': '134d5d6debdeddf8a5d761cbc9edacb8',
        'info_dict': {
            'id': '414872',
            'ext': 'mp3',
            'title': 'Ostrov pokladov 1 časť.mp3'
        },
        'params': {
            'skip_download': True,
        }
    }, {
        # tv archive
        'url': 'http://www.rtvs.sk/televizia/archiv/8249/63118',
        'md5': '85e2c55cf988403b70cac24f5c086dc6',
        'info_dict': {
            'id': '63118',
            'ext': 'mp4',
            'title': 'Amaro Džives - Náš deň',
            'description': 'Galavečer pri príležitosti Medzinárodného dňa Rómov.'
        },
        'params': {
            'skip_download': True,
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        playlist_url = self._search_regex(
            r'playlist["\']?\s*:\s*(["\'])(?P<url>(?:(?!\1).)+)\1', webpage,
            'playlist url', group='url')

        data = self._download_json(
            playlist_url, video_id, 'Downloading playlist')[0]
        return self._parse_jwplayer_data(data, video_id=video_id)
