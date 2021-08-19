# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class Formula1IE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?formula1\.com/en/latest/video\.[^.]+\.(?P<id>\d+)\.html'
    _TEST = {
        'url': 'https://www.formula1.com/en/latest/video.race-highlights-spain-2016.6060988138001.html',
        'md5': 'be7d3a8c2f804eb2ab2aa5d941c359f8',
        'info_dict': {
            'id': '6060988138001',
            'ext': 'mp4',
            'title': 'Race highlights - Spain 2016',
            'timestamp': 1463332814,
            'upload_date': '20160515',
            'uploader_id': '6057949432001',
        },
        'add_ie': ['BrightcoveNew'],
    }
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/6057949432001/S1WMrhjlh_default/index.html?videoId=%s'

    def _real_extract(self, url):
        bc_id = self._match_id(url)
        return self.url_result(
            self.BRIGHTCOVE_URL_TEMPLATE % bc_id, 'BrightcoveNew', bc_id)
