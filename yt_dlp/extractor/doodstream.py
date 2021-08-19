# coding: utf-8
from __future__ import unicode_literals

import string
import random
import time

from .common import InfoExtractor


class DoodStreamIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?dood\.(?:to|watch)/[ed]/(?P<id>[a-z0-9]+)'
    _TESTS = [{
        'url': 'http://dood.to/e/5s1wmbdacezb',
        'md5': '4568b83b31e13242b3f1ff96c55f0595',
        'info_dict': {
            'id': '5s1wmbdacezb',
            'ext': 'mp4',
            'title': 'Kat Wonders - Monthly May 2020',
            'description': 'Kat Wonders - Monthly May 2020 | DoodStream.com',
            'thumbnail': 'https://img.doodcdn.com/snaps/flyus84qgl2fsk4g.jpg',
        }
    }, {
        'url': 'https://dood.to/d/jzrxn12t2s7n',
        'md5': '3207e199426eca7c2aa23c2872e6728a',
        'info_dict': {
            'id': 'jzrxn12t2s7n',
            'ext': 'mp4',
            'title': 'Stacy Cruz Cute ALLWAYSWELL',
            'description': 'Stacy Cruz Cute ALLWAYSWELL | DoodStream.com',
            'thumbnail': 'https://img.doodcdn.com/snaps/8edqd5nppkac3x8u.jpg',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        if '/d/' in url:
            url = "https://dood.to" + self._html_search_regex(
                r'<iframe src="(/e/[a-z0-9]+)"', webpage, 'embed')
            video_id = self._match_id(url)
            webpage = self._download_webpage(url, video_id)

        title = self._html_search_meta(['og:title', 'twitter:title'],
                                       webpage, default=None)
        thumb = self._html_search_meta(['og:image', 'twitter:image'],
                                       webpage, default=None)
        token = self._html_search_regex(r'[?&]token=([a-z0-9]+)[&\']', webpage, 'token')
        description = self._html_search_meta(
            ['og:description', 'description', 'twitter:description'],
            webpage, default=None)
        auth_url = 'https://dood.to' + self._html_search_regex(
            r'(/pass_md5.*?)\'', webpage, 'pass_md5')
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:53.0) Gecko/20100101 Firefox/66.0',
            'referer': url
        }

        webpage = self._download_webpage(auth_url, video_id, headers=headers)
        final_url = webpage + ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(10)]) + "?token=" + token + "&expiry=" + str(int(time.time() * 1000))

        return {
            'id': video_id,
            'title': title,
            'url': final_url,
            'http_headers': headers,
            'ext': 'mp4',
            'description': description,
            'thumbnail': thumb,
        }
