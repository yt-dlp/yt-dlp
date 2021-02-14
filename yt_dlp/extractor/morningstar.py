# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor


class MorningstarIE(InfoExtractor):
    IE_DESC = 'morningstar.com'
    _VALID_URL = r'https?://(?:(?:www|news)\.)morningstar\.com/[cC]over/video[cC]enter\.aspx\?id=(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'http://www.morningstar.com/cover/videocenter.aspx?id=615869',
        'md5': '6c0acface7a787aadc8391e4bbf7b0f5',
        'info_dict': {
            'id': '615869',
            'ext': 'mp4',
            'title': 'Get Ahead of the Curve on 2013 Taxes',
            'description': "Vanguard's Joel Dickson on managing higher tax rates for high-income earners and fund capital-gain distributions in 2013.",
            'thumbnail': r're:^https?://.*m(?:orning)?star\.com/.+thumb\.jpg$'
        }
    }, {
        'url': 'http://news.morningstar.com/cover/videocenter.aspx?id=825556',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id')

        webpage = self._download_webpage(url, video_id)
        title = self._html_search_regex(
            r'<h1 id="titleLink">(.*?)</h1>', webpage, 'title')
        video_url = self._html_search_regex(
            r'<input type="hidden" id="hidVideoUrl" value="([^"]+)"',
            webpage, 'video URL')
        thumbnail = self._html_search_regex(
            r'<input type="hidden" id="hidSnapshot" value="([^"]+)"',
            webpage, 'thumbnail', fatal=False)
        description = self._html_search_regex(
            r'<div id="mstarDeck".*?>(.*?)</div>',
            webpage, 'description', fatal=False)

        return {
            'id': video_id,
            'title': title,
            'url': video_url,
            'thumbnail': thumbnail,
            'description': description,
        }
