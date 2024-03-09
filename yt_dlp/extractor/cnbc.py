from .common import InfoExtractor
from ..utils import int_or_none, parse_iso8601, str_or_none, url_or_none
from ..utils.traversal import traverse_obj


class CNBCVideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?cnbc\.com/video/(?:[^/?#]+/)+(?P<id>[^./?#&]+)\.html'

    _TESTS = [{
        'url': 'https://www.cnbc.com/video/2023/12/07/mcdonalds-just-unveiled-cosmcsits-new-spinoff-brand.html',
        'info_dict': {
            'ext': 'mp4',
            'id': '107344774',
            'display_id': 'mcdonalds-just-unveiled-cosmcsits-new-spinoff-brand',
            'modified_timestamp': 1702053483,
            'timestamp': 1701977810,
            'channel': 'News Videos',
            'upload_date': '20231207',
            'description': 'md5:882c001d85cb43d7579b514307b3e78b',
            'release_timestamp': 1701977375,
            'modified_date': '20231208',
            'release_date': '20231207',
            'duration': 65,
            'creators': ['Sean Conlon'],
            'title': 'Here\'s a first look at McDonald\'s new spinoff brand, CosMc\'s',
            'thumbnail': 'https://image.cnbcfm.com/api/v1/image/107344192-1701894812493-CosMcsskyHero_2336x1040_hero-desktop.jpg?v=1701894855',
        },
        'expected_warnings': ['Unable to download f4m manifest'],
    }, {
        'url': 'https://www.cnbc.com/video/2023/12/08/jim-cramer-shares-his-take-on-seattles-tech-scene.html',
        'info_dict': {
            'creators': ['Jim Cramer'],
            'channel': 'Mad Money with Jim Cramer',
            'description': 'md5:72925be21b952e95eba51178dddf4e3e',
            'duration': 299.0,
            'ext': 'mp4',
            'id': '107345451',
            'display_id': 'jim-cramer-shares-his-take-on-seattles-tech-scene',
            'thumbnail': 'https://image.cnbcfm.com/api/v1/image/107345481-1702079431MM-B-120823.jpg?v=1702079430',
            'timestamp': 1702080139,
            'title': 'Jim Cramer shares his take on Seattle\'s tech scene',
            'release_date': '20231208',
            'upload_date': '20231209',
            'modified_timestamp': 1702080139,
            'modified_date': '20231209',
            'release_timestamp': 1702073551,
        },
        'expected_warnings': ['Unable to download f4m manifest'],
    }, {
        'url': 'https://www.cnbc.com/video/2023/12/08/the-epicenter-of-ai-is-in-seattle-says-jim-cramer.html',
        'info_dict': {
            'creators': ['Jim Cramer'],
            'channel': 'Mad Money with Jim Cramer',
            'description': 'md5:72925be21b952e95eba51178dddf4e3e',
            'duration': 113.0,
            'ext': 'mp4',
            'id': '107345474',
            'display_id': 'the-epicenter-of-ai-is-in-seattle-says-jim-cramer',
            'thumbnail': 'https://image.cnbcfm.com/api/v1/image/107345486-Screenshot_2023-12-08_at_70339_PM.png?v=1702080248',
            'timestamp': 1702080535,
            'title': 'The epicenter of AI is in Seattle, says Jim Cramer',
            'release_timestamp': 1702077347,
            'modified_timestamp': 1702080535,
            'release_date': '20231208',
            'upload_date': '20231209',
            'modified_date': '20231209',
        },
        'expected_warnings': ['Unable to download f4m manifest'],
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        data = self._search_json(r'window\.__s_data=', webpage, 'video data', display_id)

        player_data = traverse_obj(data, (
            'page', 'page', 'layout', ..., 'columns', ..., 'modules',
            lambda _, v: v['name'] == 'clipPlayer', 'data', {dict}), get_all=False)

        return {
            'id': display_id,
            'display_id': display_id,
            'formats': self._extract_akamai_formats(player_data['playbackURL'], display_id),
            **self._search_json_ld(webpage, display_id, fatal=False),
            **traverse_obj(player_data, {
                'id': ('id', {str_or_none}),
                'title': ('title', {str}),
                'description': ('description', {str}),
                'creators': ('author', ..., 'name', {str}),
                'timestamp': ('datePublished', {parse_iso8601}),
                'release_timestamp': ('uploadDate', {parse_iso8601}),
                'modified_timestamp': ('dateLastPublished', {parse_iso8601}),
                'thumbnail': ('thumbnail', {url_or_none}),
                'duration': ('duration', {int_or_none}),
                'channel': ('section', 'title', {str}),
            }),
        }
