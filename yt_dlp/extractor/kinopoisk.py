# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    dict_get,
    int_or_none,
)


class KinoPoiskIE(InfoExtractor):
    _GEO_COUNTRIES = ['RU']
    _VALID_URL = r'https?://(?:www\.)?kinopoisk\.ru/film/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.kinopoisk.ru/film/81041/watch/',
        'md5': '4f71c80baea10dfa54a837a46111d326',
        'info_dict': {
            'id': '81041',
            'ext': 'mp4',
            'title': 'Алеша попович и тугарин змей',
            'description': 'md5:43787e673d68b805d0aa1df5a5aea701',
            'thumbnail': r're:^https?://.*',
            'duration': 4533,
            'age_limit': 12,
        },
    }, {
        'url': 'https://www.kinopoisk.ru/film/81041',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(
            'https://ott-widget.kinopoisk.ru/v1/kp/', video_id,
            query={'kpId': video_id})

        data = self._parse_json(
            self._search_regex(
                r'(?s)<script[^>]+\btype=["\']application/json[^>]+>(.+?)<',
                webpage, 'data'),
            video_id)['models']

        film = data['filmStatus']
        title = film.get('title') or film['originalTitle']

        formats = self._extract_m3u8_formats(
            data['playlistEntity']['uri'], video_id, 'mp4',
            entry_protocol='m3u8_native', m3u8_id='hls')
        self._sort_formats(formats)

        description = dict_get(
            film, ('descriptscription', 'description',
                   'shortDescriptscription', 'shortDescription'))
        thumbnail = film.get('coverUrl') or film.get('posterUrl')
        duration = int_or_none(film.get('duration'))
        age_limit = int_or_none(film.get('restrictionAge'))

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'age_limit': age_limit,
            'formats': formats,
        }
