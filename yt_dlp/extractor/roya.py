from .common import InfoExtractor
from ..utils.traversal import traverse_obj

ticket_api_base = 'https://ticket.roya-tv.com/api/v5'


class RoyaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:en\.)?roya\.tv/videos/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://en.roya.tv/videos/110671',
        'info_dict': {
            'id': '110671',
            'title': 'حلوة يا دنيا - الاستضافات صالح مرقة نائب رئيس ملتقى الاعمال الفلسطيني الاردنيً',
            'ext': 'mp4',
        },
    }, {
        'url': 'https://roya.tv/videos/0',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        media_id = self._match_id(url)

        stream_url = self._download_json(
            f'{ticket_api_base}/video/{media_id}/ticket', media_id)['data']['secured_url']

        webpage = self._download_webpage(url, media_id)
        watch_for_free_text = ' | شاهد مجانا'
        title = self._html_extract_title(webpage).replace(watch_for_free_text, '')

        return {
            'id': media_id,
            'formats': self._extract_m3u8_formats(stream_url, media_id, 'mp4', m3u8_id='hls', live=False),
            'title': title,
        }


class RoyaLiveIE(InfoExtractor):
    _VALID_URL = r'https?://(?:en\.)?roya\.tv/live-stream/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://en.roya.tv/live-stream/1',
        'info_dict': {
            'id': '1',
            'title': r're:Roya TV \d{4}-\d{2}-\d{2} \d{2}:\d{2}',
            'ext': 'mp4',
            'live_status': 'is_live',
        },
    }, {
        'url': 'https://roya.tv/live-stream/21',
        'info_dict': {
            'id': '21',
            'title': r're:Roya News \d{4}-\d{2}-\d{2} \d{2}:\d{2}',
            'ext': 'mp4',
            'live_status': 'is_live',
        },
    }, {
        'url': 'https://roya.tv/live-stream/10000',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        media_id = self._match_id(url)

        stream_url = self._download_json(
            f'{ticket_api_base}/fastchannel/{media_id}', media_id)['data']['secured_url']

        title = traverse_obj(
            self._download_json('https://backend.roya.tv/api/v01/channels/schedule-pagination', media_id, fatal=False),
            ('data', 0, 'channel', lambda _, v: str(v['id']) == media_id, 'title', {str}, any))

        return {
            'id': media_id,
            'formats': self._extract_m3u8_formats(stream_url, media_id, 'mp4', m3u8_id='hls', live=True),
            'title': title,
            'is_live': True,
        }
