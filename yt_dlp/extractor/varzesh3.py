# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    clean_html,
    parse_qs,
    remove_start,
)


class Varzesh3IE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?video\.varzesh3\.com/(?:[^/]+/)+(?P<id>[^/]+)/?'
    _TESTS = [{
        'url': 'http://video.varzesh3.com/germany/bundesliga/5-%D9%88%D8%A7%DA%A9%D9%86%D8%B4-%D8%A8%D8%B1%D8%AA%D8%B1-%D8%AF%D8%B1%D9%88%D8%A7%D8%B2%D9%87%E2%80%8C%D8%A8%D8%A7%D9%86%D8%A7%D9%86%D8%9B%D9%87%D9%81%D8%AA%D9%87-26-%D8%A8%D9%88%D9%86%D8%AF%D8%B3/',
        'md5': '2a933874cb7dce4366075281eb49e855',
        'info_dict': {
            'id': '76337',
            'ext': 'mp4',
            'title': '۵ واکنش برتر دروازه‌بانان؛هفته ۲۶ بوندسلیگا',
            'description': 'فصل ۲۰۱۵-۲۰۱۴',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
        'skip': 'HTTP 404 Error',
    }, {
        'url': 'http://video.varzesh3.com/video/112785/%D8%AF%D9%84%D9%87-%D8%B9%D9%84%DB%8C%D8%9B-%D8%B3%D8%AA%D8%A7%D8%B1%D9%87-%D9%86%D9%88%D8%B8%D9%87%D9%88%D8%B1-%D9%84%DB%8C%DA%AF-%D8%A8%D8%B1%D8%AA%D8%B1-%D8%AC%D8%B2%DB%8C%D8%B1%D9%87',
        'md5': '841b7cd3afbc76e61708d94e53a4a4e7',
        'info_dict': {
            'id': '112785',
            'ext': 'mp4',
            'title': 'دله علی؛ ستاره نوظهور لیگ برتر جزیره',
            'description': 'فوتبال 120',
        },
        'expected_warnings': ['description'],
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        video_url = self._search_regex(
            r'<source[^>]+src="([^"]+)"', webpage, 'video url')

        title = remove_start(self._html_search_regex(
            r'<title>([^<]+)</title>', webpage, 'title'), 'ویدیو ورزش 3 | ')

        description = self._html_search_regex(
            r'(?s)<div class="matn">(.+?)</div>',
            webpage, 'description', default=None)
        if description is None:
            description = clean_html(self._html_search_meta('description', webpage))

        thumbnail = self._og_search_thumbnail(webpage, default=None)
        if thumbnail is None:
            fb_sharer_url = self._search_regex(
                r'<a[^>]+href="(https?://www\.facebook\.com/sharer/sharer\.php?[^"]+)"',
                webpage, 'facebook sharer URL', fatal=False)
            sharer_params = parse_qs(fb_sharer_url)
            thumbnail = sharer_params.get('p[images][0]', [None])[0]

        video_id = self._search_regex(
            r"<link[^>]+rel='(?:canonical|shortlink)'[^>]+href='/\?p=([^']+)'",
            webpage, display_id, default=None)
        if video_id is None:
            video_id = self._search_regex(
                r'var\s+VideoId\s*=\s*(\d+);', webpage, 'video id',
                default=display_id)

        return {
            'url': video_url,
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
        }
