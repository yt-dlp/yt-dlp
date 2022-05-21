# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class SkiMagIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?skimag\.com/video/[a-zA-Z0-9\-]+/'
    _TESTS = [{
        'url': 'https://www.skimag.com/video/ski-people-1980/',
        'md5': '022a7e31c70620ebec18deeab376ee03',
        'info_dict': {
            'id': 'YTmgRiNU',
            'ext': 'mp4',
            'title': '1980 Ski People',
            'timestamp': 1610407738,
            'description': 'md5:cf9c3d101452c91e141f292b19fe4843',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/YTmgRiNU/poster.jpg?width=720',
            'duration': 5688.0,
            'upload_date': '20210111',
        }
    }]

    def _real_extract(self, url):
        webpage = self._download_webpage(url, '')
        media_id = self._html_search_regex(
            r'<div id="([a-zA-Z0-9]{8})"[^>]+data-video-jw-id="[a-zA-Z0-9]{8}"',
            webpage, "jwp media id")

        return self.url_result(
            'jwplatform:' + media_id, 'JWPlatform', media_id)
