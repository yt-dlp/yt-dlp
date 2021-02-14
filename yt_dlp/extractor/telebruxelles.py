# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor


class TeleBruxellesIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?:telebruxelles|bx1)\.be/(?:[^/]+/)*(?P<id>[^/#?]+)'
    _TESTS = [{
        'url': 'http://bx1.be/news/que-risque-lauteur-dune-fausse-alerte-a-la-bombe/',
        'md5': 'a2a67a5b1c3e8c9d33109b902f474fd9',
        'info_dict': {
            'id': '158856',
            'display_id': 'que-risque-lauteur-dune-fausse-alerte-a-la-bombe',
            'ext': 'mp4',
            'title': 'Que risque l’auteur d’une fausse alerte à la bombe ?',
            'description': 'md5:3cf8df235d44ebc5426373050840e466',
        },
    }, {
        'url': 'http://bx1.be/sport/futsal-schaerbeek-sincline-5-3-a-thulin/',
        'md5': 'dfe07ecc9c153ceba8582ac912687675',
        'info_dict': {
            'id': '158433',
            'display_id': 'futsal-schaerbeek-sincline-5-3-a-thulin',
            'ext': 'mp4',
            'title': 'Futsal : Schaerbeek s’incline 5-3 à Thulin',
            'description': 'md5:fd013f1488d5e2dceb9cebe39e2d569b',
        },
    }, {
        'url': 'http://bx1.be/emission/bxenf1-gastronomie/',
        'only_matching': True,
    }, {
        'url': 'https://bx1.be/berchem-sainte-agathe/personnel-carrefour-de-berchem-sainte-agathe-inquiet/',
        'only_matching': True,
    }, {
        'url': 'https://bx1.be/dernier-jt/',
        'only_matching': True,
    }, {
        # live stream
        'url': 'https://bx1.be/lives/direct-tv/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        article_id = self._html_search_regex(
            r'<article[^>]+\bid=["\']post-(\d+)', webpage, 'article ID', default=None)
        title = self._html_search_regex(
            r'<h1[^>]*>(.+?)</h1>', webpage, 'title',
            default=None) or self._og_search_title(webpage)
        description = self._og_search_description(webpage, default=None)

        rtmp_url = self._html_search_regex(
            r'file["\']?\s*:\s*"(r(?:tm|mt)ps?://[^/]+/(?:vod/mp4:"\s*\+\s*"[^"]+"\s*\+\s*"\.mp4|stream/live))"',
            webpage, 'RTMP url')
        # Yes, they have a typo in scheme name for live stream URLs (e.g.
        # https://bx1.be/lives/direct-tv/)
        rtmp_url = re.sub(r'^rmtp', 'rtmp', rtmp_url)
        rtmp_url = re.sub(r'"\s*\+\s*"', '', rtmp_url)
        formats = self._extract_wowza_formats(rtmp_url, article_id or display_id)
        self._sort_formats(formats)

        is_live = 'stream/live' in rtmp_url

        return {
            'id': article_id or display_id,
            'display_id': display_id,
            'title': self._live_title(title) if is_live else title,
            'description': description,
            'formats': formats,
            'is_live': is_live,
        }
