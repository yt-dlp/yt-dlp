# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    decode_packed_codes,
    js_to_json,
    NO_DEFAULT,
    PACKED_CODES_RE,
)


class VidziIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?vidzi\.(?:tv|cc|si|nu)/(?:embed-)?(?P<id>[0-9a-zA-Z]+)'
    _TESTS = [{
        'url': 'http://vidzi.tv/cghql9yq6emu.html',
        'md5': '4f16c71ca0c8c8635ab6932b5f3f1660',
        'info_dict': {
            'id': 'cghql9yq6emu',
            'ext': 'mp4',
            'title': 'youtube-dl test video  1\\\\2\'3/4<5\\\\6ä7↭',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'http://vidzi.tv/embed-4z2yb0rzphe9-600x338.html',
        'only_matching': True,
    }, {
        'url': 'http://vidzi.cc/cghql9yq6emu.html',
        'only_matching': True,
    }, {
        'url': 'https://vidzi.si/rph9gztxj1et.html',
        'only_matching': True,
    }, {
        'url': 'http://vidzi.nu/cghql9yq6emu.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(
            'http://vidzi.tv/%s' % video_id, video_id)
        title = self._html_search_regex(
            r'(?s)<h2 class="video-title">(.*?)</h2>', webpage, 'title')

        codes = [webpage]
        codes.extend([
            decode_packed_codes(mobj.group(0)).replace('\\\'', '\'')
            for mobj in re.finditer(PACKED_CODES_RE, webpage)])
        for num, code in enumerate(codes, 1):
            jwplayer_data = self._parse_json(
                self._search_regex(
                    r'setup\(([^)]+)\)', code, 'jwplayer data',
                    default=NO_DEFAULT if num == len(codes) else '{}'),
                video_id, transform_source=lambda s: js_to_json(
                    re.sub(r'\s*\+\s*window\[.+?\]', '', s)))
            if jwplayer_data:
                break

        info_dict = self._parse_jwplayer_data(jwplayer_data, video_id, require_title=False)
        info_dict['title'] = title

        return info_dict
