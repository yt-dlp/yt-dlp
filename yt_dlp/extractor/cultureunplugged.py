from .common import InfoExtractor
from ..utils import int_or_none


class CultureUnpluggedIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?cultureunplugged\.com/(?:documentary/watch-online/)?play/(?P<id>\d+)(?:/(?P<display_id>[^/#?]+))?'
    _TESTS = [{
        'url': 'http://www.cultureunplugged.com/documentary/watch-online/play/53662/The-Next--Best-West',
        'md5': 'ac6c093b089f7d05e79934dcb3d228fc',
        'info_dict': {
            'id': '53662',
            'display_id': 'The-Next--Best-West',
            'ext': 'mp4',
            'title': 'The Next, Best West',
            'description': 'md5:770033a3b7c2946a3bcfb7f1c6fb7045',
            'thumbnail': r're:^https?://.*\.jpg$',
            'creators': ['Coldstream Creative'],
            'duration': 2203,
            'view_count': int,
        },
    }, {
        'url': 'https://www.cultureunplugged.com/play/2833/Koi-Sunta-Hai--Journeys-with-Kumar---Kabir--Someone-is-Listening-',
        'md5': 'dc2014bc470dfccba389a1c934fa29fa',
        'info_dict': {
            'id': '2833',
            'display_id': 'Koi-Sunta-Hai--Journeys-with-Kumar---Kabir--Someone-is-Listening-',
            'ext': 'mp4',
            'title': 'Koi Sunta Hai: Journeys with Kumar & Kabir (Someone is Listening)',
            'description': 'md5:fa94ac934927c98660362b8285b2cda5',
            'view_count': int,
            'thumbnail': 'https://s3.amazonaws.com/cdn.cultureunplugged.com/thumbnails_16_9/lg/2833.jpg',
            'creators': ['Srishti'],
        },
    }, {
        'url': 'http://www.cultureunplugged.com/documentary/watch-online/play/53662',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        display_id = mobj.group('display_id') or video_id

        movie_data = self._download_json(
            f'http://www.cultureunplugged.com/movie-data/cu-{video_id}.json', display_id)

        video_url = movie_data['url']
        title = movie_data['title']

        description = movie_data.get('synopsis')
        creator = movie_data.get('producer')
        duration = int_or_none(movie_data.get('duration'))
        view_count = int_or_none(movie_data.get('views'))

        thumbnails = [{
            'url': movie_data[f'{size}_thumb'],
            'id': size,
            'preference': preference,
        } for preference, size in enumerate((
            'small', 'large')) if movie_data.get(f'{size}_thumb')]

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
