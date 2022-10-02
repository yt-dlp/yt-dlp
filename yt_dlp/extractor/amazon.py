from .common import InfoExtractor
from ..utils import ExtractorError, int_or_none


class AmazonStoreIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?amazon\.(?:[a-z]{2,3})(?:\.[a-z]{2})?/(?:[^/]+/)?(?:dp|gp/product)/(?P<id>[^/&#$?]+)'

    _TESTS = [{
        'url': 'https://www.amazon.co.uk/dp/B098XNCHLD/',
        'info_dict': {
            'id': 'B098XNCHLD',
            'title': 'md5:dae240564cbb2642170c02f7f0d7e472',
        },
        'playlist_mincount': 1,
        'playlist': [{
            'info_dict': {
                'id': 'A1F83G8C2ARO7P',
                'ext': 'mp4',
                'title': 'mcdodo usb c cable 100W 5a',
                'thumbnail': r're:^https?://.*\.jpg$',
                'duration': 34,
            },
        }]
    }, {
        'url': 'https://www.amazon.in/Sony-WH-1000XM4-Cancelling-Headphones-Bluetooth/dp/B0863TXGM3',
        'info_dict': {
            'id': 'B0863TXGM3',
            'title': 'md5:d1d3352428f8f015706c84b31e132169',
        },
        'playlist_mincount': 4,
    }, {
        'url': 'https://www.amazon.com/dp/B0845NXCXF/',
        'info_dict': {
            'id': 'B0845NXCXF',
            'title': 'md5:f3fa12779bf62ddb6a6ec86a360a858e',
        },
        'playlist-mincount': 1,
    }, {
        'url': 'https://www.amazon.es/Samsung-Smartphone-s-AMOLED-Quad-c%C3%A1mara-espa%C3%B1ola/dp/B08WX337PQ',
        'info_dict': {
            'id': 'B08WX337PQ',
            'title': 'md5:f3fa12779bf62ddb6a6ec86a360a858e',
        },
        'playlist_mincount': 1,
    }]

    def _real_extract(self, url):
        id = self._match_id(url)

        for retry in self.RetryManager():
            webpage = self._download_webpage(url, id)
            try:
                data_json = self._search_json(
                    r'var\s?obj\s?=\s?jQuery\.parseJSON\(\'', webpage, 'data', id,
                    transform_source=lambda x: x.replace(R'\\u', R'\u'))
            except ExtractorError as e:
                retry.error = e

        entries = [{
            'id': video['marketPlaceID'],
            'url': video['url'],
            'title': video.get('title'),
            'thumbnail': video.get('thumbUrl') or video.get('thumb'),
            'duration': video.get('durationSeconds'),
            'height': int_or_none(video.get('videoHeight')),
            'width': int_or_none(video.get('videoWidth')),
        } for video in (data_json.get('videos') or []) if video.get('isVideo') and video.get('url')]
        return self.playlist_result(entries, playlist_id=id, playlist_title=data_json.get('title'))
