import re

from .common import InfoExtractor

from ..utils import (
    parse_duration,
    traverse_obj,
    unified_timestamp,
)


class RTVSIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rtvs\.sk/(?:radio|televizia)/archiv(?:/\d+)?/(?P<id>\d+)/?(?:[#?]|$)'
    _TESTS = [{
        # radio archive
        'url': 'http://www.rtvs.sk/radio/archiv/11224/414872',
        'md5': '134d5d6debdeddf8a5d761cbc9edacb8',
        'info_dict': {
            'id': '414872',
            'ext': 'mp3',
            'title': 'Ostrov pokladov 1 časť.mp3',
            'duration': 2854,
            'thumbnail': 'https://www.rtvs.sk/media/a501/image/file/2/0000/b1R8.rtvs.jpg',
            'display_id': '135331',
        }
    }, {
        # tv archive
        'url': 'http://www.rtvs.sk/televizia/archiv/8249/63118',
        'info_dict': {
            'id': '63118',
            'ext': 'mp4',
            'title': 'Amaro Džives - Náš deň',
            'description': 'Galavečer pri príležitosti Medzinárodného dňa Rómov.',
            'thumbnail': 'https://www.rtvs.sk/media/a501/image/file/2/0031/L7Qm.amaro_dzives_png.jpg',
            'timestamp': 1428555900,
            'upload_date': '20150409',
            'duration': 4986,
        }
    }, {
        # tv archive
        'url': 'https://www.rtvs.sk/televizia/archiv/18083?utm_source=web&utm_medium=rozcestnik&utm_campaign=Robin',
        'info_dict': {
            'id': '18083',
            'ext': 'mp4',
            'title': 'Robin',
            'description': 'md5:2f70505a7b8364491003d65ff7a0940a',
            'timestamp': 1636652760,
            'display_id': '307655',
            'duration': 831,
            'upload_date': '20211111',
            'thumbnail': 'https://www.rtvs.sk/media/a501/image/file/2/0916/robin.jpg',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)
        iframe_id = self._search_regex(
            r'<iframe[^>]+id\s*=\s*"player_[^_]+_([0-9]+)"', webpage, 'Iframe ID')
        iframe_url = self._search_regex(
            fr'<iframe[^>]+id\s*=\s*"player_[^_]+_{re.escape(iframe_id)}"[^>]+src\s*=\s*"([^"]+)"', webpage, 'Iframe URL')

        webpage = self._download_webpage(iframe_url, video_id, 'Downloading iframe')
        json_url = self._search_regex(r'var\s+url\s*=\s*"([^"]+)"\s*\+\s*ruurl', webpage, 'json URL')
        data = self._download_json(f'https:{json_url}b=mozilla&p=win&v=97&f=0&d=1', video_id)

        if data.get('clip'):
            data['playlist'] = [data['clip']]

        if traverse_obj(data, ('playlist', 0, 'sources', 0, 'type')) == 'audio/mp3':
            formats = [{'url': traverse_obj(data, ('playlist', 0, 'sources', 0, 'src'))}]
        else:
            formats = self._extract_m3u8_formats(traverse_obj(data, ('playlist', 0, 'sources', 0, 'src')), video_id)
        self._sort_formats(formats)

        return {
            'id': video_id,
            'display_id': iframe_id,
            'title': traverse_obj(data, ('playlist', 0, 'title')),
            'description': traverse_obj(data, ('playlist', 0, 'description')),
            'duration': parse_duration(traverse_obj(data, ('playlist', 0, 'length'))),
            'thumbnail': traverse_obj(data, ('playlist', 0, 'image')),
            'timestamp': unified_timestamp(traverse_obj(data, ('playlist', 0, 'datetime_create'))),
            'formats': formats
        }
