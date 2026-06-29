import json

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    make_archive_id,
    str_or_none,
)
from ..utils.traversal import (
    find_element,
    require,
    traverse_obj,
)


class AllocineIE(InfoExtractor):
    IE_NAME = 'allocine'
    IE_DESC = 'AlloCiné'

    _VALID_URL = r'https?://(?:www\.)?allocine\.fr/(?:article|video|film)/(?:fichearticle_gen_carticle=|player_gen_cmedia=|fichefilm_gen_cfilm=|video-)(?P<id>\d+)(?:\.html)?'
    _TESTS = [{
        'url': 'https://www.allocine.fr/article/fichearticle_gen_carticle=18635087.html',
        'info_dict': {
            'id': 'x8a20c7',
            'ext': 'mp4',
            'title': 'Teaser Astérix - Le Domaine des Dieux : les Romains font grève !',
            'age_limit': 0,
            'creators': 'count:1',
            'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
            'display_id': '18635087',
            'duration': 40,
            'like_count': int,
            'modified_date': '20140702',
            'modified_timestamp': 1404270000,
            'release_date': '20140702',
            'release_timestamp': 1404270000,
            'tags': [],
            'thumbnail': r're:https?://.+\.jpg',
            'timestamp': 1404259200,
            'upload_date': '20140702',
            'uploader': 'AlloCiné',
            'uploader_id': 'x5rjhv',
            'view_count': int,
            '_old_archive_ids': ['allocine 19546517'],
        },
        'add_ie': ['Dailymotion'],
    }, {
        'url': 'https://www.allocine.fr/video/player_gen_cmedia=19540403&cfilm=222257.html',
        'info_dict': {
            'id': 'x8a48qo',
            'ext': 'mp4',
            'title': 'Planes 2 Bande-annonce VF',
            'age_limit': 0,
            'description': 'md5:3bb65456b814081d264318e661166268',
            'display_id': '19540403',
            'duration': 69.0,
            'like_count': int,
            'tags': [],
            'thumbnail': r're:https?://.+\.jpg',
            'timestamp': 1385656200,
            'upload_date': '20131128',
            'uploader': 'Allociné',
            'uploader_id': 'x5rjhv',
            'view_count': int,
            '_old_archive_ids': ['allocine 19540403'],
        },
        'add_ie': ['Dailymotion'],
    }, {
        'url': 'https://www.allocine.fr/video/player_gen_cmedia=19544709&cfilm=181290.html',
        'info_dict': {
            'id': 'x8a1vly',
            'ext': 'mp4',
            'title': 'Dragons 2 - Bande annonce finale VF',
            'age_limit': 0,
            'description': 'md5:1cda4f6c621f95fafe9c42dcac399b5f',
            'display_id': '19544709',
            'duration': 144.0,
            'like_count': int,
            'tags': [],
            'thumbnail': r're:https?://.+\.jpg',
            'timestamp': 1397582700,
            'upload_date': '20140415',
            'uploader': 'Allociné',
            'uploader_id': 'x5rjhv',
            'view_count': int,
            '_old_archive_ids': ['allocine 19544709'],
        },
        'add_ie': ['Dailymotion'],
    }, {
        'url': 'https://www.allocine.fr/video/video-19550147/',
        'info_dict': {
            'id': 'x8a3u4k',
            'ext': 'mp4',
            'title': 'Les gaffes de Cliffhanger',
            'age_limit': 0,
            'description': 'md5:f0f8daccb3a4687928edbc806d596b35',
            'display_id': '19550147',
            'duration': 346.0,
            'like_count': int,
            'tags': [],
            'thumbnail': r're:https?://.+\.jpg',
            'timestamp': 1418330280,
            'upload_date': '20141211',
            'uploader': 'Allociné',
            'uploader_id': 'x5rjhv',
            'view_count': int,
            '_old_archive_ids': ['allocine 19550147'],
        },
        'add_ie': ['Dailymotion'],

    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        videos = traverse_obj(webpage, (
            {find_element(cls='player player-auto-play js-player', html=True)},
            {extract_attributes}, 'data-model', {json.loads}, 'videos'))

        dailymotion_id = traverse_obj(videos, (
            ..., 'idDailymotion', {str}, any, {require('Dailymotion ID')}))
        old_id = traverse_obj(videos, (
            ..., 'id', {str_or_none}, any), default=display_id)

        return {
            **self._search_json_ld(webpage, display_id),
            '_old_archive_ids': [make_archive_id(self, old_id)],
            '_type': 'url_transparent',
            'display_id': display_id,
            'ie_key': 'Dailymotion',
            'url': f'https://www.dailymotion.com/video/{dailymotion_id}',
        }
