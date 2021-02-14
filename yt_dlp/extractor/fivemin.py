from __future__ import unicode_literals

from .common import InfoExtractor


class FiveMinIE(InfoExtractor):
    IE_NAME = '5min'
    _VALID_URL = r'(?:5min:|https?://(?:[^/]*?5min\.com/|delivery\.vidible\.tv/aol)(?:(?:Scripts/PlayerSeed\.js|playerseed/?)?\?.*?playList=)?)(?P<id>\d+)'

    _TESTS = [
        {
            # From http://www.engadget.com/2013/11/15/ipad-mini-retina-display-review/
            'url': 'http://pshared.5min.com/Scripts/PlayerSeed.js?sid=281&width=560&height=345&playList=518013791',
            'md5': '4f7b0b79bf1a470e5004f7112385941d',
            'info_dict': {
                'id': '518013791',
                'ext': 'mp4',
                'title': 'iPad Mini with Retina Display Review',
                'description': 'iPad mini with Retina Display review',
                'duration': 177,
                'uploader': 'engadget',
                'upload_date': '20131115',
                'timestamp': 1384515288,
            },
            'params': {
                # m3u8 download
                'skip_download': True,
            }
        },
        {
            # From http://on.aol.com/video/how-to-make-a-next-level-fruit-salad-518086247
            'url': '5min:518086247',
            'md5': 'e539a9dd682c288ef5a498898009f69e',
            'info_dict': {
                'id': '518086247',
                'ext': 'mp4',
                'title': 'How to Make a Next-Level Fruit Salad',
                'duration': 184,
            },
            'skip': 'no longer available',
        },
        {
            'url': 'http://embed.5min.com/518726732/',
            'only_matching': True,
        },
        {
            'url': 'http://delivery.vidible.tv/aol?playList=518013791',
            'only_matching': True,
        }
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result('aol-video:%s' % video_id)
