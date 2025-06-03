from .common import InfoExtractor
from ..utils import clean_html
from ..utils.traversal import find_element, traverse_obj


class UMGDeIE(InfoExtractor):
    IE_NAME = 'umg:de'
    IE_DESC = 'Universal Music Deutschland'
    _VALID_URL = r'https?://(?:www\.)?universal-music\.de/[^/?#]+/videos/(?P<slug>[^/?#]+-(?P<id>\d+))'
    _TESTS = [{
        'url': 'https://www.universal-music.de/sido/videos/jedes-wort-ist-gold-wert-457803',
        'info_dict': {
            'id': '457803',
            'ext': 'mp4',
            'title': 'Jedes Wort ist Gold wert',
            'artists': ['Sido'],
            'description': 'md5:df2dbffcff1a74e0a7c9bef4b497aeec',
            'display_id': 'jedes-wort-ist-gold-wert-457803',
            'duration': 210.0,
            'thumbnail': r're:https?://images\.universal-music\.de/img/assets/.+\.jpg',
            'timestamp': 1513591800,
            'upload_date': '20171218',
            'view_count': int,
        },
    }, {
        'url': 'https://www.universal-music.de/alexander-eder/videos/der-doktor-hat-gesagt-609533',
        'info_dict': {
            'id': '609533',
            'ext': 'mp4',
            'title': 'Der Doktor hat gesagt',
            'artists': ['Alexander Eder'],
            'display_id': 'der-doktor-hat-gesagt-609533',
            'duration': 146.0,
            'thumbnail': r're:https?://images\.universal-music\.de/img/assets/.+\.jpg',
            'timestamp': 1742982100,
            'upload_date': '20250326',
        },
    }]

    def _real_extract(self, url):
        display_id, video_id = self._match_valid_url(url).group('slug', 'id')
        webpage = self._download_webpage(url, display_id)

        return {
            **self._search_json_ld(webpage, display_id),
            'id': video_id,
            'artists': traverse_obj(self._html_search_meta('umg-artist-screenname', webpage), (filter, all)),
            # The JSON LD description duplicates the title
            'description': traverse_obj(webpage, ({find_element(cls='_3Y0Lj')}, {clean_html})),
            'display_id': display_id,
            'formats': self._extract_m3u8_formats(
                'https://hls.universal-music.de/get', display_id, 'mp4', query={'id': video_id}),
        }
