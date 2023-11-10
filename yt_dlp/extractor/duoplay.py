from .common import InfoExtractor
from ..utils import (
    traverse_obj,
    unified_timestamp,
    strip_or_none,
)


class DuoplayIE(InfoExtractor):
    _VALID_URL = r'https://duoplay\.ee/(?P<id>\d+)/'
    _TESTS = [{
        'note': 'Siberi võmm S02E12',
        'url': 'https://duoplay.ee/4312/siberi-vomm?ep=24',
        'md5': '1ff59d535310ac9c5cf5f287d8f91b2d',
        'info_dict': {
            'id': '4312',
            'ext': 'mp4',
            'title': 'Operatsioon "Öö"',
            'thumbnail': r're:https://.+\.jpg(?:\?c=\d+)?$',
            'description': 'md5:8ef98f38569d6b8b78f3d350ccc6ade8',
            'upload_date': '20170523',
            'timestamp': 1495567800,
            'series': 'Siberi võmm',
            'series_id': 4312,
            'season': 'Season 2',
            'season_number': 2,
            'episode': 'Operatsioon "Öö"',
            'episode_number': 12,
            'episode_id': 24,
        },
    }, {
        'note': 'Empty title',
        'url': 'https://duoplay.ee/17/uhikarotid?ep=14',
        'md5': '6aca68be71112314738dd17cced7f8bf',
        'info_dict': {
            'id': '17',
            'ext': 'mp4',
            'title': 'Episode 14',
            'thumbnail': r're:https://.+\.jpg(?:\?c=\d+)?$',
            'description': 'md5:4719b418e058c209def41d48b601276e',
            'upload_date': '20100916',
            'timestamp': 1284661800,
            'series': 'Ühikarotid',
            'series_id': 17,
            'season': 'Season 2',
            'season_number': 2,
            'episode_id': 14,
        },
    }]

    def _real_extract(self, url):
        def decode_quot(s: str):
            return s.replace("&quot;", '"')

        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        manifest_url = self._search_regex(r'<video-player[^>]+manifest-url="([^"]+)"', webpage, 'video-player')
        episode_attr = self._search_regex(r'<video-player[^>]+:episode="([^"]+)"', webpage, 'episode data')
        ep = self._parse_json(episode_attr, video_id, decode_quot)

        return {
            'id': video_id,
            'formats': self._extract_m3u8_formats(video_player['manifest-url'], video_id, 'mp4'),
            **traverse_obj(episode_attr, {
                'title': (None, ('subtitle', ('episode_id', {lambda x: f'Episode {x}'}))),
                'description': 'synopsis',
                'thumbnail': ('images', 'original'),
                'timestamp': ('airtime', {lambda x: unified_timestamp(x + ' +0200')}),
                'series': 'title',
                'series_id': ('telecast_id', {str_or_none}),
                'season_number': ('season_id', {int_or_none}),
                'episode': 'subtitle',
                'episode_number': (None, ('episode_nr', 'episode_id'), {int_or_none}),
            }, get_all=False),
        }
