# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    base_url,
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
            'thumbnail': 'https://elonet.finna.fi/Cover/Show?id=kavi.elonet_elokuva_107867&index=0&size=large',
        },
    }, {
        # DASH with subtitles
        'url': 'https://elonet.finna.fi/Record/kavi.elonet_elokuva_116539',
        'info_dict': {
            'id': '116539',
            'ext': 'mp4',
            'title': 'Minulla on tiikeri',
            'description': 'Pienellä pojalla, joka asuu kerrostalossa, on kotieläimenä tiikeri. Se on kuitenkin salaisuus. Kerrostalon räpätäti on Kotilaisen täti, joka on aina vali...',
            'thumbnail': 'https://elonet.finna.fi/Cover/Show?id=kavi.elonet_elokuva_116539&index=0&size=large&source=Solr',
        }
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
            r'data-video-sources="(.+?)"', webpage, 'json')
        src = try_get(
            self._parse_json(json_s, video_id),
            lambda x: x[0]["src"], compat_str)
        formats = []
        subtitles = {}
        if re.search(r'\.m3u8\??', src):
            res = self._download_webpage_handle(
                # elonet servers have certificate problems
                src.replace('https:', 'http:'), video_id,
                note='Downloading m3u8 information',
                errnote='Failed to download m3u8 information')
            if res:
                doc, urlh = res
                url = urlh.geturl()
                formats, subtitles = self._parse_m3u8_formats_and_subtitles(doc, url)
                for f in formats:
                    f['ext'] = 'mp4'
        elif re.search(r'\.mpd\??', src):
            res = self._download_xml_handle(
                src, video_id,
                note='Downloading MPD manifest',
                errnote='Failed to download MPD manifest')
            if res:
                doc, urlh = res
                url = base_url(urlh.geturl())
                formats, subtitles = self._parse_mpd_formats_and_subtitles(doc, mpd_base_url=url)
        else:
            raise ExtractorError("Unknown streaming format")

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'formats': formats,
            'subtitles': subtitles,
        }
