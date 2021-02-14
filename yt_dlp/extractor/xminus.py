# coding: utf-8
from __future__ import unicode_literals

import re
import time

from .common import InfoExtractor
from ..compat import (
    compat_ord,
)
from ..utils import (
    int_or_none,
    parse_duration,
)


class XMinusIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?x-minus\.org/track/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'http://x-minus.org/track/4542/%D0%BF%D0%B5%D1%81%D0%B5%D0%BD%D0%BA%D0%B0-%D1%88%D0%BE%D1%84%D0%B5%D1%80%D0%B0.html',
        'md5': '401a15f2d2dcf6d592cb95528d72a2a8',
        'info_dict': {
            'id': '4542',
            'ext': 'mp3',
            'title': 'Леонид Агутин-Песенка шофёра',
            'duration': 156,
            'tbr': 320,
            'filesize_approx': 5900000,
            'view_count': int,
            'description': 'md5:03238c5b663810bc79cf42ef3c03e371',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        artist = self._html_search_regex(
            r'<a[^>]+href="/artist/\d+">([^<]+)</a>', webpage, 'artist')
        title = artist + '-' + self._html_search_regex(
            r'<span[^>]+class="minustrack-full-title(?:\s+[^"]+)?"[^>]*>([^<]+)', webpage, 'title')
        duration = parse_duration(self._html_search_regex(
            r'<span[^>]+class="player-duration(?:\s+[^"]+)?"[^>]*>([^<]+)',
            webpage, 'duration', fatal=False))
        mobj = re.search(
            r'<div[^>]+class="dw-info(?:\s+[^"]+)?"[^>]*>(?P<tbr>\d+)\s*кбит/c\s+(?P<filesize>[0-9.]+)\s*мб</div>',
            webpage)
        tbr = filesize_approx = None
        if mobj:
            filesize_approx = float(mobj.group('filesize')) * 1000000
            tbr = float(mobj.group('tbr'))
        view_count = int_or_none(self._html_search_regex(
            r'<span><[^>]+class="icon-chart-bar".*?>(\d+)</span>',
            webpage, 'view count', fatal=False))
        description = self._html_search_regex(
            r'(?s)<pre[^>]+id="lyrics-original"[^>]*>(.*?)</pre>',
            webpage, 'song lyrics', fatal=False)
        if description:
            description = re.sub(' *\r *', '\n', description)

        k = self._search_regex(
            r'<div[^>]+id="player-bottom"[^>]+data-k="([^"]+)">', webpage,
            'encoded data')
        h = time.time() / 3600
        a = sum(map(int, [compat_ord(c) for c in k])) + int(video_id) + h
        video_url = 'http://x-minus.me/dl/minus?id=%s&tkn2=%df%d' % (video_id, a, h)

        return {
            'id': video_id,
            'title': title,
            'url': video_url,
            # The extension is unknown until actual downloading
            'ext': 'mp3',
            'duration': duration,
            'filesize_approx': filesize_approx,
            'tbr': tbr,
            'view_count': view_count,
            'description': description,
        }
