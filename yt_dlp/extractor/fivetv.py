# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import int_or_none


class FiveTVIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.)?5-tv\.ru/
                        (?:
                            (?:[^/]+/)+(?P<id>\d+)|
                            (?P<path>[^/?#]+)(?:[/?#])?
                        )
                    '''

    _TESTS = [{
        'url': 'http://5-tv.ru/news/96814/',
        'md5': 'bbff554ad415ecf5416a2f48c22d9283',
        'info_dict': {
            'id': '96814',
            'ext': 'mp4',
            'title': 'Россияне выбрали имя для общенациональной платежной системы',
            'description': 'md5:a8aa13e2b7ad36789e9f77a74b6de660',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 180,
        },
    }, {
        'url': 'http://5-tv.ru/video/1021729/',
        'info_dict': {
            'id': '1021729',
            'ext': 'mp4',
            'title': '3D принтер',
            'description': 'md5:d76c736d29ef7ec5c0cf7d7c65ffcb41',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 180,
        },
    }, {
        # redirect to https://www.5-tv.ru/projects/1000095/izvestia-glavnoe/
        'url': 'http://www.5-tv.ru/glavnoe/#itemDetails',
        'info_dict': {
            'id': 'glavnoe',
            'ext': 'mp4',
            'title': r're:^Итоги недели с \d+ по \d+ \w+ \d{4} года$',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
        'skip': 'redirect to «Известия. Главное» project page',
    }, {
        'url': 'http://www.5-tv.ru/glavnoe/broadcasts/508645/',
        'only_matching': True,
    }, {
        'url': 'http://5-tv.ru/films/1507502/',
        'only_matching': True,
    }, {
        'url': 'http://5-tv.ru/programs/broadcast/508713/',
        'only_matching': True,
    }, {
        'url': 'http://5-tv.ru/angel/',
        'only_matching': True,
    }, {
        'url': 'http://www.5-tv.ru/schedule/?iframe=true&width=900&height=450',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id') or mobj.group('path')

        webpage = self._download_webpage(url, video_id)

        video_url = self._search_regex(
            [r'<div[^>]+?class="(?:flow)?player[^>]+?data-href="([^"]+)"',
             r'<a[^>]+?href="([^"]+)"[^>]+?class="videoplayer"'],
            webpage, 'video url')

        title = self._og_search_title(webpage, default=None) or self._search_regex(
            r'<title>([^<]+)</title>', webpage, 'title')
        duration = int_or_none(self._og_search_property(
            'video:duration', webpage, 'duration', default=None))

        return {
            'id': video_id,
            'url': video_url,
            'title': title,
            'description': self._og_search_description(webpage, default=None),
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'duration': duration,
        }
