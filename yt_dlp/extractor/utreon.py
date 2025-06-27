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
    IE_NAME = 'playeur'
    _VALID_URL = r'https?://(?:www\.)?(?:utreon|playeur)\.com/v/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://utreon.com/v/z_I7ikQbuDw',
        'info_dict': {
            'id': 'z_I7ikQbuDw',
            'ext': 'mp4',
            'title': 'Freedom Friday meditation - Rising in the wind',
            'description': 'md5:a9bf15a42434a062fe313b938343ad1b',
            'uploader': 'Heather Dawn Elemental Health',
            'thumbnail': r're:^https?://.+\.jpg',
            'release_date': '20210723',
            'duration': 586,
        },
    }, {
        'url': 'https://utreon.com/v/jerJw5EOOVU',
        'info_dict': {
            'id': 'jerJw5EOOVU',
            'ext': 'mp4',
            'title': 'When I\'m alone, I love to reflect in peace, to make my dreams come true... [Quotes and Poems]',
            'description': 'md5:4026aa3a2c10169c3649926ac8ef62b6',
            'uploader': 'Frases e Poemas Quotes and Poems',
            'thumbnail': r're:^https?://.+\.jpg',
            'release_date': '20210723',
            'duration': 60,
        },
    }, {
        'url': 'https://utreon.com/v/C4ZxXhYBBmE',
        'info_dict': {
            'id': 'C4ZxXhYBBmE',
            'ext': 'mp4',
            'title': 'Biden’s Capital Gains Tax Rate to Test World’s Highest',
            'description': 'md5:995aa9ad0733c0e5863ebdeff954f40e',
            'uploader': 'Nomad Capitalist',
            'thumbnail': r're:^https?://.+\.jpg',
            'release_date': '20210723',
            'duration': 884,
        },
    }, {
        'url': 'https://utreon.com/v/Y-stEH-FBm8',
        'info_dict': {
            'id': 'Y-stEH-FBm8',
            'ext': 'mp4',
            'title': 'Creeper-Chan Pranks Steve! 💚 [MINECRAFT ANIME]',
            'description': 'md5:7a48450b0d761b96dec194be0c5ecb5f',
            'uploader': 'Merryweather Comics',
            'thumbnail': r're:^https?://.+\.jpg',
            'release_date': '20210718',
            'duration': 151,
        },
    }, {
        'url': 'https://playeur.com/v/Wzqp-UrxSeu',
        'info_dict': {
            'id': 'Wzqp-UrxSeu',
            'ext': 'mp4',
            'title': 'Update: Clockwork Basilisk Books on the Way!',
            'description': 'md5:d9756b0b1884c904655b0e170d17cea5',
            'uploader': 'Forgotten Weapons',
            'release_date': '20240208',
            'thumbnail': r're:^https?://.+\.jpg',
            'duration': 262,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        json_data = self._download_json(
            'https://api.playeur.com/v1/videos/' + video_id,
            video_id)
        videos_json = json_data['videos']
        formats = [{
            'url': format_url,
            'format_id': format_key.split('_')[1],
            'height': int(format_key.split('_')[1][:-1]),
        } for format_key, format_url in videos_json.items() if url_or_none(format_url)]
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
