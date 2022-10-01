from .common import InfoExtractor
from .zype import ZypeIE

class OfTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?of.tv/video/(?P<id>[0-9a-zA-Z]+)'
    _TESTS = [{
        'url': 'https://of.tv/video/627d7d95b353db0001dadd1a',
        'md5': '',
        'info_dict': {
            'id': '627d7d95b353db0001dadd1a',
            'ext': 'mp4',
            'title': '',
            'thumbnail': r're:^https?://.*\.jpg$',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        extraction = ZypeIE.extract_from_webpage(self._downloader, url, webpage)
        output = list(extraction)
        print(f'extractor: {output[0]}')
        return output[0]
