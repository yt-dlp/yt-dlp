# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class WeiqiTVIE(InfoExtractor):
    IE_DESC = 'WQTV'
    _VALID_URL = r'https?://(?:www\.)?weiqitv\.com/index/video_play\?videoId=(?P<id>[A-Za-z0-9]+)'

    _TESTS = [{
        'url': 'http://www.weiqitv.com/index/video_play?videoId=53c744f09874f0e76a8b46f3',
        'md5': '26450599afd64c513bc77030ad15db44',
        'info_dict': {
            'id': '53c744f09874f0e76a8b46f3',
            'ext': 'mp4',
            'title': '2013年度盘点',
        },
    }, {
        'url': 'http://www.weiqitv.com/index/video_play?videoId=567379a2d4c36cca518b4569',
        'info_dict': {
            'id': '567379a2d4c36cca518b4569',
            'ext': 'mp4',
            'title': '民国围棋史',
        },
    }, {
        'url': 'http://www.weiqitv.com/index/video_play?videoId=5430220a9874f088658b4567',
        'info_dict': {
            'id': '5430220a9874f088658b4567',
            'ext': 'mp4',
            'title': '二路托过的手段和运用',
        },
    }]

    def _real_extract(self, url):
        media_id = self._match_id(url)
        page = self._download_webpage(url, media_id)

        info_json_str = self._search_regex(
            r'var\s+video\s*=\s*(.+});', page, 'info json str')
        info_json = self._parse_json(info_json_str, media_id)

        letvcloud_url = self._search_regex(
            r'var\s+letvurl\s*=\s*"([^"]+)', page, 'letvcloud url')

        return {
            '_type': 'url_transparent',
            'ie_key': 'LetvCloud',
            'url': letvcloud_url,
            'title': info_json['name'],
            'id': media_id,
        }
