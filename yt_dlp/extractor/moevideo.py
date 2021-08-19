# coding: utf-8
from __future__ import unicode_literals


from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
)


class MoeVideoIE(InfoExtractor):
    IE_DESC = 'LetitBit video services: moevideo.net, playreplay.net and videochart.net'
    _VALID_URL = r'''(?x)
        https?://(?P<host>(?:www\.)?
        (?:(?:moevideo|playreplay|videochart)\.net|thesame\.tv))/
        (?:video|framevideo|embed)/(?P<id>[0-9a-z]+\.[0-9A-Za-z]+)'''
    _API_URL = 'http://api.letitbit.net/'
    _API_KEY = 'tVL0gjqo5'
    _TESTS = [
        {
            'url': 'http://moevideo.net/video/00297.0036103fe3d513ef27915216fd29',
            'md5': '129f5ae1f6585d0e9bb4f38e774ffb3a',
            'info_dict': {
                'id': '00297.0036103fe3d513ef27915216fd29',
                'ext': 'flv',
                'title': 'Sink cut out machine',
                'description': 'md5:f29ff97b663aefa760bf7ca63c8ca8a8',
                'thumbnail': r're:^https?://.*\.jpg$',
                'width': 540,
                'height': 360,
                'duration': 179,
                'filesize': 17822500,
            },
            'skip': 'Video has been removed',
        },
        {
            'url': 'http://playreplay.net/video/77107.7f325710a627383d40540d8e991a',
            'md5': '74f0a014d5b661f0f0e2361300d1620e',
            'info_dict': {
                'id': '77107.7f325710a627383d40540d8e991a',
                'ext': 'flv',
                'title': 'Operacion Condor.',
                'description': 'md5:7e68cb2fcda66833d5081c542491a9a3',
                'thumbnail': r're:^https?://.*\.jpg$',
                'width': 480,
                'height': 296,
                'duration': 6027,
                'filesize': 588257923,
            },
            'skip': 'Video has been removed',
        },
    ]

    def _real_extract(self, url):
        host, video_id = self._match_valid_url(url).groups()

        webpage = self._download_webpage(
            'http://%s/video/%s' % (host, video_id),
            video_id, 'Downloading webpage')

        title = self._og_search_title(webpage)

        embed_webpage = self._download_webpage(
            'http://%s/embed/%s' % (host, video_id),
            video_id, 'Downloading embed webpage')
        video = self._parse_json(self._search_regex(
            r'mvplayer\("#player"\s*,\s*({.+})',
            embed_webpage, 'mvplayer'), video_id)['video']

        return {
            'id': video_id,
            'title': title,
            'thumbnail': video.get('poster') or self._og_search_thumbnail(webpage),
            'description': clean_html(self._og_search_description(webpage)),
            'duration': int_or_none(self._og_search_property('video:duration', webpage)),
            'url': video['ourUrl'],
        }
