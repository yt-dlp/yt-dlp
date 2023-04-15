from .common import InfoExtractor
from ..utils import traverse_obj


class WhypIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?whyp\.it/tracks/(?P<number_id>[0-9_-]+)/(?P<display_id>[a-zA-Z0-9_-]+)'
    _TEST = {
        'url': 'https://www.whyp.it/tracks/18337/home-page-example-track-b4kq7',
        'md5': 'c1187b42ebf8605284e3dc92aeb33d16',
        'info_dict': {
            'url': 'https://cdn.whyp.it/50eb17cc-e9ff-4e18-b89b-dc9206a95cb1.mp3',
            'id': '18337',
            'title': 'Home Page Example Track',
            'description': 'Just an example track for the home page!\n\nCredit: https://file-examples.com/index.php/sample-audio-files/sample-mp3-download/',
            'ext': 'mp3',
            'duration': 52.82,
            'uploader': 'Brad',
            'uploader_id': 1,
            'thumbnail': 'https://cdn.whyp.it/a537bb36-3373-4c61-96c8-27fc1b2f427a.jpg',
            'vcodec': 'none',
        }
    }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        unique_id = mobj.group('number_id')

        webpage = self._download_webpage(url, unique_id)

        data = self._search_nuxt_data(webpage, unique_id)['rawTrack']

        return {
            'url': data['audio_url'],
            'id': unique_id,
            'title': data.get('title'),
            'description': data.get('description'),
            'duration': data.get('duration'),
            'uploader': traverse_obj(data, ('user', 'username')),
            'uploader_id': traverse_obj(data, ('user', 'id')),
            'thumbnail': data.get('artwork_url'),
            'ext': 'mp3',
            'vcodec': 'none',
            # Need referer header otherwise get 403 error from cdn
            'http_headers': {'Referer': 'https://whyp.it/'},
        }
