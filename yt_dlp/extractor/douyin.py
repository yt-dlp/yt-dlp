# coding: utf-8
from __future__ import unicode_literals

import json

from .common import (
    InfoExtractor,
    compat_urllib_parse_unquote,
)


class DouyinIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?douyin\.com/video/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.douyin.com/video/6961737553342991651',
        'md5': 'f0114e6688442972d80fab1083543197',
        'info_dict': {
            'id': '6961737553342991651',
            'ext': 'mp4',
            'title': '#杨超越  小小水手带你去远航❤️',
        }
    }, {
        'url': 'https://www.douyin.com/video/6982497745948921092',
        'md5': 'bdc8a6b4ce22c887e0064d2813befa27',
        'info_dict': {
            'id': '6982497745948921092',
            'ext': 'mp4',
            'title': '这个夏日和小羊@杨超越 一起遇见白色幻想',
        }
    }, {
        'url': 'https://www.douyin.com/video/6953975910773099811',
        'md5': 'dde3302460f19db59c47060ff013b902',
        'info_dict': {
            'id': '6953975910773099811',
            'ext': 'mp4',
            'title': '#一起看海  出现在你的夏日里',
        }
    }, {
        'url': 'https://www.douyin.com/video/6950251282489675042',
        'md5': 'f61844399e85f0ff18cfab91d20fe326',
        'info_dict': {
            'id': '6950251282489675042',
            'ext': 'mp4',
            'title': '哈哈哈，成功了哈哈哈哈哈哈',
        }
    }, {
        'url': 'https://www.douyin.com/video/6963263655114722595',
        'md5': '30a852b6efb232df202b80894f51422d',
        'info_dict': {
            'id': '6963263655114722595',
            'ext': 'mp4',
            'title': '#哪个爱豆的105度最甜 换个角度看看我哈哈',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        # The video player and video source are rendered client-side, the data
        # contains in a <script id="RENDER_DATA" type="application/json"> tag
        # quoted, unquote the whole page content then search using regex with
        # regular string.
        webpage = compat_urllib_parse_unquote(webpage)

        # As of today, this seems good enough to pinpoint the title
        title = self._html_search_regex(r'"desc":"([^"]*)"', webpage, 'title')

        # video URLs are in this pattern {"src":"THE_URL"}, in json format,
        # as a list of CDN urls, all serving the same file
        urls = json.loads(
            self._html_search_regex(r'"playAddr":(\[.*?\])', webpage, 'urls'))

        return {
            'id': video_id,
            'title': title,
            'url': 'https:' + urls[0]['src'],
            'ext': 'mp4',
        }
