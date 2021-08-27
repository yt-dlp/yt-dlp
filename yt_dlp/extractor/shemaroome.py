# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..aes import aes_cbc_decrypt
from ..compat import (
    compat_b64decode,
    compat_ord,
)
from ..utils import (
    bytes_to_intlist,
    intlist_to_bytes,
    unified_strdate,
    url_or_none,
)


class ShemarooMeIE(InfoExtractor):
    _VALID_URL = r'(?:https?://)(?:www\.)?shemaroome\.com/(?:movies|shows)/(?P<id>[^?#]+)'
    _TESTS = [{
        'url': 'https://www.shemaroome.com/movies/dil-hai-tumhaara',
        'info_dict': {
            'id': 'dil-hai-tumhaara',
            'ext': 'mp4',
            'title': 'Dil Hai Tumhaara',
            'release_date': '20020906',
            'thumbnail': 'https://daex9l847wg3n.cloudfront.net/shemoutputimages/Dil-Hai-Tumhaara/60599346a609d2faa3000020/large_16_9_1616436538.jpg?1616483693',
            'description': 'md5:2782c4127807103cf5a6ae2ca33645ce',
        },
        'params': {
            'skip_download': True
        }
    }, {
        'url': 'https://www.shemaroome.com/shows/jurm-aur-jazbaat/laalach',
        'info_dict': {
            'id': 'jurm-aur-jazbaat_laalach',
            'ext': 'mp4',
            'title': 'Laalach',
            'description': 'md5:92b79c2dcb539b0ab53f9fa5a048f53c',
            'release_date': '20210507',
        },
        'params': {
            'skip_download': True
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url).replace('/', '_')
        webpage = self._download_webpage(url, video_id)
        m = re.search(
            r'params_for_player\s*=\s*"(?P<data>[^|]+)\|key=(?P<key>[^|]+)\|image=(?P<thumbnail>[^|]+)\|title=(?P<title>[^|]+)',
            webpage)
        data = bytes_to_intlist(compat_b64decode(m.group('data')))
        key = bytes_to_intlist(compat_b64decode(m.group('key')))
        iv = [0] * 16
        m3u8_url = intlist_to_bytes(aes_cbc_decrypt(data, key, iv))
        m3u8_url = m3u8_url[:-compat_ord((m3u8_url[-1]))].decode('ascii')
        formats = self._extract_m3u8_formats(m3u8_url, video_id, fatal=False)
        self._sort_formats(formats)

        release_date = self._html_search_regex(
            (r'itemprop="uploadDate">\s*([\d-]+)', r'id="release_date" value="([\d-]+)'),
            webpage, 'release date', fatal=False)

        description = self._html_search_regex(r'(?s)>Synopsis(</.+?)</', webpage, 'description', fatal=False)

        return {
            'id': video_id,
            'formats': formats,
            'title': m.group('title'),
            'thumbnail': url_or_none(m.group('thumbnail')),
            'release_date': unified_strdate(release_date),
            'description': description,
        }
