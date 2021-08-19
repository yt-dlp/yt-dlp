# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import remove_start


class Ir90TvIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?90tv\.ir/video/(?P<id>[0-9]+)/.*'
    _TESTS = [{
        'url': 'http://90tv.ir/video/95719/%D8%B4%D8%A7%DB%8C%D8%B9%D8%A7%D8%AA-%D9%86%D9%82%D9%84-%D9%88-%D8%A7%D9%86%D8%AA%D9%82%D8%A7%D9%84%D8%A7%D8%AA-%D9%85%D9%87%D9%85-%D9%81%D9%88%D8%AA%D8%A8%D8%A7%D9%84-%D8%A7%D8%B1%D9%88%D9%BE%D8%A7-940218',
        'md5': '411dbd94891381960cb9e13daa47a869',
        'info_dict': {
            'id': '95719',
            'ext': 'mp4',
            'title': 'شایعات نقل و انتقالات مهم فوتبال اروپا 94/02/18',
            'thumbnail': r're:^https?://.*\.jpg$',
        }
    }, {
        'url': 'http://www.90tv.ir/video/95719/%D8%B4%D8%A7%DB%8C%D8%B9%D8%A7%D8%AA-%D9%86%D9%82%D9%84-%D9%88-%D8%A7%D9%86%D8%AA%D9%82%D8%A7%D9%84%D8%A7%D8%AA-%D9%85%D9%87%D9%85-%D9%81%D9%88%D8%AA%D8%A8%D8%A7%D9%84-%D8%A7%D8%B1%D9%88%D9%BE%D8%A7-940218',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = remove_start(self._html_search_regex(
            r'<title>([^<]+)</title>', webpage, 'title'), '90tv.ir :: ')

        video_url = self._search_regex(
            r'<source[^>]+src="([^"]+)"', webpage, 'video url')

        thumbnail = self._search_regex(r'poster="([^"]+)"', webpage, 'thumbnail url', fatal=False)

        return {
            'url': video_url,
            'id': video_id,
            'title': title,
            'video_url': video_url,
            'thumbnail': thumbnail,
        }
