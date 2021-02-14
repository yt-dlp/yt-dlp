# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_filesize,
    unified_strdate,
)


class XboxClipsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?xboxclips\.com/(?:video\.php\?.*vid=|[^/]+/)(?P<id>[\w-]{36})'
    _TEST = {
        'url': 'http://xboxclips.com/video.php?uid=2533274823424419&gamertag=Iabdulelah&vid=074a69a9-5faf-46aa-b93b-9909c1720325',
        'md5': 'fbe1ec805e920aeb8eced3c3e657df5d',
        'info_dict': {
            'id': '074a69a9-5faf-46aa-b93b-9909c1720325',
            'ext': 'mp4',
            'title': 'Iabdulelah playing Titanfall',
            'filesize_approx': 26800000,
            'upload_date': '20140807',
            'duration': 56,
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        video_url = self._html_search_regex(
            r'>(?:Link|Download): <a[^>]+href="([^"]+)"', webpage, 'video URL')
        title = self._html_search_regex(
            r'<title>XboxClips \| ([^<]+)</title>', webpage, 'title')
        upload_date = unified_strdate(self._html_search_regex(
            r'>Recorded: ([^<]+)<', webpage, 'upload date', fatal=False))
        filesize = parse_filesize(self._html_search_regex(
            r'>Size: ([^<]+)<', webpage, 'file size', fatal=False))
        duration = int_or_none(self._html_search_regex(
            r'>Duration: (\d+) Seconds<', webpage, 'duration', fatal=False))
        view_count = int_or_none(self._html_search_regex(
            r'>Views: (\d+)<', webpage, 'view count', fatal=False))

        return {
            'id': video_id,
            'url': video_url,
            'title': title,
            'upload_date': upload_date,
            'filesize_approx': filesize,
            'duration': duration,
            'view_count': view_count,
        }
