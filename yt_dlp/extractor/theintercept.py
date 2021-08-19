# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    parse_iso8601,
    int_or_none,
    ExtractorError,
)


class TheInterceptIE(InfoExtractor):
    _VALID_URL = r'https?://theintercept\.com/fieldofvision/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://theintercept.com/fieldofvision/thisisacoup-episode-four-surrender-or-die/',
        'md5': '145f28b41d44aab2f87c0a4ac8ec95bd',
        'info_dict': {
            'id': '46214',
            'ext': 'mp4',
            'title': '#ThisIsACoup – Episode Four: Surrender or Die',
            'description': 'md5:74dd27f0e2fbd50817829f97eaa33140',
            'timestamp': 1450429239,
            'upload_date': '20151218',
            'comment_count': int,
        }
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        json_data = self._parse_json(self._search_regex(
            r'initialStoreTree\s*=\s*(?P<json_data>{.+})', webpage,
            'initialStoreTree'), display_id)

        for post in json_data['resources']['posts'].values():
            if post['slug'] == display_id:
                return {
                    '_type': 'url_transparent',
                    'url': 'jwplatform:%s' % post['fov_videoid'],
                    'id': compat_str(post['ID']),
                    'display_id': display_id,
                    'title': post['title'],
                    'description': post.get('excerpt'),
                    'timestamp': parse_iso8601(post.get('date')),
                    'comment_count': int_or_none(post.get('comments_number')),
                }
        raise ExtractorError('Unable to find the current post')
