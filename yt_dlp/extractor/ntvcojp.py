# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    js_to_json,
    smuggle_url,
)


class NTVCoJpCUIE(InfoExtractor):
    IE_NAME = 'cu.ntv.co.jp'
    IE_DESC = 'Nippon Television Network'
    _VALID_URL = r'https?://cu\.ntv\.co\.jp/(?!program)(?P<id>[^/?&#]+)'
    _TEST = {
        'url': 'https://cu.ntv.co.jp/televiva-chill-gohan_181031/',
        'info_dict': {
            'id': '5978891207001',
            'ext': 'mp4',
            'title': '桜エビと炒り卵がポイント！ 「中華風 エビチリおにぎり」──『美虎』五十嵐美幸',
            'upload_date': '20181213',
            'description': 'md5:211b52f4fd60f3e0e72b68b0c6ba52a9',
            'uploader_id': '3855502814001',
            'timestamp': 1544669941,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/default_default/index.html?videoId=%s'

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        player_config = self._parse_json(self._search_regex(
            r'(?s)PLAYER_CONFIG\s*=\s*({.+?})',
            webpage, 'player config'), display_id, js_to_json)
        video_id = player_config['videoId']
        account_id = player_config.get('account') or '3855502814001'
        return {
            '_type': 'url_transparent',
            'id': video_id,
            'display_id': display_id,
            'title': self._search_regex(r'<h1[^>]+class="title"[^>]*>([^<]+)', webpage, 'title').strip(),
            'description': self._html_search_meta(['description', 'og:description'], webpage),
            'url': smuggle_url(self.BRIGHTCOVE_URL_TEMPLATE % (account_id, video_id), {'geo_countries': ['JP']}),
            'ie_key': 'BrightcoveNew',
        }
