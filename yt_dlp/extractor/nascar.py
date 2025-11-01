from .common import InfoExtractor
from ..utils import int_or_none, parse_iso8601, str_or_none, traverse_obj, url_or_none


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
            'description': '',
            'timestamp': 1690732800,
            'upload_date': '20230730',
            'tags': ['2023', 'race #22', 'richmond', 'chris buescher', 'cup'],
            'chapters': 'count:18',
        },
    },
        {
        'url': 'https://classics.nascar.com/video/UASvPDOwEha~SIvJii7uAC~wszPshklHN',
        'md5': 'a5e8d6ec6005da3857d25ba2df5e7133',
        'info_dict': {
            'id': 'UASvPDOwEha~SIvJii7uAC~wszPshklHN',
            'ext': 'mp4',
            'title': 'I Love New York 355 at the Glen 2017',
            'thumbnail': 'https://va.aws.nascar.com/IMAGES/CUP_2017_22_WATKINSGLEN_THUMB_NCD.jpg',
            'description': '',
            'timestamp': 1501995600,
            'upload_date': '20170806',
            'tags': ['watkins glen', 'race #22', '2017', 'martin truex jr.', 'cup'],
            'chapters': 'count:13',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        content_data = self._search_json('contentData":', webpage, 'nascar_classics_content_data', video_id)

        name = traverse_obj(content_data, ('input', 'name'))
        description = str_or_none(traverse_obj(content_data, ('input', 'description')))
        thumbnail = url_or_none(traverse_obj(content_data, ('input', 'thumbnail')))
        m3u8_url = traverse_obj(content_data, ('input', 'src'))
        tags = traverse_obj(content_data, ('input', 'settings', 'tags'))
        timestamp = int_or_none(parse_iso8601(traverse_obj(content_data, ('input', 'start_time'))))
        timeline_events = traverse_obj(content_data, ('overlay', 'data', 'timelines', 0, 'events'), default=[])

        chapters = [{'start_time': int_or_none(event.get('timestamp'), default=0), 'title': event.get('name', '')} for event in timeline_events]
        formats = self._extract_m3u8_formats(m3u8_url=m3u8_url, video_id=video_id)

        return {
            'id': video_id,
            'title': name,
            'description': description,
            'formats': formats,
            'thumbnail': thumbnail,
            'tags': tags,
            'timestamp': timestamp,
            'chapters': chapters,
        }
