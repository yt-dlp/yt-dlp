from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    join_nonempty,
    traverse_obj,
    unified_timestamp,
    update_url_query,
)


class DuoplayIE(InfoExtractor):
    _VALID_URL = r'https://duoplay\.ee/(?P<id>\d+)/'
    _TESTS = [{
        'note': 'S02E12',
        'url': 'https://duoplay.ee/4312/siberi-vomm?ep=24',
        'md5': '7ea7b16266ec1798743777df241883dd',
        'info_dict': {
            'id': '40792',
            'ext': 'mp4',
            'title': 'Osa 12 - Operatsioon "Öö"',
            'thumbnail': r're:https?://.*\.jpg$',
            'description': 'md5:53cabf3c5d73150d594747f727431248',
            'upload_date': '20160805',
            'timestamp': 1470420000,
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
            'title': join_nonempty(traverse_obj(ep, 'title'), traverse_obj(ep, 'subtitle'), delim=' / '),
            'description': traverse_obj(ep, 'synopsis'),
            'thumbnail': traverse_obj(ep, ('images', 'original')),
            'formats': self._extract_m3u8_formats(manifest_url, video_id, 'mp4'),
            'timestamp': unified_timestamp(traverse_obj(ep, 'airtime') + ' +0200'),
        }
