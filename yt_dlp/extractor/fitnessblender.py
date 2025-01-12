from .brightcove import BrightcoveNewIE
from .common import InfoExtractor


class FitnessBlenderIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?fitnessblender\.com/videos/'

    _TESTS = [{
        'url': 'https://www.fitnessblender.com/videos/lower-body-strength-hiit-workout-strength-sets-with-hiit-cardio-burst',
        'info_dict': {
            'id': '6296677311001',
            'ext': 'mp4',
            'title': 'WO 2022-02-02 Ks Lower Body HIIT and Strength',
            'thumbnail': r're:^https://.+\.jpg',
        },
        'params': {'skip_download': 'm3u8'},
    }]
    def _real_extract(self, url):
        video_id = self._match_valid_url(url).group('id')

        return self.url_result(
            f'https://players.brightcove.net/6036648099001/skIgx8kLxj_default/index.html?videoId={video_id}',
            BrightcoveNewIE, video_id)

