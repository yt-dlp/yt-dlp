# coding: utf-8
from .common import InfoExtractor
from ..utils import int_or_none


class AmazonStoreIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?amazon\.(?:[a-z]{2,3})(?:\.[a-z]{2})?/(?:[^/]+/)?(?:dp|gp/product)/(?P<id>[^/&#$?]+)'

    _TESTS = [{
        'url': 'https://www.amazon.co.uk/dp/B098XNCHLD/',
        'info_dict': {
            'id': 'B098XNCHLD',
            'title': 'md5:5f3194dbf75a8dcfc83079bd63a2abed',
        },
        'playlist_mincount': 1,
        'playlist': [{
            'info_dict': {
                'id': 'A1F83G8C2ARO7P',
                'ext': 'mp4',
                'title': 'mcdodo usb c cable 100W 5a',
                'thumbnail': r're:^https?://.*\.jpg$',
            },
        }]
    }, {
        'url': 'https://www.amazon.in/Sony-WH-1000XM4-Cancelling-Headphones-Bluetooth/dp/B0863TXGM3',
        'info_dict': {
            'id': 'B0863TXGM3',
            'title': 'md5:b0bde4881d3cfd40d63af19f7898b8ff',
        },
        'playlist_mincount': 4,
    }, {
        'url': 'https://www.amazon.com/dp/B0845NXCXF/',
        'info_dict': {
            'id': 'B0845NXCXF',
            'title': 'md5:2145cd4e3c7782f1ee73649a3cff1171',
        },
        'playlist-mincount': 1,
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        webpage = self._download_webpage(url, id)
        data_json = self._parse_json(self._html_search_regex(r'var\s?obj\s?=\s?jQuery\.parseJSON\(\'(.*)\'\)', webpage, 'data'), id)
        entries = [{
            'id': video['marketPlaceID'],
            'url': video['url'],
            'title': video.get('title'),
            'thumbnail': video.get('thumbUrl') or video.get('thumb'),
            'duration': video.get('durationSeconds'),
            'height': int_or_none(video.get('videoHeight')),
            'width': int_or_none(video.get('videoWidth')),
        } for video in (data_json.get('videos') or []) if video.get('isVideo') and video.get('url')]
        return self.playlist_result(entries, playlist_id=id, playlist_title=data_json['title'])
