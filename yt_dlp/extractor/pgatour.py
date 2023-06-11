from .brightcove import BrightcoveNewIE
from .common import InfoExtractor


class PGATourIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?pgatour\.com/video/[\w-]+/(?P<tc>T)?(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.pgatour.com/video/competition/T6322447785112/adam-hadwin-2023-the-players-round-4-18th-hole-shot-1',
        'info_dict': {
            'id': '6322447785112',
            'ext': 'mp4',
            'title': 'Adam Hadwin | 2023 THE PLAYERS | Round 4 | 18th hole | Shot 1',
            'uploader_id': '6116716431001',
            'upload_date': '20230312',
            'timestamp': 1678653136,
            'duration': 20.011,
            'thumbnail': r're:^https://.+\.jpg',
            'tags': 'count:7',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.pgatour.com/video/features/6322506425112/follow-the-players-trophy-on-championship-sunday',
        'info_dict': {
            'id': '6322506425112',
            'ext': 'mp4',
            'title': 'Follow THE PLAYERS trophy on Championship Sunday',
            'description': 'md5:4d29e4bdfa03694a0ebfd08950398568',
            'uploader_id': '6082840763001',
            'upload_date': '20230313',
            'timestamp': 1678739835,
            'duration': 123.435,
            'thumbnail': r're:^https://.+\.jpg',
            'tags': 'count:8',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        video_id, is_tourcast = self._match_valid_url(url).group('id', 'tc')

        # From https://www.pgatour.com/_next/static/chunks/pages/_app-8bcf849560daf38d.js
        account_id = '6116716431001' if is_tourcast else '6082840763001'
        player_id = 'Vsd5Umu8r' if is_tourcast else 'FWIBYMBPj'

        return self.url_result(
            f'https://players.brightcove.net/{account_id}/{player_id}_default/index.html?videoId={video_id}',
            BrightcoveNewIE)
