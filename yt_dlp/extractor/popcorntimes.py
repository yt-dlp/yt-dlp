# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import (
    compat_b64decode,
    compat_chr,
)
from ..utils import int_or_none


class PopcorntimesIE(InfoExtractor):
    _VALID_URL = r'https?://popcorntimes\.tv/[^/]+/m/(?P<id>[^/]+)/(?P<display_id>[^/?#&]+)'
    _TEST = {
        'url': 'https://popcorntimes.tv/de/m/A1XCFvz/haensel-und-gretel-opera-fantasy',
        'md5': '93f210991ad94ba8c3485950a2453257',
        'info_dict': {
            'id': 'A1XCFvz',
            'display_id': 'haensel-und-gretel-opera-fantasy',
            'ext': 'mp4',
            'title': 'Hänsel und Gretel',
            'description': 'md5:1b8146791726342e7b22ce8125cf6945',
            'thumbnail': r're:^https?://.*\.jpg$',
            'creator': 'John Paul',
            'release_date': '19541009',
            'duration': 4260,
            'tbr': 5380,
            'width': 720,
            'height': 540,
        },
    }

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id, display_id = mobj.group('id', 'display_id')

        webpage = self._download_webpage(url, display_id)

        title = self._search_regex(
            r'<h1>([^<]+)', webpage, 'title',
            default=None) or self._html_search_meta(
            'ya:ovs:original_name', webpage, 'title', fatal=True)

        loc = self._search_regex(
            r'PCTMLOC\s*=\s*(["\'])(?P<value>(?:(?!\1).)+)\1', webpage, 'loc',
            group='value')

        loc_b64 = ''
        for c in loc:
            c_ord = ord(c)
            if ord('a') <= c_ord <= ord('z') or ord('A') <= c_ord <= ord('Z'):
                upper = ord('Z') if c_ord <= ord('Z') else ord('z')
                c_ord += 13
                if upper < c_ord:
                    c_ord -= 26
            loc_b64 += compat_chr(c_ord)

        video_url = compat_b64decode(loc_b64).decode('utf-8')

        description = self._html_search_regex(
            r'(?s)<div[^>]+class=["\']pt-movie-desc[^>]+>(.+?)</div>', webpage,
            'description', fatal=False)

        thumbnail = self._search_regex(
            r'<img[^>]+class=["\']video-preview[^>]+\bsrc=(["\'])(?P<value>(?:(?!\1).)+)\1',
            webpage, 'thumbnail', default=None,
            group='value') or self._og_search_thumbnail(webpage)

        creator = self._html_search_meta(
            'video:director', webpage, 'creator', default=None)

        release_date = self._html_search_meta(
            'video:release_date', webpage, default=None)
        if release_date:
            release_date = release_date.replace('-', '')

        def int_meta(name):
            return int_or_none(self._html_search_meta(
                name, webpage, default=None))

        return {
            'id': video_id,
            'display_id': display_id,
            'url': video_url,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'creator': creator,
            'release_date': release_date,
            'duration': int_meta('video:duration'),
            'tbr': int_meta('ya:ovs:bitrate'),
            'width': int_meta('og:video:width'),
            'height': int_meta('og:video:height'),
            'http_headers': {
                'Referer': url,
            },
        }
