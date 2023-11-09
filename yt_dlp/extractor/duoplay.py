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
            # fallback to absolute "episode_id" value
            'title': traverse_obj(ep, 'subtitle') or f"Episode {traverse_obj(ep, 'episode_id')}",
            'description': strip_or_none(traverse_obj(ep, 'synopsis')),
            'thumbnail': traverse_obj(ep, ('images', 'original')),
            'formats': self._extract_m3u8_formats(manifest_url, video_id, 'mp4'),
            'timestamp': unified_timestamp(traverse_obj(ep, 'airtime') + ' +0200'),
            'series': traverse_obj(ep, 'title'),
            'series_id': traverse_obj(ep, 'telecast_id'),
            'season_number': traverse_obj(ep, 'season_id'),
            'episode': traverse_obj(ep, 'subtitle'),
            # fallback to absolute "episode_id" value
            'episode_number': traverse_obj(ep, 'episode_nr') or traverse_obj(ep, 'episode_id'),
            'episode_id': traverse_obj(ep, 'episode_id'),
        }
