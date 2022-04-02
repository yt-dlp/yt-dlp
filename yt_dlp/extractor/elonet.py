# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    try_get,
)
from ..compat import compat_str


class ElonetIE(InfoExtractor):
    _VALID_URL = r'https?://elonet\.finna\.fi/Record/kavi\.elonet_elokuva_(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://elonet.finna.fi/Record/kavi.elonet_elokuva_107867',
        'md5': '17d2a9be862e88a8657a03253fe32636',
        'info_dict': {
            'id': '107867',
            'ext': 'mp4',
            'title': 'Valkoinen peura',
            'description': 'Valkoinen peura (1952) on Erik Blombergin ohjaama ja yhdessä Mirjami Kuosmasen kanssa käsikirjoittama tarunomainen kertomus valkoisen peuran hahmossa lii...',
            'thumbnail': r're:^https?://elonet\.finna\.fi/Cover/Show\?id=kavi\.elonet_elokuva_107867.+',
        },
        'params': {
            'skip_download': 'dash',
        },
    }, {
        # DASH with subtitles
        'url': 'https://elonet.finna.fi/Record/kavi.elonet_elokuva_116539',
        'md5': '17d2a9be862e88a8657a03253fe32636',
        'info_dict': {
            'id': '116539',
            'ext': 'mp4',
            'title': 'Minulla on tiikeri',
            'description': 'Pienellä pojalla, joka asuu kerrostalossa, on kotieläimenä tiikeri. Se on kuitenkin salaisuus. Kerrostalon räpätäti on Kotilaisen täti, joka on aina vali...',
            'thumbnail': r're:^https?://elonet\.finna\.fi/Cover/Show\?id=kavi\.elonet_elokuva_116539.+',
        },
        'params': {
            'skip_download': 'dash',
        },
    }, {
        # Page with multiple videos, download the main one
        'url': 'https://elonet.finna.fi/Record/kavi.elonet_elokuva_117396',
        'md5': '17d2a9be862e88a8657a03253fe32636',
        'info_dict': {
            'id': '117396',
            'ext': 'mp4',
            'title': 'Sampo',
            'description': 'Aleksandr Ptushkon ohjaama, neuvostoliittolais-suomalainen yhteistuotanto Sampo (1959) on Kalevalan tarustoon pohjautuva fantasiaelokuva. Pohjolan emäntä...',
            'thumbnail': r're:^https?://elonet\.finna\.fi/Cover/Show\?id=kavi\.elonet_elokuva_117396.+',
        },
        'params': {
            'skip_download': 'dash',
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
            r'id=\'video-data\'[^>]+data-video-sources="(.+?)"', webpage, 'json')
        src = try_get(
            self._parse_json(json_s, video_id),
            lambda x: x[0]["src"], compat_str)

        formats = []
        subtitles = {}

        ext = determine_ext(src)
        if ext == 'm3u8':
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(src, video_id, fatal=False)
        elif ext == 'mpd':
            formats, subtitles = self._extract_mpd_formats_and_subtitles(src, video_id, fatal=False)
        else:
            self.report_warning('Unknown streaming format %s' % ext)
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'formats': formats,
            'subtitles': subtitles,
        }
