from .common import InfoExtractor
from .piaulizaportal import PIAULIZAPortalAPIIE
from ..utils import ExtractorError, multipart_encode, smuggle_url


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
            },
            'params': {
                'skip_download': True,
                'ignore_no_formats_error': True,
            },
        },
    ]

    def handle_embed_player(self, player_tag, video_id, info_dict={}):
        player_data_url = self._search_regex([PIAULIZAPortalAPIIE.TAG_REGEX_PATTERN],
                                             player_tag, 'player data url', fatal=False)

        if PIAULIZAPortalAPIIE.BASE_URL in player_data_url:
            return self.url_result(
                smuggle_url(
                    player_data_url,
                    {'video_id': video_id, 'referer': self.PLAYER_ROOT_URL, 'info_dict': info_dict},
                ),
                ie=PIAULIZAPortalAPIIE.ie_key(),
            )

        raise ExtractorError('Unsupported streaming platform', expected=True)

    def _real_extract(self, url):
        video_key = self._match_id(url)
        webpage = self._download_webpage(url, video_key)
        program_code = self._search_regex(r"const programCode = '(.*?)';", webpage, 'program code')

        prod_configure = self._download_webpage(
            self.PLAYER_ROOT_URL + self._search_regex(r'<script [^>]*\bsrc="(/statics/js/s_prod[^"]+)"', webpage, 'prod configure page'),
            program_code,
            headers={'Referer': self.PLAYER_ROOT_URL},
            note='Fetching prod configure page', errnote='Unable to fetch prod configure page',
        )

        api_key = self._search_regex(r"const APIKEY = '(.*?)';", prod_configure, 'api key')
        payload, content_type = multipart_encode({
            'play_url': video_key,
            'api_key': api_key,
        })
        player_tag_list = self._download_json(
            f'{self.PIA_LIVE_API_URL}/perf/player-tag-list/{program_code}',
            program_code,
            data=payload,
            headers={
                'Content-Type': content_type,
            },
        )

        return self.handle_embed_player(
            player_tag_list['data']['movie_one_tag'],
            video_id=program_code,
            info_dict={
                'id': program_code,
                'title': self._html_extract_title(webpage),
            },
        )
