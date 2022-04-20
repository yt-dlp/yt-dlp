from .common import InfoExtractor
from ..utils import int_or_none


class FilmmoduIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www.)?filmmodu.org/(?P<id>[^/]+-(?:turkce-dublaj-izle|altyazili-izle))'
    _TESTS = [{
        'url': 'https://www.filmmodu.org/f9-altyazili-izle',
        'md5': 'aeefd955c2a508a5bdaa3bcec8eeb0d4',
        'info_dict': {
            'id': '10804',
            'ext': 'mp4',
            'title': 'F9',
            'description': 'md5:2713f584a4d65afa2611e2948d0b953c',
            'subtitles': {
                'tr': [{
                    'ext': 'vtt',
                }],
            },
            'thumbnail': r're:https://s[0-9]+.filmmodu.org/uploads/movie/cover/10804/xXHZeb1yhJvnSHPzZDqee0zfMb6.jpg',
        },
    }, {
        'url': 'https://www.filmmodu.org/the-godfather-turkce-dublaj-izle',
        'md5': '109f2fcb9c941330eed133971c035c00',
        'info_dict': {
            'id': '3646',
            'ext': 'mp4',
            'title': 'Baba',
            'description': 'md5:d43fd651937cd75cc650883ebd8d8461',
            'thumbnail': r're:https://s[0-9]+.filmmodu.org/uploads/movie/cover/3646/6xKCYgH16UuwEGAyroLU6p8HLIn.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        title = self._og_search_title(webpage, fatal=True)
        description = self._og_search_description(webpage)
        thumbnail = self._og_search_thumbnail(webpage)
        real_video_id = self._search_regex(r'var\s*videoId\s*=\s*\'([0-9]+)\'', webpage, 'video_id')
        video_type = self._search_regex(r'var\s*videoType\s*=\s*\'([a-z]+)\'', webpage, 'video_type')
        data = self._download_json('https://www.filmmodu.org/get-source', real_video_id, query={
            'movie_id': real_video_id,
            'type': video_type,
        })
        formats = [{
            'url': source['src'],
            'ext': 'mp4',
            'format_id': source['label'],
            'height': int_or_none(source.get('res')),
            'protocol': 'm3u8_native',
        } for source in data['sources']]

        self._sort_formats(formats)

        subtitles = {}

        if data.get('subtitle'):
            subtitles['tr'] = [{
                'url': data['subtitle'],
            }]

        return {
            'id': real_video_id,
            'display_id': video_id,
            'title': title,
            'description': description,
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': thumbnail,
        }
