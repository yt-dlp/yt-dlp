from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import (
    compat_urllib_parse_unquote,
    compat_urllib_parse_unquote_plus,
)
from ..utils import (
    clean_html,
    ExtractorError,
)


class PlayvidIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?playvid\.com/watch(\?v=|/)(?P<id>.+?)(?:#|$)'
    _TESTS = [{
        'url': 'http://www.playvid.com/watch/RnmBNgtrrJu',
        'md5': 'ffa2f6b2119af359f544388d8c01eb6c',
        'info_dict': {
            'id': 'RnmBNgtrrJu',
            'ext': 'mp4',
            'title': 'md5:9256d01c6317e3f703848b5906880dc8',
            'duration': 82,
            'age_limit': 18,
        },
        'skip': 'Video removed due to ToS',
    }, {
        'url': 'http://www.playvid.com/watch/hwb0GpNkzgH',
        'md5': '39d49df503ad7b8f23a4432cbf046477',
        'info_dict': {
            'id': 'hwb0GpNkzgH',
            'ext': 'mp4',
            'title': 'Ellen Euro Cutie Blond Takes a Sexy Survey Get Facial in The Park',
            'age_limit': 18,
            'thumbnail': r're:^https?://.*\.jpg$',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        m_error = re.search(
            r'<div class="block-error">\s*<div class="heading">\s*<div>(?P<msg>.+?)</div>\s*</div>', webpage)
        if m_error:
            raise ExtractorError(clean_html(m_error.group('msg')), expected=True)

        video_title = None
        duration = None
        video_thumbnail = None
        formats = []

        # most of the information is stored in the flashvars
        flashvars = self._html_search_regex(
            r'flashvars="(.+?)"', webpage, 'flashvars')

        infos = compat_urllib_parse_unquote(flashvars).split(r'&')
        for info in infos:
            videovars_match = re.match(r'^video_vars\[(.+?)\]=(.+?)$', info)
            if videovars_match:
                key = videovars_match.group(1)
                val = videovars_match.group(2)

                if key == 'title':
                    video_title = compat_urllib_parse_unquote_plus(val)
                if key == 'duration':
                    try:
                        duration = int(val)
                    except ValueError:
                        pass
                if key == 'big_thumb':
                    video_thumbnail = val

                videourl_match = re.match(
                    r'^video_urls\]\[(?P<resolution>[0-9]+)p', key)
                if videourl_match:
                    height = int(videourl_match.group('resolution'))
                    formats.append({
                        'height': height,
                        'url': val,
                    })
        self._sort_formats(formats)

        # Extract title - should be in the flashvars; if not, look elsewhere
        if video_title is None:
            video_title = self._html_search_regex(
                r'<title>(.*?)</title', webpage, 'title')

        return {
            'id': video_id,
            'formats': formats,
            'title': video_title,
            'thumbnail': video_thumbnail,
            'duration': duration,
            'description': None,
            'age_limit': 18
        }
