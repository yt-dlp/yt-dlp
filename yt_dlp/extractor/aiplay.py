from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    urljoin,
)


class AIPlayIE(InfoExtractor):
    IE_NAME = 'aiplay'
    IE_DESC = 'AIPlay.it'
    _VALID_URL = r'https?://app\.aiplay\.it/programs/(?P<id>[^/?#]+)'
    _TEST = {

        'url': 'https://app.aiplay.it/programs/creazione-di-un-avatar-ai-con-nano-banana-e-higgsfield?category_id=277143',
        'info_dict': {
            'id': 'creazione-di-un-avatar-ai-con-nano-banana-e-higgsfield',
            'ext': 'mp4',
            'title': 'Creazione di un Avatar AI con Nano Banana e Higgsfield',
            'description': r're:.+',
            'thumbnail': r're:^https?://.+',
            'duration': 1329,
        },
        'params': {'skip_download': True},
    }

    _FRAME_RE = r'<turbo-frame[^>]+id=(["\'])program_(?:show|content|player)\1[^>]+src=(["\'])(?P<url>[^"\']+)\2'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        page = webpage
        m3u8_url = None
        next_src = self._search_regex(
            self._FRAME_RE, page, 'frame', group='url', default=None)

        for _ in range(5):
            m3u8_url = self._search_regex(
                r'(https?://stream\.mux\.com/[^"\'\s<>]+\.m3u8[^"\'\s<>]*)',
                page, 'm3u8 url', default=None)
            if m3u8_url or not next_src:
                break
            page = self._download_webpage(
                urljoin(url, next_src), video_id,
                note='Downloading fragment',
                headers={'Accept': 'text/vnd.turbo-stream.html, text/html'})
            next_src = self._search_regex(
                self._FRAME_RE, page, 'frame', group='url', default=None)

        if not m3u8_url:
            raise ExtractorError(
                'No video found, login may be required', expected=True)

        headers = {
            'Origin': 'https://app.aiplay.it',
            'Referer': 'https://app.aiplay.it/',
        }
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            m3u8_url, video_id, 'mp4',
            entry_protocol='m3u8_native', m3u8_id='hls', headers=headers)
        for f in formats:
            f['http_headers'] = headers

        info = self._search_json_ld(webpage, video_id, default={})
        return {
            'id': video_id,
            'title': info.get('title') or self._og_search_title(webpage),
            'description': info.get('description') or self._og_search_description(webpage, default=None),
            'thumbnail': info.get('thumbnail') or self._og_search_thumbnail(webpage, default=None),
            'duration': info.get('duration'),
            'formats': formats,
            'subtitles': subtitles,
            'http_headers': headers,
        }
