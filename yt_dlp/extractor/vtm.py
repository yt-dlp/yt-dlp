from .medialaan import MedialaanBaseIE
from ..utils import str_or_none
from ..utils.traversal import require, traverse_obj


class VTMIE(MedialaanBaseIE):
    _VALID_URL = r'https?://(?:www\.)?vtm\.be/[^/?#]+~v(?P<id>[\da-f]{8}(?:-[\da-f]{4}){3}-[\da-f]{12})'
    _TESTS = [{
        'url': 'https://vtm.be/gast-vernielt-genkse-hotelkamer~ve7534523-279f-4b4d-a5c9-a33ffdbe23e1',
        'info_dict': {
            'id': '192445',
            'ext': 'mp4',
            'title': 'Gast vernielt Genkse hotelkamer',
            'channel': 'VTM',
            'channel_id': '867',
            'description': 'md5:75fce957d219646ff1b65ba449ab97b5',
            'duration': 74,
            'genres': ['Documentaries'],
            'release_date': '20210119',
            'release_timestamp': 1611060180,
            'series': 'Op Interventie',
            'series_id': '2658',
            'tags': 'count:2',
            'thumbnail': r're:https?://images\.mychannels\.video/imgix/.+\.(?:jpe?g|png)',
            'uploader': 'VTM',
            'uploader_id': '74',
        },
    }]

    def _real_initialize(self):
        if not self._get_cookies('https://vtm.be/').get('authId'):
            self.raise_login_required()

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        apollo_state = self._search_json(
            r'window\.__APOLLO_STATE__\s*=', webpage, 'apollo state', video_id)
        mychannels_id = traverse_obj(apollo_state, (
            f'Video:{{"uuid":"{video_id}"}}', 'myChannelsVideo', {str_or_none}, {require('mychannels ID')}))

        return self._extract_from_mychannels_api(mychannels_id)
