# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    dict_get,
    int_or_none,
    str_or_none,
    try_get,
    unified_strdate,
    url_or_none,
)


class UtreonIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?utreon.com/v/(?P<id>[a-zA-Z0-9_-]+)'
    _TESTS = [{
        'url': 'https://utreon.com/v/z_I7ikQbuDw',
        'info_dict': {
            'id': 'z_I7ikQbuDw',
            'ext': 'mp4',
            'title': 'Freedom Friday meditation - Rising in the wind',
            'description': 'md5:a9bf15a42434a062fe313b938343ad1b',
            'uploader': 'Heather Dawn Elemental Health',
            'thumbnail': 'https://data-1.utreon.com/v/MG/M2/NT/z_I7ikQbuDw/z_I7ikQbuDw_preview.jpg',
            'release_date': '20210723',
        }
    }, {
        'url': 'https://utreon.com/v/jerJw5EOOVU',
        'info_dict': {
            'id': 'jerJw5EOOVU',
            'ext': 'mp4',
            'title': 'When I\'m alone, I love to reflect in peace, to make my dreams come true... [Quotes and Poems]',
            'description': 'md5:61ee6c2da98be51b04b969ca80273aaa',
            'uploader': 'Frases e Poemas Quotes and Poems',
            'thumbnail': 'https://data-1.utreon.com/v/Mz/Zh/ND/jerJw5EOOVU/jerJw5EOOVU_89af85470a4b16eededde7f8674c96d9_cover.jpg',
            'release_date': '20210723',
        }
    }, {
        'url': 'https://utreon.com/v/C4ZxXhYBBmE',
        'info_dict': {
            'id': 'C4ZxXhYBBmE',
            'ext': 'mp4',
            'title': 'Biden’s Capital Gains Tax Rate to Test World’s Highest',
            'description': 'md5:fb5a6c2e506f013cc76f133f673bc5c8',
            'uploader': 'Nomad Capitalist',
            'thumbnail': 'https://data-1.utreon.com/v/ZD/k1/Mj/C4ZxXhYBBmE/C4ZxXhYBBmE_628342076198c9c06dd6b2c665978584_cover.jpg',
            'release_date': '20210723',
        }
    }, {
        'url': 'https://utreon.com/v/Y-stEH-FBm8',
        'info_dict': {
            'id': 'Y-stEH-FBm8',
            'ext': 'mp4',
            'title': 'Creeper-Chan Pranks Steve! 💚 [MINECRAFT ANIME]',
            'description': 'md5:7a48450b0d761b96dec194be0c5ecb5f',
            'uploader': 'Merryweather Comics',
            'thumbnail': 'https://data-1.utreon.com/v/MT/E4/Zj/Y-stEH-FBm8/Y-stEH-FBm8_5290676a41a4a1096db133b09f54f77b_cover.jpg',
            'release_date': '20210718',
        }},
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        json_data = self._download_json(
            'https://api.utreon.com/v1/videos/' + video_id,
            video_id)
        videos_json = json_data['videos']
        formats = [{
            'url': format_url,
            'format_id': format_key.split('_')[1],
            'height': int(format_key.split('_')[1][:-1]),
        } for format_key, format_url in videos_json.items() if url_or_none(format_url)]
        self._sort_formats(formats)
        thumbnail = url_or_none(dict_get(json_data, ('cover_image_url', 'preview_image_url')))
        return {
            'id': video_id,
            'title': json_data['title'],
            'formats': formats,
            'description': str_or_none(json_data.get('description')),
            'duration': int_or_none(json_data.get('duration')),
            'uploader': str_or_none(try_get(json_data, lambda x: x['channel']['title'])),
            'thumbnail': thumbnail,
            'release_date': unified_strdate(json_data.get('published_datetime')),
        }
