# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    smuggle_url,
    traverse_obj,
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
            'description': 'md5:1985b51a9abc285df0104d982a325f2a',
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
        player_config = self._search_nuxt_data(webpage, display_id)
        video_id = traverse_obj(player_config, ('movie', 'video_id'))
        if not video_id:
            raise ExtractorError('Failed to extract video ID for Brightcove')
        account_id = traverse_obj(player_config, ('player', 'account')) or '3855502814001'
        title = traverse_obj(player_config, ('movie', 'name'))
        if not title:
            og_title = self._og_search_title(webpage, fatal=False) or traverse_obj(player_config, ('player', 'title'))
            if og_title:
                title = og_title.split('(', 1)[0].strip()
        description = (traverse_obj(player_config, ('movie', 'description'))
                       or self._html_search_meta(['description', 'og:description'], webpage))
        return {
            '_type': 'url_transparent',
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'url': smuggle_url(self.BRIGHTCOVE_URL_TEMPLATE % (account_id, video_id), {'geo_countries': ['JP']}),
            'ie_key': 'BrightcoveNew',
        }
