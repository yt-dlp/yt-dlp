from .common import InfoExtractor
from ..utils import parse_iso8601, traverse_obj, try_call


class PrankCastIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?prankcast\.com/[^/?#]+/showreel/(?P<id>\d+)-(?P<display_id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://prankcast.com/Devonanustart/showreel/1561-Beverly-is-back-like-a-heart-attack-',
        'info_dict': {
            'id': '1561',
            'ext': 'mp3',
            'title': 'Beverly is back like a heart attack!',
            'display_id': 'Beverly-is-back-like-a-heart-attack-',
            'timestamp': 1661391575,
            'uploader': 'Devonanustart',
            'channel_id': 4,
            'duration': 7918,
            'cast': ['Devonanustart', 'Phonelosers'],
            'description': '',
            'categories': ['prank'],
            'tags': ['prank call', 'prank'],
            'upload_date': '20220825'
        }
    }, {
        'url': 'https://prankcast.com/phonelosers/showreel/2048-NOT-COOL',
        'info_dict': {
            'id': '2048',
            'ext': 'mp3',
            'title': 'NOT COOL',
            'display_id': 'NOT-COOL',
            'timestamp': 1665028364,
            'uploader': 'phonelosers',
            'channel_id': 6,
            'duration': 4044,
            'cast': ['phonelosers'],
            'description': '',
            'categories': ['prank'],
            'tags': ['prank call', 'prank'],
            'upload_date': '20221006'
        }
    }]

    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).group('id', 'display_id')

        webpage = self._download_webpage(url, video_id)
        json_info = self._search_nextjs_data(webpage, video_id)['props']['pageProps']['ssr_data_showreel']

        uploader = json_info.get('user_name')
        guests_json = self._parse_json(json_info.get('guests_json') or '{}', video_id)
        start_date = parse_iso8601(json_info.get('start_date'))

        return {
            'id': video_id,
            'title': json_info.get('broadcast_title') or self._og_search_title(webpage),
            'display_id': display_id,
            'url': f'{json_info["broadcast_url"]}{json_info["recording_hash"]}.mp3',
            'timestamp': start_date,
            'uploader': uploader,
            'channel_id': json_info.get('user_id'),
            'duration': try_call(lambda: parse_iso8601(json_info['end_date']) - start_date),
            'cast': list(filter(None, [uploader] + traverse_obj(guests_json, (..., 'name')))),
            'description': json_info.get('broadcast_description'),
            'categories': [json_info.get('broadcast_category')],
            'tags': self._parse_json(json_info.get('broadcast_tags') or '{}', video_id)
        }
