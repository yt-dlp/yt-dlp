from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_iso8601,
    traverse_obj,
    url_or_none,
)


class CloudyCDNIE(InfoExtractor):
    _VALID_URL = r'https?://embed\.cloudycdn\.services/(?P<site_id>[^/]+)/media/(?P<id>[^?]+)'
    _TESTS = [{
        'url': 'https://embed.cloudycdn.services/ltv/media/46k_d23-6000-105?',
        'md5': '64f72a360ca530d5ed89c77646c9eee5',
        'info_dict': {
            'id': '46k_d23-6000-105',
            'ext': 'mp4',
            'timestamp': 1700589151,
            'duration': 1442,
            'upload_date': '20231121',
            'title': 'D23-6000-105_cetstud',
            'thumbnail': 'https://store.cloudycdn.services/tmsp00060/assets/media/660858/placeholder1700589200.jpg',
        }
    }, {
        'url': 'https://embed.cloudycdn.services/izm/media/26e_lv-8-5-1',
        'md5': '798828a479151e2444d8dcfbec76e482',
        'info_dict': {
            'id': '26e_lv-8-5-1',
            'ext': 'mp4',
            'title': 'LV-8-5-1',
            'timestamp': 1669767167,
            'thumbnail': 'https://store.cloudycdn.services/tmsp00120/assets/media/488306/placeholder1679423604.jpg',
            'duration': 1205,
            'upload_date': '20221130',
        }
    }]

    def _real_extract(self, url):
        site_id, video_id = self._match_valid_url(url).group('site_id', 'id')

        json = self._download_json(
            f'https://player.cloudycdn.services/player/{site_id}/media/{video_id}/',
            video_id, data=b'referer=https://embed.cloudycdn.services/')

        formats = []
        subtitles = {}
        for source in traverse_obj(json, ('source', 'sources'), default=[]):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(source.get('src'), video_id)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        return {
            'id': video_id,
            'title': json.get('name'),
            'formats': formats,
            'subtitles': subtitles,
            'duration': int_or_none(json.get('duration')),
            'timestamp': parse_iso8601(json.get('upload_date')),
            'thumbnail': traverse_obj(json, ('source', 'poster', {url_or_none})),
        }
