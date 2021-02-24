# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    str_to_int,
    ExtractorError
)


class AppleConnectIE(InfoExtractor):
    _VALID_URL = r'https?://itunes\.apple\.com/\w{0,2}/?post/idsa\.(?P<id>[\w-]+)'
    _TEST = {
        'url': 'https://itunes.apple.com/us/post/idsa.4ab17a39-2720-11e5-96c5-a5b38f6c42d3',
        'md5': 'e7c38568a01ea45402570e6029206723',
        'info_dict': {
            'id': '4ab17a39-2720-11e5-96c5-a5b38f6c42d3',
            'ext': 'm4v',
            'title': 'Energy',
            'uploader': 'Drake',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20150710',
            'timestamp': 1436545535,
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        try:
            video_json = self._html_search_regex(
                r'class="auc-video-data">(\{.*?\})', webpage, 'json')
        except ExtractorError:
            raise ExtractorError('This post doesn\'t contain a video', expected=True)

        video_data = self._parse_json(video_json, video_id)
        timestamp = str_to_int(self._html_search_regex(r'data-timestamp="(\d+)"', webpage, 'timestamp'))
        like_count = str_to_int(self._html_search_regex(r'(\d+) Loves', webpage, 'like count'))

        return {
            'id': video_id,
            'url': video_data['sslSrc'],
            'title': video_data['title'],
            'description': video_data['description'],
            'uploader': video_data['artistName'],
            'thumbnail': video_data['artworkUrl'],
            'timestamp': timestamp,
            'like_count': like_count,
        }
