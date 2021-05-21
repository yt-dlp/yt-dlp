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
)


class ShemarooMeIE(InfoExtractor):
    _VALID_URL = r'(?:https?://)(?:www\.)?shemaroome\.com/(?:movies|shows)/(?P<id>\S+)'
    _TESTS = [{
        'url': 'https://www.shemaroome.com/movies/dil-hai-tumhaara',
        'info_dict': {
            'id': 'dil-hai-tumhaara',
            'ext': 'mp4',
            'title': 'Dil Hai Tumhaara',
            'release_date': '2002-09-06',
            'thumbnail': 'https://daex9l847wg3n.cloudfront.net/shemoutputimages/Dil-Hai-Tumhaara/60599346a609d2faa3000020/large_16_9_1616436538.jpg?1616483693',
            'description': "A chirpy young girl Shalu craves for the love of her mother Sarita, but Sarita is partial towards her elder daughter Nimmi. Shalu is in love with her employer's son, Dev, but when Sarita proposes Nimmi's marriage to Dev, Shalu is forced to choose between her mother's acceptance and Dev's love. Matters worsen when Shalu is told the truth about her heritage.",
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        params_pattern = r'params_for_player\ =\ \"(?P<data>[^|]+)\|key=(?P<key>[^|]+)\|image=(?P<thumbnail>[^|]+)\|title=(?P<title>[^|]+)'
        m = re.search(params_pattern, webpage)
        data = bytes_to_intlist(compat_b64decode(m.group('data')))
        key = bytes_to_intlist(compat_b64decode(m.group('key')))
        iv = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        m3u8_url = intlist_to_bytes(aes_cbc_decrypt(data, key, iv))
        m3u8_url = m3u8_url[:-compat_ord((m3u8_url[-1]))].decode('ascii')
        formats = self._extract_m3u8_formats(m3u8_url, video_id, fatal=False)
        self._sort_formats(formats)
        release_date = self._html_search_regex(r'\<span\ itemprop\=\"uploadDate\"\>(?P<uploaddate>\S+)\<\/span\>',
                                               webpage, 'release_date', default="NA", fatal=False)
        description = self._html_search_regex(r'\<p\ class\=\"float-left\ w-100\ app-color1\ font-regular\"\>(?P<description>[^\<]+)\<\/p\>',
                                              webpage, 'description', default="NA", fatal=False)
        return {
            'id': video_id,
            'formats': formats,
            'title': m.group('title'),
            'thumbnail': m.group('thumbnail'),
            'release_date': release_date,
            'description': description,
        }
