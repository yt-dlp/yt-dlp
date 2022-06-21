import re

from ..utils import (
    int_or_none,
    str_to_int,
)
from .keezmovies import KeezMoviesIE


class Tube8IE(KeezMoviesIE):
    _VALID_URL = r'https?://(?:www\.)?tube8\.com/(?:[^/]+/)+(?P<display_id>[^/]+)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.tube8.com/teen/kasia-music-video/229795/',
        'md5': '65e20c48e6abff62ed0c3965fff13a39',
        'info_dict': {
            'id': '229795',
            'display_id': 'kasia-music-video',
            'ext': 'mp4',
            'description': 'hot teen Kasia grinding',
            'uploader': 'unknown',
            'title': 'Kasia music video',
            'age_limit': 18,
            'duration': 230,
            'categories': ['Teen'],
            'tags': ['dancing'],
        },
    }, {
        'url': 'http://www.tube8.com/shemale/teen/blonde-cd-gets-kidnapped-by-two-blacks-and-punished-for-being-a-slutty-girl/19569151/',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_urls(webpage):
        return re.findall(
            r'<iframe[^>]+\bsrc=["\']((?:https?:)?//(?:www\.)?tube8\.com/embed/(?:[^/]+/)+\d+)',
            webpage)

    def _real_extract(self, url):
        webpage, info = self._extract_info(url)

        if not info['title']:
            info['title'] = self._html_search_regex(
                r'videoTitle\s*=\s*"([^"]+)', webpage, 'title')

        description = self._html_search_regex(
            r'(?s)Description:</dt>\s*<dd>(.+?)</dd>', webpage, 'description', fatal=False)
        uploader = self._html_search_regex(
            r'<span class="username">\s*(.+?)\s*<',
            webpage, 'uploader', fatal=False)

        like_count = int_or_none(self._search_regex(
            r'rupVar\s*=\s*"(\d+)"', webpage, 'like count', fatal=False))
        dislike_count = int_or_none(self._search_regex(
            r'rdownVar\s*=\s*"(\d+)"', webpage, 'dislike count', fatal=False))
        view_count = str_to_int(self._search_regex(
            r'Views:\s*</dt>\s*<dd>([\d,\.]+)',
            webpage, 'view count', fatal=False))
        comment_count = str_to_int(self._search_regex(
            r'<span id="allCommentsCount">(\d+)</span>',
            webpage, 'comment count', fatal=False))

        category = self._search_regex(
            r'Category:\s*</dt>\s*<dd>\s*<a[^>]+href=[^>]+>([^<]+)',
            webpage, 'category', fatal=False)
        categories = [category] if category else None

        tags_str = self._search_regex(
            r'(?s)Tags:\s*</dt>\s*<dd>(.+?)</(?!a)',
            webpage, 'tags', fatal=False)
        tags = [t for t in re.findall(
            r'<a[^>]+href=[^>]+>([^<]+)', tags_str)] if tags_str else None

        info.update({
            'description': description,
            'uploader': uploader,
            'view_count': view_count,
            'like_count': like_count,
            'dislike_count': dislike_count,
            'comment_count': comment_count,
            'categories': categories,
            'tags': tags,
        })

        return info
