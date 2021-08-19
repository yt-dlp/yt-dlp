# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class FOX9IE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?fox9\.com/video/(?P<id>\d+)'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result(
            'anvato:anvato_epfox_app_web_prod_b3373168e12f423f41504f207000188daf88251b:' + video_id,
            'Anvato', video_id)


class FOX9NewsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?fox9\.com/news/(?P<id>[^/?&#]+)'
    _TEST = {
        'url': 'https://www.fox9.com/news/black-bear-in-tree-draws-crowd-in-downtown-duluth-minnesota',
        'md5': 'd6e1b2572c3bab8a849c9103615dd243',
        'info_dict': {
            'id': '314473',
            'ext': 'mp4',
            'title': 'Bear climbs tree in downtown Duluth',
            'description': 'md5:6a36bfb5073a411758a752455408ac90',
            'duration': 51,
            'timestamp': 1478123580,
            'upload_date': '20161102',
            'uploader': 'EPFOX',
            'categories': ['News', 'Sports'],
            'tags': ['news', 'video'],
        },
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        anvato_id = self._search_regex(
            r'anvatoId\s*:\s*[\'"](\d+)', webpage, 'anvato id')
        return self.url_result('https://www.fox9.com/video/' + anvato_id, 'FOX9')
