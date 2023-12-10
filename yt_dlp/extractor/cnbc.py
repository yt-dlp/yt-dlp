import json
from .common import InfoExtractor
from ..utils import traverse_obj, unified_strdate, url_or_none


class CNBCVideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?cnbc\.com/video/(?:[^/]+/)+(?P<id>[^./?#&]+)\.html'

    _TESTS = [
        {
            'url': 'https://www.cnbc.com/video/2023/12/07/mcdonalds-just-unveiled-cosmcsits-new-spinoff-brand.html',
            'info_dict': {
                'author': 'Sean Conlon',
                'channel': 'News Videos',
                'description': 'McDonald\'s unveiled its new spinoff brand known as CosMc\'s this week, announcing that the new brand\'s first location will open in Bolingbrook, Illinois. CosMc\'s drive-thru focused menu features brand new lemonades and teas, blended beverages, and cold coffee, as well as a small lineup of food. The burger chain first revealed it was creating CosMc\'s as a spinoff during its second-quarter earnings call in July.',
                'duration': 65.0,
                'ext': 'mp4',
                'id': 'mcdonalds-just-unveiled-cosmcsits-new-spinoff-brand',
                'title': 'Here\'s a first look at McDonald\'s new spinoff brand, CosMc\'s',
                'thumbnail': 'https://image.cnbcfm.com/api/v1/image/107344192-1701894812493-CosMcsskyHero_2336x1040_hero-desktop.jpg?v=1701894855',
                'thumbnails': [
                    {
                        'url': 'https://image.cnbcfm.com/api/v1/image/107344192-1701894812493-CosMcsskyHero_2336x1040_hero-desktop.jpg?v=1701894855'
                    }
                ],
                'timestamp': 1701977810,
                'upload_date': '20231207',
            },
            'expected_warnings': ['Unable to download f4m manifest'],
        },
        {
            'url': 'https://www.cnbc.com/video/2023/12/08/jim-cramer-shares-his-take-on-seattles-tech-scene.html',
            'info_dict': {
                'author': 'Jim Cramer',
                'channel': 'Mad Money with Jim Cramer',
                'description': '\'Mad Money\' host Jim Cramer returns from his trip to the West Coast with insight into the tech scene in Seattle, WA.',
                'duration': 299.0,
                'ext': 'mp4',
                'id': 'jim-cramer-shares-his-take-on-seattles-tech-scene',
                'thumbnail': 'https://image.cnbcfm.com/api/v1/image/107345481-1702079431MM-B-120823.jpg?v=1702079430',
                'thumbnails': [
                    {
                        'url': 'https://image.cnbcfm.com/api/v1/image/107345481-1702079431MM-B-120823.jpg?v=1702079430'
                    }
                ],
                'timestamp': 1702080139,
                'title': 'Jim Cramer shares his take on Seattle\'s tech scene',
                'upload_date': '20231208',
            },
            'expected_warnings': ['Unable to download f4m manifest'],
        },
        {
            'url': 'https://www.cnbc.com/video/2023/12/08/the-epicenter-of-ai-is-in-seattle-says-jim-cramer.html',
            'info_dict': {
                'author': 'Jim Cramer',
                'channel': 'Mad Money with Jim Cramer',
                'description': '\'Mad Money\' host Jim Cramer returns from his trip to the West Coast with insight into the tech scene in Seattle, WA.',
                'duration': 113.0,
                'ext': 'mp4',
                'id': 'the-epicenter-of-ai-is-in-seattle-says-jim-cramer',
                'thumbnail': 'https://image.cnbcfm.com/api/v1/image/107345486-Screenshot_2023-12-08_at_70339_PM.png?v=1702080248',
                'thumbnails': [
                    {
                        'url': 'https://image.cnbcfm.com/api/v1/image/107345486-Screenshot_2023-12-08_at_70339_PM.png?v=1702080248'
                    }
                ],
                'timestamp': 1702080535,
                'title': 'The epicenter of AI is in Seattle, says Jim Cramer',
                'upload_date': '20231208',
            },
            'expected_warnings': ['Unable to download f4m manifest'],
        },
    ]

    def _real_extract(self, url):
        display_id = self._match_valid_url(url).group('id')
        webpage = self._download_webpage(url, display_id)
        metadata = json.loads(
            self._html_search_regex(
                r'window\.__s_data=(\{.*?\});', webpage, 'video JSON data.'))

        link = traverse_obj(
            metadata,
            ('page', 'page', 'layout', 1, 'columns', 0, 'modules', 0, 'data', 'encodings', 0, 'url'), expected_type=url_or_none)

        upload_date = traverse_obj(
            metadata,
            ('page', 'page', 'layout', 1, 'columns', 0, 'modules', 0, 'data', 'uploadDate'))

        return {
            'author': self._html_search_regex(
                r'<meta name="parsely-author" content="([^<]+)"',
                webpage,
                'video author',
                default=None),
            'channel': self._html_search_regex(
                r'<div class="ClipPlayer-clipPlayerIntroSection"><[^>]*>([^<]+)<',
                webpage,
                'channel name',
                fatal=False),
            'formats': self._extract_akamai_formats(url, str(display_id)),
            'id': display_id,
            'upload_date': unified_strdate(upload_date) if upload_date else None,
            'url': link,
            **traverse_obj(
                self._search_json_ld(webpage, display_id, default={}),
                {
                    'title': 'title',
                    'description': 'description',
                    'duration': 'duration',
                    'timestamp': 'timestamp',
                    'thumbnails': 'thumbnails',
                }),
        }
