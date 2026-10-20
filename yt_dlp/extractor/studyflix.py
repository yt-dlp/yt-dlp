from .common import InfoExtractor
from ..utils import extract_attributes, url_or_none
from ..utils.traversal import traverse_obj


class StudyflixIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?studyflix\.de/(?:.*)/(?:[^/?#]+-)?(?P<id>\d+)'
    _TESTS = [{
            'url': 'https://studyflix.de/ingenieurwissenschaften/arbeit-und-energie-ii-371',
            'info_dict': {
                'id': '371',
                'ext': 'mp4',
                'thumbnail': r're:^https?://.*\.(?:png|jpg)',
                'title': 'Arbeit und Energie Übung',
            },
        }, {
            'url': 'https://studyflix.de/ingenieurwissenschaften/winkelgeschwindigkeit-1533',
            'info_dict': {
                'id': '1533',
                'ext': 'mp4',
                'thumbnail': r're:^https?://.*\.(?:png|jpg)',
                'title': 'Winkelgeschwindigkeit',
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