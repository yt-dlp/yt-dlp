from .common import InfoExtractor
from ..utils.traversal import traverse_obj


class FilmzieIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?filmzie\.com/content/(?P<id>[a-zA-Z0-9-]+)'
    _TESTS = [{
        'url': 'https://filmzie.com/content/intermate-2019?sourceId=613744175971e8001d714ce7',
        'info_dict': {
            'id': '371',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.*\.(?:png|jpg)',
            'title': 'Arbeit und Energie Übung',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        player_host = self._search_regex(r'(<div[^>]+class="video-player-host"[^>]+>)', webpage, 'player_host')
        up_data = extract_attributes(player_host)['up-data']
        up_info = self._parse_json(up_data, video_id)['video']

        return {
            'id': video_id,
            'formats': self._extract_m3u8_formats(up_info['stream_urls'][0], video_id),
            **traverse_obj(up_info, {
                'thumbnail': ('poster_url', {url_or_none}),
                'title': ('title', {str}),
            }),
        }
