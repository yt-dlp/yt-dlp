import time

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    HEADRequest,
)


class CultureUnpluggedIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?cultureunplugged\.com/documentary/watch-online/play/(?P<id>\d+)(?:/(?P<display_id>[^/]+))?'
    _TESTS = [{
        'url': 'http://www.cultureunplugged.com/documentary/watch-online/play/53662/The-Next--Best-West',
        'md5': 'ac6c093b089f7d05e79934dcb3d228fc',
        'info_dict': {
            'id': '53662',
            'display_id': 'The-Next--Best-West',
            'ext': 'mp4',
            'title': 'The Next, Best West',
            'description': 'md5:0423cd00833dea1519cf014e9d0903b1',
            'thumbnail': r're:^https?://.*\.jpg$',
            'creator': 'Coldstream Creative',
            'duration': 2203,
            'view_count': int,
        }
    }, {
        'url': 'http://www.cultureunplugged.com/documentary/watch-online/play/53662',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        display_id = mobj.group('display_id') or video_id

        # request setClientTimezone.php to get PHPSESSID cookie which is need to get valid json data in the next request
        self._request_webpage(HEADRequest(
            'http://www.cultureunplugged.com/setClientTimezone.php?timeOffset=%d' % -(time.timezone / 3600)), display_id)
        movie_data = self._download_json(
            'http://www.cultureunplugged.com/movie-data/cu-%s.json' % video_id, display_id)

        video_url = movie_data['url']
        title = movie_data['title']

        description = movie_data.get('synopsis')
        creator = movie_data.get('producer')
        duration = int_or_none(movie_data.get('duration'))
        view_count = int_or_none(movie_data.get('views'))

        thumbnails = [{
            'url': movie_data['%s_thumb' % size],
            'id': size,
            'preference': preference,
        } for preference, size in enumerate((
            'small', 'large')) if movie_data.get('%s_thumb' % size)]

        return {
            'id': video_id,
            'display_id': display_id,
            'url': video_url,
            'title': title,
            'description': description,
            'creator': creator,
            'duration': duration,
            'view_count': view_count,
            'thumbnails': thumbnails,
        }
