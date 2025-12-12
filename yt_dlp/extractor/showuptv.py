from .common import InfoExtractor
from ..utils import UserNotLive


class ShowupTvIE(InfoExtractor):
    IE_NAME = 'showup.tv'
    _VALID_URL = r'https?://(?:www\.)?showup\.tv/(?P<id>[\w-]+)(?:$|[#?])'

    _TESTS = [{
        'url': 'https://showup.tv/malamisia',
        'info_dict': {
            'id': 'c4dfef41fe4f5e9838028f2f8f160086',
            'ext': 'flv',
            'live_status': 'is_live',
            'url': r're:^rtmp://[\w-]+?\.showup\.tv/webrtc/[a-z0-9]{32}_aac$',
            'title': r're:malamisia - Darmowe sex kamerki, chat na żywo. Seks pokazy online - live show webcams \d{4}-\d{2}-\d{1,2} \d{1,2}:\d{1,2}',
            'uploader_id': 'malamisia',
            'uploader_url': 'https://showup.tv/profile/malamisia',
        },
        'params': {
            # rtmp download
            'skip_download': True,
        },
    }, {
        'url': 'https://showup.tv/_Sensej',
        'only_matching': True,
    }, {
        'url': 'https://showup.tv/Lina-hill',
        'only_matching': True,
    }]

    def _real_initialize(self):
        self._set_cookie('showup.tv', 'accept_rules', 'true')

    def _extract_player_var(self, variable, html):
        return self._html_search_regex(
            rf'player\.{variable}\s*=\s*(["\'])(?P<value>(?:(?!\1).)+)\1', html, variable, group='value', default=None)

    def _real_extract(self, url):
        uploader_id = self._match_id(url)
        webpage = self._download_webpage(url, uploader_id)

        stream_id = self._extract_player_var('streamID', webpage)
        if not stream_id:
            raise UserNotLive(video_id=uploader_id)

        return {
            'id': stream_id,
            'title': self._html_extract_title(webpage),
            'uploader_id': uploader_id,
            'uploader_url': f'https://showup.tv/profile/{uploader_id}',
            'url': f'rtmp://{self._extract_player_var("transcoderAddr", webpage)}/webrtc/{stream_id}_aac',
            'ext': 'flv',
            'is_live': True,
        }
