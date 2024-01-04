from .common import InfoExtractor
from ..utils import parse_iso8601, traverse_obj, try_call


class PrankCastIE(InfoExtractor):
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
            'channel_id': 4,
            'duration': 13175,
            'cast': ['Devonanustart'],
            'description': '',
            'categories': ['prank call'],
            'tags': [''],
            'upload_date': '20240104'
        }
    }, {
        'url': 'https://prankcast.com/despicabledogs/posts/6217-jake-the-work-crow-',
        'info_dict': {
            'id': '6217',
            'ext': 'mp3',
            'title': 'Jake the Work Crow!',
            'display_id': 'jake-the-work-crow-',
            'timestamp': 1704346592,
            'uploader': 'despicabledogs',
            'channel_id': 957,
            'duration': 263,
            'cast': ['despicabledogs'],
            'description': 'https://imgur.com/a/vtxLvKU',
            'categories': [],
            'tags': [''],
            'upload_date': '20240104'
        }
    }]

    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).group('id', 'display_id')

        webpage = self._download_webpage(url, video_id)
        json_info = self._search_nextjs_data(webpage, video_id)['props']['pageProps']['ssr_data_posts']
        json_post_info = self._parse_json(json_info['post_contents_json'], video_id)[0]

        uploader = json_info.get('user_name')
        guests_json = self._parse_json(json_post_info.get('guests_json') or '{}', video_id)

        broadcast_id = json_info.get('content_id')
        live_chat_url = f'https://prankcast.com/api/private/chat/select-broadcast?id={broadcast_id}&cache='

        return {
            'id': video_id,
            'title': json_info.get('post_title') or self._og_search_title(webpage),
            'display_id': display_id,
            'url': json_post_info.get('url'),
            'timestamp': parse_iso8601(json_post_info.get('start_date') or json_post_info.get('crdate'), ' '),
            'uploader': uploader,
            'channel_id': json_info.get('user_id'),
            'duration': round(json_post_info.get('duration') or 0),
            'cast': list(filter(None, [uploader] + traverse_obj(guests_json, (..., 'name')))),
            'description': json_info.get('post_body'),
            'categories': list(filter(None, [json_post_info.get('category')])),
            'tags': try_call(lambda: json_info['post_tags'].split(',')),
            'subtitles': {'live_chat': [{'url': live_chat_url}]} if broadcast_id else None
        }
