# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    unified_timestamp,
)


class Zaq1IE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?zaq1\.pl/video/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'http://zaq1.pl/video/xev0e',
        'md5': '24a5eb3f052e604ae597c4d0d19b351e',
        'info_dict': {
            'id': 'xev0e',
            'title': 'DJ NA WESELE. TANIEC Z FIGURAMI.węgrów/sokołów podlaski/siedlce/mińsk mazowiecki/warszawa',
            'description': 'www.facebook.com/weseledjKontakt: 728 448 199 / 505 419 147',
            'ext': 'mp4',
            'duration': 511,
            'timestamp': 1490896361,
            'uploader': 'Anonim',
            'upload_date': '20170330',
            'view_count': int,
        }
    }, {
        # malformed JSON-LD
        'url': 'http://zaq1.pl/video/x81vn',
        'info_dict': {
            'id': 'x81vn',
            'title': 'SEKRETNE ŻYCIE WALTERA MITTY',
            'ext': 'mp4',
            'duration': 6234,
            'timestamp': 1493494860,
            'uploader': 'Anonim',
            'upload_date': '20170429',
            'view_count': int,
        },
        'params': {
            'skip_download': True,
        },
        'expected_warnings': ['Failed to parse JSON'],
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        video_url = self._search_regex(
            r'data-video-url=(["\'])(?P<url>(?:(?!\1).)+)\1', webpage,
            'video url', group='url')

        info = self._search_json_ld(webpage, video_id, fatal=False)

        def extract_data(field, name, fatal=False):
            return self._search_regex(
                r'data-%s=(["\'])(?P<field>(?:(?!\1).)+)\1' % field,
                webpage, field, fatal=fatal, group='field')

        if not info.get('title'):
            info['title'] = extract_data('file-name', 'title', fatal=True)

        if not info.get('duration'):
            info['duration'] = int_or_none(extract_data('duration', 'duration'))

        if not info.get('thumbnail'):
            info['thumbnail'] = extract_data('photo-url', 'thumbnail')

        if not info.get('timestamp'):
            info['timestamp'] = unified_timestamp(self._html_search_meta(
                'uploadDate', webpage, 'timestamp'))

        if not info.get('interactionCount'):
            info['view_count'] = int_or_none(self._html_search_meta(
                'interactionCount', webpage, 'view count'))

        uploader = self._html_search_regex(
            r'Wideo dodał:\s*<a[^>]*>([^<]+)</a>', webpage, 'uploader',
            fatal=False)

        width = int_or_none(self._html_search_meta(
            'width', webpage, fatal=False))
        height = int_or_none(self._html_search_meta(
            'height', webpage, fatal=False))

        info.update({
            'id': video_id,
            'formats': [{
                'url': video_url,
                'width': width,
                'height': height,
                'http_headers': {
                    'Referer': url,
                },
            }],
            'uploader': uploader,
        })

        return info
