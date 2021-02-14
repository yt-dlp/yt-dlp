# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    urlencode_postdata,
)


class StreamcloudIE(InfoExtractor):
    IE_NAME = 'streamcloud.eu'
    _VALID_URL = r'https?://streamcloud\.eu/(?P<id>[a-zA-Z0-9_-]+)(?:/(?P<fname>[^#?]*)\.html)?'

    _TESTS = [{
        'url': 'http://streamcloud.eu/skp9j99s4bpz/youtube-dlc_test_video_____________-BaW_jenozKc.mp4.html',
        'md5': '6bea4c7fa5daaacc2a946b7146286686',
        'info_dict': {
            'id': 'skp9j99s4bpz',
            'ext': 'mp4',
            'title': 'youtube-dlc test video  \'/\\ ä ↭',
        },
        'skip': 'Only available from the EU'
    }, {
        'url': 'http://streamcloud.eu/ua8cmfh1nbe6/NSHIP-148--KUC-NG--H264-.mp4.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        url = 'http://streamcloud.eu/%s' % video_id

        orig_webpage = self._download_webpage(url, video_id)

        if '>File Not Found<' in orig_webpage:
            raise ExtractorError(
                'Video %s does not exist' % video_id, expected=True)

        fields = re.findall(r'''(?x)<input\s+
            type="(?:hidden|submit)"\s+
            name="([^"]+)"\s+
            (?:id="[^"]+"\s+)?
            value="([^"]*)"
            ''', orig_webpage)

        self._sleep(6, video_id)

        webpage = self._download_webpage(
            url, video_id, data=urlencode_postdata(fields), headers={
                b'Content-Type': b'application/x-www-form-urlencoded',
            })

        try:
            title = self._html_search_regex(
                r'<h1[^>]*>([^<]+)<', webpage, 'title')
            video_url = self._search_regex(
                r'file:\s*"([^"]+)"', webpage, 'video URL')
        except ExtractorError:
            message = self._html_search_regex(
                r'(?s)<div[^>]+class=(["\']).*?msgboxinfo.*?\1[^>]*>(?P<message>.+?)</div>',
                webpage, 'message', default=None, group='message')
            if message:
                raise ExtractorError('%s said: %s' % (self.IE_NAME, message), expected=True)
            raise
        thumbnail = self._search_regex(
            r'image:\s*"([^"]+)"', webpage, 'thumbnail URL', fatal=False)

        return {
            'id': video_id,
            'title': title,
            'url': video_url,
            'thumbnail': thumbnail,
            'http_headers': {
                'Referer': url,
            },
        }
