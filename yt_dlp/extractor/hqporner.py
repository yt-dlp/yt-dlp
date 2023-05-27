import re

from .common import InfoExtractor
from ..utils import (
    get_element_by_class,
    parse_duration,
    parse_resolution,
    url_or_none,
)


class HqpornerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?hqporner\.com/hdporn/(?P<id>[0-9]+)-(?P<display_id>[^.]+)\.html'
    _TESTS = [{
        'url': 'https://hqporner.com/hdporn/86482-all_night_rager.html',
        'md5': '69cd373eb38aa82209c0450e0b9fc730',
        'info_dict': {
            'id': '86482',
            'title': 'all night rager',
            'display_id': 'all_night_rager',
            'thumbnail': r're:^https?://.*\.jpg$',
            'ext': 'mp4',
            'age_limit': 18,
            'duration': 2434.0,
            'tags': 'count:13'
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        iframe_url = self._html_search_regex(r'<iframe[^>]*src=[\'"]([^\'"]+)[^>]*allowfullscreen',
                                             webpage, 'iframe url')

        iframe_webpage = self._download_webpage(iframe_url, video_id, note='Downloading iframe webpage')

        formats = []
        for mobj in re.finditer(
            r'<source[^>]+src=\\[\'"](?P<url>[^\\]+)\\[\'"][^>]+title=\\[\'"](?P<id>[^\\]+)',
                iframe_webpage):
            format_id, format_url = mobj.group('id', 'url')
            f_url = url_or_none(format_url)
            if not f_url:
                return
            f = parse_resolution(format_id)
            f.update({
                'url': f_url,
                'format_id': format_id,
            })
            formats.append(f)

        return {
            'id': video_id,
            'display_id': self._match_valid_url(url).group('display_id'),
            'title': get_element_by_class('main-h1', webpage).strip(),
            'formats': formats,
            'thumbnail': self._search_regex(r'poster=\\[\'"]([^\\]+)', iframe_webpage, 'thumbnail', fatal=False),
            'age_limit': 18,
            'duration': parse_duration(get_element_by_class('fa-clock-o', webpage)),
            'tags': [mobj.group(1)
                     for mobj in re.finditer(r'<a[^>]+class=[\'"]tag-link click-trigger[\'"]>([^>]+)</a>', webpage)]
        }
