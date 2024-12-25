from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    extract_attributes,
    get_element_by_class,
    get_element_html_by_class,
    multipart_encode,
    str_or_none,
    unified_timestamp,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class PiaLiveIE(InfoExtractor):
    _VALID_URL = r'https?://player\.pia-live\.jp/stream/(?P<id>[\w-]+)'
    _PLAYER_ROOT_URL = 'https://player.pia-live.jp/'
    _PIA_LIVE_API_URL = 'https://api.pia-live.jp'
    _API_KEY = 'kfds)FKFps-dms9e'
    _TESTS = [{
        'url': 'https://player.pia-live.jp/stream/4JagFBEIM14s_hK9aXHKf3k3F3bY5eoHFQxu68TC6krUDqGOwN4d61dCWQYOd6CTxl4hjya9dsfEZGsM4uGOUdax60lEI4twsXGXf7crmz8Gk__GhupTrWxA7RFRVt76',
        'info_dict': {
            'id': '88f3109a-f503-4d0f-a9f7-9f39ac745d84',
            'display_id': '2431867_001',
            'title': 'こながめでたい日２０２４の視聴ページ | PIA LIVE STREAM(ぴあライブストリーム)',
            'live_status': 'was_live',
            'comment_count': int,
        },
        'params': {
            'getcomments': True,
            'skip_download': True,
            'ignore_no_formats_error': True,
        },
        'skip': 'The video is no longer available',
    }, {
        'url': 'https://player.pia-live.jp/stream/4JagFBEIM14s_hK9aXHKf3k3F3bY5eoHFQxu68TC6krJdu0GVBVbVy01IwpJ6J3qBEm3d9TCTt1d0eWpsZGj7DrOjVOmS7GAWGwyscMgiThopJvzgWC4H5b-7XQjAfRZ',
        'info_dict': {
            'id': '9ce8b8ba-f6d1-4d1f-83a0-18c3148ded93',
            'display_id': '2431867_002',
            'title': 'こながめでたい日２０２４の視聴ページ | PIA LIVE STREAM(ぴあライブストリーム)',
            'live_status': 'was_live',
            'comment_count': int,
        },
        'params': {
            'getcomments': True,
            'skip_download': True,
            'ignore_no_formats_error': True,
        },
        'skip': 'The video is no longer available',
    }]

    def _extract_var(self, variable, html):
        return self._search_regex(
            rf'(?:var|const|let)\s+{variable}\s*=\s*(["\'])(?P<value>(?:(?!\1).)+)\1',
            html, f'variable {variable}', group='value')

    def _real_extract(self, url):
        video_key = self._match_id(url)
        webpage = self._download_webpage(url, video_key)

        program_code = self._extract_var('programCode', webpage)
        article_code = self._extract_var('articleCode', webpage)
        title = self._html_extract_title(webpage)

        if get_element_html_by_class('play-end', webpage):
            raise ExtractorError('The video is no longer available', expected=True, video_id=program_code)

        if start_info := clean_html(get_element_by_class('play-waiting__date', webpage)):
            date, time = self._search_regex(
                r'(?P<date>\d{4}/\d{1,2}/\d{1,2})\([月火水木金土日]\)(?P<time>\d{2}:\d{2})',
                start_info, 'start_info', fatal=False, group=('date', 'time'))
            if date and time:
                release_timestamp_str = f'{date} {time} +09:00'
                release_timestamp = unified_timestamp(release_timestamp_str)
                self.raise_no_formats(f'The video will be available after {release_timestamp_str}', expected=True)
                return {
                    'id': program_code,
                    'title': title,
                    'live_status': 'is_upcoming',
                    'release_timestamp': release_timestamp,
                }

        payload, content_type = multipart_encode({
            'play_url': video_key,
            'api_key': self._API_KEY,
        })
        api_data_and_headers = {
            'data': payload,
            'headers': {'Content-Type': content_type, 'Referer': self._PLAYER_ROOT_URL},
        }

        player_tag_list = self._download_json(
            f'{self._PIA_LIVE_API_URL}/perf/player-tag-list/{program_code}', program_code,
            'Fetching player tag list', 'Unable to fetch player tag list', **api_data_and_headers)

        return self.url_result(
            extract_attributes(player_tag_list['data']['movie_one_tag'])['src'],
            url_transparent=True, title=title, display_id=program_code,
            __post_extractor=self.extract_comments(program_code, article_code, api_data_and_headers))

    def _get_comments(self, program_code, article_code, api_data_and_headers):
        chat_room_url = traverse_obj(self._download_json(
            f'{self._PIA_LIVE_API_URL}/perf/chat-tag-list/{program_code}/{article_code}', program_code,
            'Fetching chat info', 'Unable to fetch chat info', fatal=False, **api_data_and_headers),
            ('data', 'chat_one_tag', {extract_attributes}, 'src', {url_or_none}))
        if not chat_room_url:
            return
        comment_page = self._download_webpage(
            chat_room_url, program_code, 'Fetching comment page', 'Unable to fetch comment page',
            fatal=False, headers={'Referer': self._PLAYER_ROOT_URL})
        if not comment_page:
            return
        yield from traverse_obj(self._search_json(
            r'var\s+_history\s*=', comment_page, 'comment list',
            program_code, contains_pattern=r'\[(?s:.+)\]', fatal=False), (..., {
                'timestamp': (0, {int}),
                'author_is_uploader': (1, {lambda x: x == 2}),
                'author': (2, {str}),
                'text': (3, {str}),
                'id': (4, {str_or_none}),
            }))
