from .brightcove import BrightcoveNewIE
from .common import InfoExtractor


class FitnessBlenderIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?fitnessblender\.com/videos/[\w-]+/(?P<tc>T)?(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.fitnessblender.com/page/fb-plus-player-test',
        'info_dict': {
            'id': '6076568195001',
            'ext': 'mp4',
            'title': 'Sports Endurance Workout - Stamina, Speed, and Agility Workout',
            'thumbnail': r're:^https://.+\.jpg',
        },
        'params': {'skip_download': 'm3u8'},
    }]
    def _real_extract(self, url):
        video_id = self._match_valid_url(url).group('id')

        account_id = '6036648099001'
        player_id = 'skIgx8kLxj'

        return self.url_result(
            f'https://players.brightcove.net/{account_id}/{player_id}_default/index.html?videoId={video_id}',
            BrightcoveNewIE)
