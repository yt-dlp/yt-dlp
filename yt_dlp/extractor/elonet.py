# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    try_get,
)
from ..compat import compat_str


class ElonetIE(InfoExtractor):
    _VALID_URL = r'https?://elonet\.finna\.fi/Record/kavi\.elonet_elokuva_(?P<id>[0-9]+)'
    _TESTS = [{
        # m3u8 with subtitles
        'url': 'https://elonet.finna.fi/Record/kavi.elonet_elokuva_107867',
        'md5': '8efc954b96c543711707f87de757caea',
        'info_dict': {
            'id': '107867',
            'ext': 'mp4',
            'title': 'Valkoinen peura',
            'description': 'Valkoinen peura (1952) on Erik Blombergin ohjaama ja yhdessä Mirjami Kuosmasen kanssa käsikirjoittama tarunomainen kertomus valkoisen peuran hahmossa lii...',
            'thumbnail': 'https://elonet.finna.fi/Cover/Show?id=kavi.elonet_elokuva_107867&index=0&size=large&source=Solr',
        },
        'skip': 'Site no longer provides m3u8 streams',
    }, {
        # DASH with subtitles
        'url': 'https://elonet.finna.fi/Record/kavi.elonet_elokuva_116539',
        'info_dict': {
            'id': '116539',
            'ext': 'mp4',
            'title': 'Minulla on tiikeri',
            'description': 'Pienellä pojalla, joka asuu kerrostalossa, on kotieläimenä tiikeri. Se on kuitenkin salaisuus. Kerrostalon räpätäti on Kotilaisen täti, joka on aina vali...',
            'thumbnail': 'https://elonet.finna.fi/Cover/Show?id=kavi.elonet_elokuva_116539&index=0&size=large&source=Solr',
            'manifest_stream_number': 5,
        },
        'params': {
            # AssertionError: Expected test_Elonet_116539.mp4 to be at least 9.77KiB, but it's only 840.00B
            'skip_download': True,
        },
    }, {
        # Page with multiple videos, download the main one
        'url': 'https://elonet.finna.fi/Record/kavi.elonet_elokuva_117396',
        'info_dict': {
            'id': '117396',
            'ext': 'mp4',
            'title': 'Sampo',
            'description': 'Aleksandr Ptushkon ohjaama, neuvostoliittolais-suomalainen yhteistuotanto Sampo (1959) on Kalevalan tarustoon pohjautuva fantasiaelokuva. Pohjolan emäntä...',
            'thumbnail': 'https://elonet.finna.fi/Cover/Show?id=kavi.elonet_elokuva_117396&index=0&size=large&source=Solr',
            'manifest_stream_number': 3,
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._html_search_regex(
            r'<meta .*property="og&#x3A;title" .*content="(.+?)"', webpage, 'title')
        description = self._html_search_regex(
            r'<meta .*property="og&#x3A;description" .*content="(.+?)"', webpage, 'description')
        thumbnail = self._html_search_regex(
            r'<meta .*property="og&#x3A;image" .*content="(.+?)"', webpage, 'thumbnail')

        json_s = self._html_search_regex(
            r'id=\'video-data\'.+?data-video-sources="(.+?)"', webpage, 'json')
        src = try_get(
            self._parse_json(json_s, video_id),
            lambda x: x[0]["src"], compat_str)

        formats = []
        subtitles = {}
        if re.search(r'\.m3u8\??', src):
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(src, video_id, fatal=False)
            for f in formats:
                f['ext'] = 'mp4'
        elif re.search(r'\.mpd\??', src):
            formats, subtitles = self._extract_mpd_formats_and_subtitles(src, video_id, fatal=False)
        else:
            raise ExtractorError("Unknown streaming format")
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'formats': formats,
            'subtitles': subtitles,
        }
