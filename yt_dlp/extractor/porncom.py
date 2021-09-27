from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_urlparse
from ..utils import (
    int_or_none,
    js_to_json,
    parse_filesize,
    str_to_int,
)


class PornComIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[a-zA-Z]+\.)?porn\.com/videos/(?:(?P<display_id>[^/]+)-)?(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.porn.com/videos/teen-grabs-a-dildo-and-fucks-her-pussy-live-on-1hottie-i-rec-2603339',
        'md5': '3f30ce76267533cd12ba999263156de7',
        'info_dict': {
            'id': '2603339',
            'display_id': 'teen-grabs-a-dildo-and-fucks-her-pussy-live-on-1hottie-i-rec',
            'ext': 'mp4',
            'title': 'Teen grabs a dildo and fucks her pussy live on 1hottie, I rec',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 551,
            'view_count': int,
            'age_limit': 18,
            'categories': list,
            'tags': list,
        },
    }, {
        'url': 'http://se.porn.com/videos/marsha-may-rides-seth-on-top-of-his-thick-cock-2658067',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        display_id = mobj.group('display_id') or video_id

        webpage = self._download_webpage(url, display_id)

        config = self._parse_json(
            self._search_regex(
                (r'=\s*({.+?})\s*;\s*v1ar\b',
                 r'=\s*({.+?})\s*,\s*[\da-zA-Z_]+\s*='),
                webpage, 'config', default='{}'),
            display_id, transform_source=js_to_json, fatal=False)

        if config:
            title = config['title']
            formats = [{
                'url': stream['url'],
                'format_id': stream.get('id'),
                'height': int_or_none(self._search_regex(
                    r'^(\d+)[pP]', stream.get('id') or '', 'height', default=None))
            } for stream in config['streams'] if stream.get('url')]
            thumbnail = (compat_urlparse.urljoin(
                config['thumbCDN'], config['poster'])
                if config.get('thumbCDN') and config.get('poster') else None)
            duration = int_or_none(config.get('length'))
        else:
            title = self._search_regex(
                (r'<title>([^<]+)</title>', r'<h1[^>]*>([^<]+)</h1>'),
                webpage, 'title')
            formats = [{
                'url': compat_urlparse.urljoin(url, format_url),
                'format_id': '%sp' % height,
                'height': int(height),
                'filesize_approx': parse_filesize(filesize),
            } for format_url, height, filesize in re.findall(
                r'<a[^>]+href="(/download/[^"]+)">[^<]*?(\d+)p<span[^>]*>(\d+\s*[a-zA-Z]+)<',
                webpage)]
            thumbnail = None
            duration = None

        self._sort_formats(formats)

        view_count = str_to_int(self._search_regex(
            (r'Views:\s*</span>\s*<span>\s*([\d,.]+)',
             r'class=["\']views["\'][^>]*><p>([\d,.]+)'), webpage,
            'view count', fatal=False))

        def extract_list(kind):
            s = self._search_regex(
                (r'(?s)%s:\s*</span>\s*<span>(.+?)</span>' % kind.capitalize(),
                 r'(?s)<p[^>]*>%s:(.+?)</p>' % kind.capitalize()),
                webpage, kind, fatal=False)
            return re.findall(r'<a[^>]+>([^<]+)</a>', s or '')

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'thumbnail': thumbnail,
            'duration': duration,
            'view_count': view_count,
            'formats': formats,
            'age_limit': 18,
            'categories': extract_list('categories'),
            'tags': extract_list('tags'),
        }
