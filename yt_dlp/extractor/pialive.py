from .common import InfoExtractor
from .piaulizaportal import PIAULIZAPortalAPIIE
from ..networking import Request
from ..utils import multipart_encode, smuggle_url


class PiaLiveIE(InfoExtractor):
    PLAYER_ROOT_URL = 'https://player.pia-live.jp'
    PIA_LIVE_API_URL = 'https://api.pia-live.jp'
    _VALID_URL = r'https?://player\.pia-live\.jp/stream/(?P<id>[\w-]+)'

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
            Request(
                url=f'{self.PIA_LIVE_API_URL}/perf/player-tag-list/{program_code}',
                method='POST',
                data=payload,
                headers={
                    'Content-Type': content_type,
                },
            ),
            program_code,
        )

        player_data_url = self._search_regex(PIAULIZAPortalAPIIE.SCRIPT_TAG_REGEX_PATTERN,
                                             player_tag_list['data']['movie_one_tag'], 'player data url')

        return {
            **self.url_result(
                smuggle_url(
                    player_data_url,
                    {'video_id': program_code, 'referer': self.PLAYER_ROOT_URL, 'info_dict': {
                        'id': program_code,
                        'title': self._html_extract_title(webpage),
                    }},
                ),
                ie=PIAULIZAPortalAPIIE.ie_key(),
            ),
        }
