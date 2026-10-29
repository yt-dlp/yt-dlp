from .common import InfoExtractor
from ..utils.traversal import traverse_obj


class FilmzieIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?filmzie\.com/content/(?P<id>[a-zA-Z0-9-]+)'
    _TESTS = [{
        'url': 'https://filmzie.com/content/intermate-2019',
        'info_dict': {
            'id': '63a43a6c9b52a1714855eba0',
            'ext': 'mp4',
            'description': 'md5:4dc313028ad2850aaea4084e1814da9e',
            'title': 'Intermate',
        },
    }, {
        'url': 'https://filmzie.com/content/southern-star-2013',
        'info_dict': {
            'id': '62d10d24d68da3293a90bbc5',
            'ext': 'mp4',
            'description': 'md5:259be286dd434bc416841d6cc6abe30b',
            'title': 'Southern Star',
        },
    }]

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
