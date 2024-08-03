from .common import InfoExtractor


class TeachingChannelIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'https?://(?:www\.)?teachingchannel\.org/videos?/(?P<id>[^/?&#]+)'

    _TEST = {
        'url': 'https://www.teachingchannel.org/videos/teacher-teaming-evolution',
        'info_dict': {
            'id': '3swwlzkT',
            'ext': 'mp4',
            'title': 'A History of Teaming',
            'description': 'md5:2a9033db8da81f2edffa4c99888140b3',
            'duration': 422,
            'upload_date': '20170316',
            'timestamp': 1489691297,
        },
        'params': {
            'skip_download': True,
        },
        'add_ie': ['JWPlatform'],
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        mid = self._search_regex(
            r'(?:data-mid=["\']|id=["\']jw-video-player-)([a-zA-Z0-9]{8})',
            webpage, 'media id')

        return self.url_result('jwplatform:' + mid, 'JWPlatform', mid)
