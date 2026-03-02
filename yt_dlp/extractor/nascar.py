from .common import InfoExtractor
from ..utils import (
    float_or_none,
    parse_iso8601,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class NascarClassicsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?classics\.nascar\.com/video/(?P<id>[\w~-]+)'
    _TESTS = [{
        'url': 'https://classics.nascar.com/video/Ka5qGuxzZ~SIvJii7uAC~wszPshklHN',
        'md5': '81d712eccffa7169c328281b8cc28f77',
        'info_dict': {
            'id': 'Ka5qGuxzZ~SIvJii7uAC~wszPshklHN',
            'ext': 'mp4',
            'title': 'Cook Out 400 2023',
            'thumbnail': 'https://va.aws.nascar.com/IMAGES/CUP_2023_22_RICHMOND_THUMB_NCD.jpg',
            'timestamp': 1690732800,
            'upload_date': '20230730',
            'tags': ['2023', 'race #22', 'richmond', 'chris buescher', 'cup'],
            'chapters': 'count:18',
        },
    }, {
        'url': 'https://classics.nascar.com/video/UASvPDOwEha~SIvJii7uAC~wszPshklHN',
        'md5': 'a5e8d6ec6005da3857d25ba2df5e7133',
        'info_dict': {
            'id': 'UASvPDOwEha~SIvJii7uAC~wszPshklHN',
            'ext': 'mp4',
            'title': 'I Love New York 355 at the Glen 2017',
            'thumbnail': 'https://va.aws.nascar.com/IMAGES/CUP_2017_22_WATKINSGLEN_THUMB_NCD.jpg',
            'timestamp': 1501995600,
            'upload_date': '20170806',
            'tags': ['watkins glen', 'race #22', '2017', 'martin truex jr.', 'cup'],
            'chapters': 'count:13',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        content_data = self._search_nextjs_data(
            webpage, video_id)['props']['pageProps']['contentData']

        return {
            'id': video_id,
            'formats': self._extract_m3u8_formats(content_data['input']['src'], video_id, 'mp4'),
            **traverse_obj(content_data, {
                'title': ('input', 'name', {str}),
                'description': ('input', 'description', {str}, filter),
                'thumbnail': ('input', 'thumbnail', {url_or_none}),
                'tags': ('input', 'settings', 'tags', ..., {str}),
                'timestamp': ('input', 'start_time', {parse_iso8601}),
                'chapters': ('overlay', 'data', 'timelines', 0, 'events', lambda _, v: float(v['timestamp']) is not None, {
                    'start_time': ('timestamp', {float_or_none}),
                    'title': ('name', {str}),
                }),
            }),
        }
