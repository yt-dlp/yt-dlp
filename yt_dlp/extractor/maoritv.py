# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class MaoriTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?maoritelevision\.com/shows/(?:[^/]+/)+(?P<id>[^/?&#]+)'
    _TEST = {
        'url': 'https://www.maoritelevision.com/shows/korero-mai/S01E054/korero-mai-series-1-episode-54',
        'md5': '5ade8ef53851b6a132c051b1cd858899',
        'info_dict': {
            'id': '4774724855001',
            'ext': 'mp4',
            'title': 'Kōrero Mai, Series 1 Episode 54',
            'upload_date': '20160226',
            'timestamp': 1456455018,
            'description': 'md5:59bde32fd066d637a1a55794c56d8dcb',
            'uploader_id': '1614493167001',
        },
    }
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/1614493167001/HJlhIQhQf_default/index.html?videoId=%s'

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        brightcove_id = self._search_regex(
            r'data-main-video-id=["\'](\d+)', webpage, 'brightcove id')
        return self.url_result(
            self.BRIGHTCOVE_URL_TEMPLATE % brightcove_id,
            'BrightcoveNew', brightcove_id)
