import json

from .common import InfoExtractor
from ..utils import float_or_none, parse_iso8601, str_or_none, try_call, url_or_none
from ..utils.traversal import traverse_obj, value


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
            'channel_id': '4',
            'duration': 7918,
            'cast': ['Devonanustart', 'Phonelosers'],
            'description': '',
            'categories': ['prank'],
            'tags': ['prank call', 'prank', 'live show'],
            'upload_date': '20220825',
        },
    }, {
        'url': 'https://prankcast.com/phonelosers/showreel/2048-NOT-COOL',
        'info_dict': {
            'id': '2048',
            'ext': 'mp3',
            'title': 'NOT COOL',
            'display_id': 'NOT-COOL',
            'timestamp': 1665028364,
            'uploader': 'phonelosers',
            'channel_id': '6',
            'duration': 4044,
            'cast': ['phonelosers'],
            'description': '',
            'categories': ['prank'],
            'tags': ['prank call', 'prank', 'live show'],
            'upload_date': '20221006',
        },
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
            'channel_id': str_or_none(json_info.get('user_id')),
            'duration': try_call(lambda: parse_iso8601(json_info['end_date']) - start_date),
            'cast': list(filter(None, [uploader, *traverse_obj(guests_json, (..., 'name'))])),
            'description': json_info.get('broadcast_description'),
            'categories': [json_info.get('broadcast_category')],
            'tags': try_call(lambda: json_info['broadcast_tags'].split(',')),
        }


class PrankCastPostIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?prankcast\.com/[^/?#]+/posts/(?P<id>\d+)-(?P<display_id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://prankcast.com/devonanustart/posts/6214-happy-national-rachel-day-',
        'info_dict': {
            'id': '6214',
            'ext': 'mp3',
            'title': 'Happy National Rachel Day!',
            'display_id': 'happy-national-rachel-day-',
            'timestamp': 1704333938,
            'uploader': 'Devonanustart',
            'channel_id': '4',
            'duration': 13175,
            'cast': ['Devonanustart'],
            'description': '',
            'categories': ['prank call'],
            'upload_date': '20240104',
        },
    }, {
        'url': 'https://prankcast.com/despicabledogs/posts/6217-jake-the-work-crow-',
        'info_dict': {
            'id': '6217',
            'ext': 'mp3',
            'title': 'Jake the Work Crow!',
            'display_id': 'jake-the-work-crow-',
            'timestamp': 1704346592,
            'uploader': 'despicabledogs',
            'channel_id': '957',
            'duration': 263.287,
            'cast': ['despicabledogs'],
            'description': 'https://imgur.com/a/vtxLvKU',
            'upload_date': '20240104',
        },
    }, {
        'url': 'https://prankcast.com/drtomservo/posts/11988-butteye-s-late-night-stank-episode-1-part-1-',
        'info_dict': {
            'id': '11988',
            'ext': 'mp3',
            'title': 'Butteye\'s Late Night Stank Episode 1 (Part 1)',
            'display_id': 'butteye-s-late-night-stank-episode-1-part-1-',
            'timestamp': 1754238686,
            'uploader': 'DrTomServo',
            'channel_id': '136',
            'duration': 2176.464,
            'cast': ['DrTomServo'],
            'description': '',
            'upload_date': '20250803',
        },
    }, {
        'url': 'https://prankcast.com/drtomservo/posts/12105-butteye-s-late-night-stank-episode-08-16-2025-part-2',
        'info_dict': {
            'id': '12105',
            'ext': 'mp3',
            'title': 'Butteye\'s Late Night Stank Episode 08-16-2025 Part 2',
            'display_id': 'butteye-s-late-night-stank-episode-08-16-2025-part-2',
            'timestamp': 1755453505,
            'uploader': 'DrTomServo',
            'channel_id': '136',
            'duration': 19018.392,
            'cast': ['DrTomServo'],
            'description': '',
            'upload_date': '20250817',
        },
    }]

    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).group('id', 'display_id')

        webpage = self._download_webpage(url, video_id)
        post = self._search_nextjs_data(webpage, video_id)['props']['pageProps']['ssr_data_posts']
        content = self._parse_json(post['post_contents_json'], video_id)[0]

        return {
            'id': video_id,
            'display_id': display_id,
            'title': self._og_search_title(webpage),
            **traverse_obj(post, {
                'title': ('post_title', {str}),
                'description': ('post_body', {str}),
                'tags': ('post_tags', {lambda x: x.split(',')}, ..., {str.strip}, filter),
                'channel_id': ('user_id', {int}, {str_or_none}),
                'uploader': ('user_name', {str}),
            }),
            **traverse_obj(content, {
                'url': (('secure_url', 'url'), {url_or_none}, any),
                'timestamp': ((
                    (('start_date', 'crdate'), {parse_iso8601(delimiter=' ')}),
                    ('created_at', {parse_iso8601}),
                ), any),
                'duration': ('duration', {float_or_none}),
                'categories': ('category', {str}, filter, all, filter),
                'cast': ((
                    {value(post.get('user_name'))},
                    ('guests_json', {json.loads}, ..., 'name'),
                ), {str}, filter),
            }),
        }
