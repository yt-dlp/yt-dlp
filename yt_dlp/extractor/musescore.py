# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class MuseScoreIE(InfoExtractor):
    _VALID_URL = r'(?:https?://)(?:www\.)?musescore\.com/(?:user/\d+|[^/]+)(?:/scores)?/(?P<id>[^#&?]+)'
    _TESTS = [{
        'url': 'https://musescore.com/minh_cuteee/scores/6555384',
        'info_dict': {
            'id': '6555384',
            'ext': 'mp3',
            'title': 'Waltz No. 2 (The Second Waltz) by Dmitri Shostakovich for Piano',
            'description': 'md5:4632f2a04d34311292c3fd89211c5d7c',
            'thumbnail': r're:(?:https?://)(?:www\.)?musescore\.com/.*\.png[^$]+',
            'uploader': 'Minh_Cuteee',
            'creator': 'Dmaitri Shostakovich',
        }
    }, {
        'url': 'https://musescore.com/user/12461571/scores/3291706',
        'info_dict': {
            'id': '3291706',
            'ext': 'mp3',
            'title': 'River Flows In You',
            'description': 'md5:148c03afb5b1d237bca46458e225f4fd',
            'thumbnail': r're:(?:https?://)(?:www\.)?musescore\.com/.*\.png[^$]+',
            'uploader': 'emmy langevin',
            'creator': 'YIRUMA',
        }
    }, {
        'url': 'https://musescore.com/classicman/fur-elise',
        'info_dict': {
            'id': '33816',
            'ext': 'mp3',
            'title': 'Für Elise – Beethoven',
            'description': 'md5:49515a3556d5ecaf9fa4b2514064ac34',
            'thumbnail': r're:(?:https?://)(?:www\.)?musescore\.com/.*\.png[^$]+',
            'uploader': 'ClassicMan',
            'creator': 'Ludwig van Beethoven (1770–1827)',
        }
    }]

    def _real_extract(self, url):
        webpage = self._download_webpage(url, None)
        url = self._og_search_url(webpage) or url
        id = self._match_id(url)
        mp3_url = self._download_json(f'https://musescore.com/api/jmuse?id={id}&index=0&type=mp3&v2=1', id,
                                      headers={'authorization': '63794e5461e4cfa046edfbdddfccc1ac16daffd2'})['info']['url']
        formats = [{
            'url': mp3_url,
            'ext': 'mp3',
            'vcodec': 'none',
        }]

        return {
            'id': id,
            'formats': formats,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
            'uploader': self._html_search_meta('musescore:author', webpage, 'uploader'),
            'creator': self._html_search_meta('musescore:composer', webpage, 'composer'),
        }
