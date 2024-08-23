from .common import InfoExtractor
from .piaulizaportal import PIAULIZAPortalAPIIE
from ..utils import ExtractorError, extract_attributes, multipart_encode, smuggle_url, traverse_obj


class PiaLiveIE(InfoExtractor):
    PLAYER_ROOT_URL = 'https://player.pia-live.jp'
    PIA_LIVE_API_URL = 'https://api.pia-live.jp'
    _VALID_URL = r'https?://player\.pia-live\.jp/stream/(?P<id>[\w-]+)'

    _TESTS = [
        {
            'url': 'https://player.pia-live.jp/stream/4JagFBEIM14s_hK9aXHKf3k3F3bY5eoHFQxu68TC6krUDqGOwN4d61dCWQYOd6CTxl4hjya9dsfEZGsM4uGOUdax60lEI4twsXGXf7crmz8Gk__GhupTrWxA7RFRVt76',
            'info_dict': {
                'id': '2431867_001',
                'title': 'こながめでたい日２０２４の視聴ページ | PIA LIVE STREAM(ぴあライブストリーム)',
                'live_status': 'was_live',
                'comment_count': 1000,
            },
            'params': {
                'skip_download': True,
                'ignore_no_formats_error': True,
            },
        },
        {
            'url': 'https://player.pia-live.jp/stream/4JagFBEIM14s_hK9aXHKf3k3F3bY5eoHFQxu68TC6krJdu0GVBVbVy01IwpJ6J3qBEm3d9TCTt1d0eWpsZGj7DrOjVOmS7GAWGwyscMgiThopJvzgWC4H5b-7XQjAfRZ',
            'info_dict': {
                'id': '2431867_002',
                'title': 'こながめでたい日２０２４の視聴ページ | PIA LIVE STREAM(ぴあライブストリーム)',
                'live_status': 'was_live',
                'comment_count': 1000,
            },
            'params': {
                'skip_download': True,
                'ignore_no_formats_error': True,
            },
        },
    ]

    def handle_embed_player(self, player_tag, info_dict={}):
        player_data_url = extract_attributes(player_tag)['src']

        if player_data_url.startswith(PIAULIZAPortalAPIIE.BASE_URL):
            return self.url_result(
                smuggle_url(
                    player_data_url,
                    {'referer': self.PLAYER_ROOT_URL},
                ),
                ie=PIAULIZAPortalAPIIE.ie_key(),
                url_transparent=True,
                **info_dict,
            )

        raise ExtractorError('Unsupported streaming platform', expected=True)

    def _real_extract(self, url):
        video_key = self._match_id(url)
        webpage = self._download_webpage(url, video_key)
        program_code = self._search_regex(r"const programCode = '(.*?)';", webpage, 'program code')

        prod_configure = self._download_webpage(
            self.PLAYER_ROOT_URL + self._search_regex(r'<script [^>]*\bsrc="(/statics/js/s_prod[^"]+)"', webpage, 'prod configure page'),
            program_code, headers={'Referer': self.PLAYER_ROOT_URL},
            note='Fetching prod configure page', errnote='Unable to fetch prod configure page',
        )

        api_key = self._search_regex(r"const APIKEY = '(.*?)';", prod_configure, 'api key')
        payload, content_type = multipart_encode({
            'play_url': video_key,
            'api_key': api_key,
        })
        player_tag_list = self._download_json(
            f'{self.PIA_LIVE_API_URL}/perf/player-tag-list/{program_code}',
            program_code, data=payload, headers={'Content-Type': content_type, 'Referer': self.PLAYER_ROOT_URL},
        )

        article_code = self._search_regex(r"const articleCode = '(.*?)';", webpage, 'article code')
        chat_info = self._download_json(
            f'{self.PIA_LIVE_API_URL}/perf/chat-tag-list/{program_code}/{article_code}',
            program_code, data=payload, headers={'Content-Type': content_type, 'Referer': self.PLAYER_ROOT_URL},
        )['data']['chat_one_tag']
        chat_room_url = extract_attributes(chat_info)['src']
        comment_page = self._download_webpage(
            chat_room_url, program_code, headers={'Referer': f'{self.PLAYER_ROOT_URL}/'}, note='Fetching comment page', errnote='Unable to fetch comment page')
        comment_list = self._search_json(
            r'var\s+_history\s*=', comment_page, 'comment list', program_code,
            contains_pattern=r'\[(?s:.+)\]') or []
        comments = traverse_obj(comment_list, (..., {
            'timestamp': (0),
            'author_is_uploader': (1, {lambda x: x == 2}),
            'author': (2),
            'text': (3),
            'id': (4),
        }))

        return self.handle_embed_player(
            player_tag_list['data']['movie_one_tag'],
            info_dict={
                'id': program_code,
                'title': self._html_extract_title(webpage),
                'comments': comments,
                'comment_count': len(comments),
            },
        )
