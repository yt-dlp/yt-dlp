from .common import InfoExtractor


class ShowupTvIE(InfoExtractor):
    IE_NAME = 'showup.tv'
    _VALID_URL = r'https?://(?:www\.)?showup\.tv/(?P<id>[\w-]+)(?:$|[#?])'

    _TESTS = [{
        'url': 'https://showup.tv/Kayla',
        'info_dict': {
            'id': '6c6c81226012516a8121da51c135cf54',
            'ext': 'flv',
            'live_status': 'is_live',
            'url': r're:^rtmp://[\w-]+?\.showup\.tv/webrtc/[a-z0-9]{32}_aac$',
            'title': r're:Kayla - Darmowe sex kamerki, chat na żywo. Seks pokazy online - live show webcams \d{4}-\d{2}-\d{1,2} \d{1,2}:\d{1,2}',
            'uploader_id': 'Kayla',
            'uploader_url': 'https://showup.tv/profile/Kayla',
        },
        'params': {
            # rtmp download
            'skip_download': True,
        },
        'skip': 'Room is offline',
    }, {
        'url': 'https://showup.tv/_Sensej',
        'only_matching': True,
    }, {
        'url': 'https://showup.tv/Lina-hill',
        'only_matching': True,
    }]

    def _real_initialize(self):
        self._set_cookie('showup.tv', 'accept_rules', 'true')

    def _extract_player_args(self, variable, html):
        return self._html_search_regex(
            rf'player\.{variable}\s*=\s*(["\'])(?P<value>(?:(?!\1).)+)\1', html, variable, group='value')

    def _real_extract(self, url):
        uploader_id = self._match_id(url)
        webpage = self._download_webpage(url, uploader_id)

        stream_id = self._extract_player_args('streamID', webpage)
        server_url = self._extract_player_args('transcoderAddr', webpage)

        return {
            'id': stream_id,
            'title': self._html_extract_title(webpage),
            'uploader_id': uploader_id,
            'uploader_url': f'https://showup.tv/profile/{uploader_id}',
            'url': f'rtmp://{server_url}/webrtc/{stream_id}_aac',
            'ext': 'flv',
            'is_live': True,
        }
