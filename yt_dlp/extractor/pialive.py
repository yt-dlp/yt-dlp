from .common import InfoExtractor
from ..utils import extract_attributes, multipart_encode, url_or_none
from ..utils.traversal import traverse_obj


class PiaLiveIE(InfoExtractor):
    PLAYER_ROOT_URL = 'https://player.pia-live.jp/'
    PIA_LIVE_API_URL = 'https://api.pia-live.jp'
    _VALID_URL = r'https?://player\.pia-live\.jp/stream/(?P<id>[\w-]+)'

    _TESTS = [
        {
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
        },
        {
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
        },
    ]

    def _extract_vars(self, variable, html):
        return self._search_regex(
            rf'(?:var|const)\s+{variable}\s*=\s*(["\'])(?P<value>(?:(?!\1).)+)\1',
            html, 'variable', group='value', default=None)

    def _real_extract(self, url):
        video_key = self._match_id(url)
        webpage = self._download_webpage(url, video_key)

        program_code = self._extract_vars('programCode', webpage)
        article_code = self._extract_vars('articleCode', webpage)

        prod_configure = self._download_webpage(
            self.PLAYER_ROOT_URL + self._search_regex(
                r'<script[^>]+src=(["\'])(?P<url>/statics/js/s_prod\?(?:(?!\1).)+)\1',
                webpage, 'prod configure page url', group='url'),
            program_code, headers={'Referer': self.PLAYER_ROOT_URL},
            note='Fetching prod configure page', errnote='Unable to fetch prod configure page')

        payload, content_type = multipart_encode({
            'play_url': video_key,
            'api_key': self._extract_vars('APIKEY', prod_configure)})

        player_tag_list = self._download_json(
            f'{self.PIA_LIVE_API_URL}/perf/player-tag-list/{program_code}', program_code,
            data=payload, headers={'Content-Type': content_type, 'Referer': self.PLAYER_ROOT_URL},
            note='Fetching player tag list', errnote='Unable to fetch player tag list')

        chat_room_url = traverse_obj(self._download_json(
            f'{self.PIA_LIVE_API_URL}/perf/chat-tag-list/{program_code}/{article_code}', program_code,
            data=payload, headers={'Content-Type': content_type, 'Referer': self.PLAYER_ROOT_URL},
            note='Fetching chat info', errnote='Unable to fetch chat info', fatal=False),
            ('data', 'chat_one_tag', {extract_attributes}, 'src', {url_or_none}))

        return self.url_result(
            extract_attributes(player_tag_list['data']['movie_one_tag'])['src'], url_transparent=True,
            video_title=self._html_extract_title(webpage), display_id=program_code,
            __post_extractor=self.extract_comments(program_code, chat_room_url))

    def _get_comments(self, video_id, chat_room_url):
        if not chat_room_url:
            return
        if comment_page := self._download_webpage(
                chat_room_url, video_id, headers={'Referer': f'{self.PLAYER_ROOT_URL}'},
                note='Fetching comment page', errnote='Unable to fetch comment page', fatal=False):
            yield from traverse_obj(self._search_json(
                r'var\s+_history\s*=', comment_page, 'comment list',
                video_id, contains_pattern=r'\[(?s:.+)\]', fatal=False), (..., {
                    'timestamp': 0,
                    'author_is_uploader': (1, {lambda x: x == 2}),
                    'author': 2,
                    'text': 3,
                    'id': 4,
                }))
