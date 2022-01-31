# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
)


class VoeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?voe\.sx/(?P<id>[0-9a-zA-Z]+)'
    _TEST = {
        'url': 'https://voe.sx/689qhm634rc8',
        'md5': '963b6ce24c8a9b1877d596ab69dbedca',
        'info_dict': {
            'id': '689qhm634rc8',
            'ext': 'mp4',
            'title': 'Big Buck Bunny 512kb',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        if any(p in webpage for p in (
                '>Error 404 - File not found<',
                '>Oh nooo! The file you are looking for could not be found.<')):
            raise ExtractorError('Video %s does not exist' % video_id, expected=True)

        title = self._html_search_regex(r'<title>Watch (.+?)</title>', webpage, 'title')
        video_url = self._html_search_regex(r'"hls": "(.+?)",', webpage, 'title')

        return {
            'id': video_id,
            'title': title,
            'url': video_url,
            'protocol': 'm3u8',
            'manifest_url': video_url,
            'ext': 'mp4',
        }
