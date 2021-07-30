# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class VIDLOXIE(InfoExtractor):
    IE_NAME = 'vidlox'
    IE_DESC = 'vidlox'
    _VALID_URL = r'https?://vidlox\.me/(embed-)?(?P<id>[a-z0-9]+).html'
    _TEST = {
        'url': 'https://vidlox.me/6wq8gciafziz.html',
        'info_dict': {
            'id': '6wq8gciafziz',
            'title': 'md5:74c82229b059846a82628e60dcc661b5',
            'ext': 'm3u8',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(
            'https://vidlox.me/%s.html' % video_id, video_id)

        m3u8 = self._search_regex(
            r'(https.+m3u8)',
            webpage, 'm3u8')

        title = self._search_regex(
            r'<title>Watch (?P<title>.+)<\/title>',
            webpage, 'title', group='title')

        thumbnail = self._search_regex(
            r'spriteSheetUrl = "(?P<thumbnail>https.+)"',
            webpage, 'thumbnail', group='thumbnail')

        formats = self._extract_m3u8_formats(m3u8, video_id)
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': thumbnail,
        }
