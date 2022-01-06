# coding: utf-8
from __future__ import unicode_literals
from .common import InfoExtractor
from ..utils import int_or_none


class PornezIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?pornez\.net/video(?P<id>[0-9]+)/'
    _TEST = {
        'url': 'https://pornez.net/video344819/mistresst-funny_penis_names-wmv/',
        'md5': '2e19a0a1cff3a5dbea0ef1b9e80bcbbc',
        'info_dict': {
            'id': '344819',
            'ext': 'mp4',
            'title': r'mistresst funny_penis_names wmv',
            'thumbnail': r're:^https?://.*\.jpg$',
            'age_limit': 18,
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        iframe_src = self._html_search_regex(
            r'<iframe[^>]+src="(https?://pornez\.net/player/\?[^"]+)"', webpage, 'iframe', fatal=True)
        title = self._html_search_meta(['name', 'twitter:title', 'og:title'], webpage, 'title', default=None)
        if title is None:
            title = self._search_regex(r'<h1>(.*?)</h1>', webpage, 'title', fatal=True)
        thumbnail = self._html_search_meta(['thumbnailUrl'], webpage, 'title', default=None)
        webpage = self._download_webpage(iframe_src, video_id)
        entries = self._parse_html5_media_entries(iframe_src, webpage, video_id)[0]
        for format in entries['formats']:
            height = self._search_regex(r'_(\d+)\.m3u8', format['url'], 'height')
            format['format_id'] = '%sp' % height
            format['height'] = int_or_none(height)

        entries.update({
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'age_limit': 18
        })
        return entries
