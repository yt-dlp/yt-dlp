import json

from .common import InfoExtractor
from ..utils import int_or_none


class PornotubeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:\w+\.)?pornotube\.com/(?:[^?#]*?)/video/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'http://www.pornotube.com/orientation/straight/video/4964/title/weird-hot-and-wet-science',
        'md5': '60fc5a4f0d93a97968fc7999d98260c9',
        'info_dict': {
            'id': '4964',
            'ext': 'mp4',
            'upload_date': '20141203',
            'title': 'Weird Hot and Wet Science',
            'description': 'md5:a8304bef7ef06cb4ab476ca6029b01b0',
            'categories': ['Adult Humor', 'Blondes'],
            'uploader': 'Alpha Blue Archives',
            'thumbnail': r're:^https?://.*\.jpg$',
            'timestamp': 1417582800,
            'age_limit': 18,
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        token = self._download_json(
            'https://api.aebn.net/auth/v2/origins/authenticate',
            video_id, note='Downloading token',
            data=json.dumps({'credentials': 'Clip Application'}).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Origin': 'http://www.pornotube.com',
            })['tokenKey']

        video_url = self._download_json(
            'https://api.aebn.net/delivery/v1/clips/%s/MP4' % video_id,
            video_id, note='Downloading delivery information',
            headers={'Authorization': token})['mediaUrl']

        FIELDS = (
            'title', 'description', 'startSecond', 'endSecond', 'publishDate',
            'studios{name}', 'categories{name}', 'movieId', 'primaryImageNumber'
        )

        info = self._download_json(
            'https://api.aebn.net/content/v2/clips/%s?fields=%s'
            % (video_id, ','.join(FIELDS)), video_id,
            note='Downloading metadata',
            headers={'Authorization': token})

        if isinstance(info, list):
            info = info[0]

        title = info['title']

        timestamp = int_or_none(info.get('publishDate'), scale=1000)
        uploader = info.get('studios', [{}])[0].get('name')
        movie_id = info.get('movieId')
        primary_image_number = info.get('primaryImageNumber')
        thumbnail = None
        if movie_id and primary_image_number:
            thumbnail = 'http://pic.aebn.net/dis/t/%s/%s_%08d.jpg' % (
                movie_id, movie_id, primary_image_number)
        start = int_or_none(info.get('startSecond'))
        end = int_or_none(info.get('endSecond'))
        duration = end - start if start and end else None
        categories = [c['name'] for c in info.get('categories', []) if c.get('name')]

        return {
            'id': video_id,
            'url': video_url,
            'title': title,
            'description': info.get('description'),
            'duration': duration,
            'timestamp': timestamp,
            'uploader': uploader,
            'thumbnail': thumbnail,
            'categories': categories,
            'age_limit': 18,
        }
