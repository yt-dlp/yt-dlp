# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    month_by_abbreviation,
    parse_filesize,
    parse_qs,
)


class XboxClipsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?:xboxclips\.com|gameclips\.io)/(?:video\.php\?.*vid=|[^/]+/)(?P<id>[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12})'
    _TESTS = [{
        'url': 'http://xboxclips.com/video.php?uid=2533274823424419&gamertag=Iabdulelah&vid=074a69a9-5faf-46aa-b93b-9909c1720325',
        'md5': 'fbe1ec805e920aeb8eced3c3e657df5d',
        'info_dict': {
            'id': '074a69a9-5faf-46aa-b93b-9909c1720325',
            'ext': 'mp4',
            'title': 'iAbdulElah playing Titanfall',
            'filesize_approx': 26800000,
            'upload_date': '20140807',
            'duration': 56,
        }
    }, {
        'url': 'https://gameclips.io/iAbdulElah/074a69a9-5faf-46aa-b93b-9909c1720325',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        if '/video.php' in url:
            qs = parse_qs(url)
            url = 'https://gameclips.io/%s/%s' % (qs['gamertag'][0], qs['vid'][0])

        webpage = self._download_webpage(url, video_id)
        info = self._parse_html5_media_entries(url, webpage, video_id)[0]

        title = self._html_search_meta(['og:title', 'twitter:title'], webpage)
        upload_date = None
        mobj = re.search(
            r'>Recorded: (\d{2})-(Jan|Feb|Mar|Apr|May|Ju[nl]|Aug|Sep|Oct|Nov|Dec)-(\d{4})',
            webpage)
        if mobj:
            upload_date = '%s%.2d%s' % (mobj.group(3), month_by_abbreviation(mobj.group(2)), mobj.group(1))
        filesize = parse_filesize(self._html_search_regex(
            r'>Size: ([^<]+)<', webpage, 'file size', fatal=False))
        duration = int_or_none(self._html_search_regex(
            r'>Duration: (\d+) Seconds<', webpage, 'duration', fatal=False))
        view_count = int_or_none(self._html_search_regex(
            r'>Views: (\d+)<', webpage, 'view count', fatal=False))

        info.update({
            'id': video_id,
            'title': title,
            'upload_date': upload_date,
            'filesize_approx': filesize,
            'duration': duration,
            'view_count': view_count,
        })
        return info
