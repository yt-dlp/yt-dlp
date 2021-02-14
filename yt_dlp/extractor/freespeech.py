from __future__ import unicode_literals

from .common import InfoExtractor
from .youtube import YoutubeIE


class FreespeechIE(InfoExtractor):
    IE_NAME = 'freespeech.org'
    _VALID_URL = r'https?://(?:www\.)?freespeech\.org/stories/(?P<id>.+)'
    _TEST = {
        'add_ie': ['Youtube'],
        'url': 'http://www.freespeech.org/stories/fcc-announces-net-neutrality-rollback-whats-stake/',
        'info_dict': {
            'id': 'waRk6IPqyWM',
            'ext': 'mp4',
            'title': 'What\'s At Stake - Net Neutrality Special',
            'description': 'Presented by MNN and FSTV',
            'upload_date': '20170728',
            'uploader_id': 'freespeechtv',
            'uploader': 'freespeechtv',
        },
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        youtube_url = self._search_regex(
            r'data-video-url="([^"]+)"',
            webpage, 'youtube url')

        return self.url_result(youtube_url, YoutubeIE.ie_key())
