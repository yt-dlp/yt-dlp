# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    get_element_by_class,
    strip_or_none,
)


class SeekerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?seeker\.com/(?P<display_id>.*)-(?P<article_id>\d+)\.html'
    _TESTS = [{
        'url': 'http://www.seeker.com/should-trump-be-required-to-release-his-tax-returns-1833805621.html',
        'md5': '897d44bbe0d8986a2ead96de565a92db',
        'info_dict': {
            'id': 'Elrn3gnY',
            'ext': 'mp4',
            'title': 'Should Trump Be Required To Release His Tax Returns?',
            'description': 'md5:41efa8cfa8d627841045eec7b018eb45',
            'timestamp': 1490090165,
            'upload_date': '20170321',
        }
    }, {
        'url': 'http://www.seeker.com/changes-expected-at-zoos-following-recent-gorilla-lion-shootings-1834116536.html',
        'playlist': [
            {
                'md5': '0497b9f20495174be73ae136949707d2',
                'info_dict': {
                    'id': 'FihYQ8AE',
                    'ext': 'mp4',
                    'title': 'The Pros & Cons Of Zoos',
                    'description': 'md5:d88f99a8ea8e7d25e6ff77f271b1271c',
                    'timestamp': 1490039133,
                    'upload_date': '20170320',
                },
            }
        ],
        'info_dict': {
            'id': '1834116536',
            'title': 'After Gorilla Killing, Changes Ahead for Zoos',
            'description': 'The largest association of zoos and others are hoping to learn from recent incidents that led to the shooting deaths of a gorilla and two lions.',
        },
    }]

    def _real_extract(self, url):
        display_id, article_id = re.match(self._VALID_URL, url).groups()
        webpage = self._download_webpage(url, display_id)
        entries = []
        for jwp_id in re.findall(r'data-video-id="([a-zA-Z0-9]{8})"', webpage):
            entries.append(self.url_result(
                'jwplatform:' + jwp_id, 'JWPlatform', jwp_id))
        return self.playlist_result(
            entries, article_id,
            self._og_search_title(webpage),
            strip_or_none(get_element_by_class('subtitle__text', webpage)) or self._og_search_description(webpage))
