from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    ExtractorError,
    int_or_none,
    js_to_json,
    merge_dicts,
    urljoin,
)


class PornHdIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?pornhd\.com/(?:[a-z]{2,4}/)?videos/(?P<id>\d+)(?:/(?P<display_id>.+))?'
    _TESTS = [{
        'url': 'http://www.pornhd.com/videos/9864/selfie-restroom-masturbation-fun-with-chubby-cutie-hd-porn-video',
        'md5': '87f1540746c1d32ec7a2305c12b96b25',
        'info_dict': {
            'id': '9864',
            'display_id': 'selfie-restroom-masturbation-fun-with-chubby-cutie-hd-porn-video',
            'ext': 'mp4',
            'title': 'Restroom selfie masturbation',
            'description': 'md5:3748420395e03e31ac96857a8f125b2b',
            'thumbnail': r're:^https?://.*\.jpg',
            'view_count': int,
            'like_count': int,
            'age_limit': 18,
        },
        'skip': 'HTTP Error 404: Not Found',
    }, {
        'url': 'http://www.pornhd.com/videos/1962/sierra-day-gets-his-cum-all-over-herself-hd-porn-video',
        'md5': '1b7b3a40b9d65a8e5b25f7ab9ee6d6de',
        'info_dict': {
            'id': '1962',
            'display_id': 'sierra-day-gets-his-cum-all-over-herself-hd-porn-video',
            'ext': 'mp4',
            'title': 'md5:98c6f8b2d9c229d0f0fde47f61a1a759',
            'description': 'md5:8ff0523848ac2b8f9b065ba781ccf294',
            'thumbnail': r're:^https?://.*\.jpg',
            'view_count': int,
            'like_count': int,
            'age_limit': 18,
        },
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id')
        display_id = mobj.group('display_id')

        webpage = self._download_webpage(url, display_id or video_id)

        title = self._html_search_regex(
            [r'<span[^>]+class=["\']video-name["\'][^>]*>([^<]+)',
             r'<title>(.+?) - .*?[Pp]ornHD.*?</title>'], webpage, 'title')

        sources = self._parse_json(js_to_json(self._search_regex(
            r"(?s)sources'?\s*[:=]\s*(\{.+?\})",
            webpage, 'sources', default='{}')), video_id)

        info = {}
        if not sources:
            entries = self._parse_html5_media_entries(url, webpage, video_id)
            if entries:
                info = entries[0]

        if not sources and not info:
            message = self._html_search_regex(
                r'(?s)<(div|p)[^>]+class="no-video"[^>]*>(?P<value>.+?)</\1',
                webpage, 'error message', group='value')
            raise ExtractorError('%s said: %s' % (self.IE_NAME, message), expected=True)

        formats = []
        for format_id, video_url in sources.items():
            video_url = urljoin(url, video_url)
            if not video_url:
                continue
            height = int_or_none(self._search_regex(
                r'^(\d+)[pP]', format_id, 'height', default=None))
            formats.append({
                'url': video_url,
                'ext': determine_ext(video_url, 'mp4'),
                'format_id': format_id,
                'height': height,
            })
        if formats:
            info['formats'] = formats
        self._sort_formats(info['formats'])

        description = self._html_search_regex(
            (r'(?s)<section[^>]+class=["\']video-description[^>]+>(?P<value>.+?)</section>',
             r'<(div|p)[^>]+class="description"[^>]*>(?P<value>[^<]+)</\1'),
            webpage, 'description', fatal=False,
            group='value') or self._html_search_meta(
            'description', webpage, default=None) or self._og_search_description(webpage)
        view_count = int_or_none(self._html_search_regex(
            r'(\d+) views\s*<', webpage, 'view count', fatal=False))
        thumbnail = self._search_regex(
            r"poster'?\s*:\s*([\"'])(?P<url>(?:(?!\1).)+)\1", webpage,
            'thumbnail', default=None, group='url')

        like_count = int_or_none(self._search_regex(
            (r'(\d+)</span>\s*likes',
             r'(\d+)\s*</11[^>]+>(?:&nbsp;|\s)*\blikes',
             r'class=["\']save-count["\'][^>]*>\s*(\d+)'),
            webpage, 'like count', fatal=False))

        return merge_dicts(info, {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'view_count': view_count,
            'like_count': like_count,
            'formats': formats,
            'age_limit': 18,
        })
