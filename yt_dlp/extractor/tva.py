# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    float_or_none,
    get_element_by_id,
    int_or_none,
    smuggle_url,
    str_to_int,
    strip_or_none,
    try_get,
)


class TVAIE(InfoExtractor):
    _VALID_URL = r'https?://videos?\.tva\.ca/details/_(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://videos.tva.ca/details/_5596811470001',
        'info_dict': {
            'id': '5596811470001',
            'ext': 'mp4',
            'title': 'Un extrait de l\'épisode du dimanche 8 octobre 2017 !',
            'uploader_id': '5481942443001',
            'upload_date': '20171003',
            'timestamp': 1507064617,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'skip': 'HTTP Error 404: Not Found',
    }, {
        'url': 'https://video.tva.ca/details/_5596811470001',
        'only_matching': True,
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/5481942443001/default_default/index.html?videoId=%s'

    def _real_extract(self, url):
        video_id = self._match_id(url)

        return {
            '_type': 'url_transparent',
            'id': video_id,
            'url': smuggle_url(self.BRIGHTCOVE_URL_TEMPLATE % video_id, {'geo_countries': ['CA']}),
            'ie_key': 'BrightcoveNew',
        }


class QubIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?qub\.ca/(?:[^/]+/)*[0-9a-z-]+-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.qub.ca/tvaplus/tva/alerte-amber/saison-1/episode-01-1000036619',
        'md5': '949490fd0e7aee11d0543777611fbd53',
        'info_dict': {
            'id': '6084352463001',
            'ext': 'mp4',
            'title': 'Ép 01. Mon dernier jour',
            'uploader_id': '5481942443001',
            'upload_date': '20190907',
            'timestamp': 1567899756,
            'description': 'md5:9c0d7fbb90939420c651fd977df90145',
            'age_limit': 13,
        },
    }, {
        'url': 'https://www.qub.ca/tvaplus/tva/indefendable/saison-1/episode-2-apte-a-subir-son-proces-1080300766',
        'md5': 'ba7e0da53f472d39230418a9d980dc9f',
        'info_dict': {
            'id': '6312064712112',
            'ext': 'mp4',
            'description': 'md5:9fd8701b50199e52fe9a5a43d20862e9',
            'title': 'Ép 02. Apte à subir son procès?',
            'timestamp': 1662681334,
            'upload_date': '20220908',
            'uploader_id': '5481942443001',
            'age_limit': 8,
        },
    }, {
        'url': 'https://www.qub.ca/tele/video/lcn-ca-vous-regarde-rev-30s-ap369664-1009357943',
        'only_matching': True,
    }]

    @staticmethod
    def _parse_rating(rating):
        age = str_to_int(rating)
        if age is not None:
            return age
        return {
            # CBSC
            'Exempt': None,
            'C': 0,
            'C8': 8,
            'G': 0,
            'PG': 10,
            # Régie du cinéma
            'G-Dec': 8,  # "déconseillé"
        }.get(rating)

    def _real_extract(self, url):
        entity_id = self._match_id(url)
        webpage = self._download_webpage(url, entity_id)
        next_data = get_element_by_id('__NEXT_DATA__', webpage) or '{}'
        entity = self._parse_json(next_data, entity_id)['props']['initialProps']['pageProps']['fallbackData']
        video_id = entity['videoId']
        episode = strip_or_none(entity.get('name')) or None

        return {
            '_type': 'url_transparent',
            'id': video_id,
            'title': episode or self._generic_title(url),
            'url': 'https://videos.tva.ca/details/_' + video_id,
            'description': entity.get('longDescription'),
            'duration': float_or_none(entity.get('durationMillis'), 1000),
            'episode': episode,
            'episode_number': int_or_none(entity.get('episodeNumber')),
            'channel': try_get(entity, lambda x: x['knownEntities']['channel']['name'], compat_str),
            'series': try_get(entity, lambda x: x['knownEntities']['videoShow']['name'], compat_str),
            'season_number': int_or_none(self._search_regex(r'/s(?:ai|ea)son-(\d+)/', entity.get('slug', ''), 'season', default=None)),
            'age_limit': self._parse_rating(entity.get('parentalRating')),
            'ie_key': TVAIE.ie_key(),
        }
