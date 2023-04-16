from .common import InfoExtractor
from ..utils import (
    float_or_none,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class WhypIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?whyp\.it/tracks/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.whyp.it/tracks/18337/home-page-example-track-b4kq7',
        'md5': 'c1187b42ebf8605284e3dc92aeb33d16',
        'info_dict': {
            'url': 'https://cdn.whyp.it/50eb17cc-e9ff-4e18-b89b-dc9206a95cb1.mp3',
            'id': '18337',
            'title': 'Home Page Example Track',
            'description': 'md5:bd758000fb93f3159339c852b5b9133c',
            'ext': 'mp3',
            'duration': 52.82,
            'uploader': 'Brad',
            'uploader_id': '1',
            'thumbnail': 'https://cdn.whyp.it/a537bb36-3373-4c61-96c8-27fc1b2f427a.jpg',
        },
    }, {
        'url': 'https://www.whyp.it/tracks/18337',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        unique_id = self._match_id(url)
        webpage = self._download_webpage(url, unique_id)
        data = self._search_nuxt_data(webpage, unique_id)['rawTrack']

        return {
            'url': data['audio_url'],
            'id': unique_id,
            **traverse_obj(data, {
                'title': 'title',
                'description': 'description',
                'duration': ('duration', {float_or_none}),
                'uploader': ('user', 'username'),
                'uploader_id': ('user', 'id', {str_or_none}),
                'thumbnail': ('artwork_url', {url_or_none}),
            }),
            'ext': 'mp3',
            'vcodec': 'none',
            'http_headers': {'Referer': 'https://whyp.it/'},
        }
