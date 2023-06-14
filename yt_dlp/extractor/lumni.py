from .common import InfoExtractor
from .francetv import FranceTVIE


class LumniIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?lumni\.fr/video/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.lumni.fr/video/l-homme-et-son-environnement-dans-la-revolution-industrielle',
        'md5': '960e8240c4f2c7a20854503a71e52f5e',
        'info_dict': {
            'id': 'd2b9a4e5-a526-495b-866c-ab72737e3645',
            'ext': 'mp4',
            'title': "L'homme et son environnement dans la révolution industrielle - L'ère de l'homme",
            'thumbnail': 'https://assets.webservices.francetelevisions.fr/v1/assets/images/a7/17/9f/a7179f5f-63a5-4e11-8d4d-012ab942d905.jpg',
            'duration': 230,
        }
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        video_id = self._html_search_regex(
            r'<div[^>]+data-factoryid\s*=\s*["\']([^"\']+)', webpage, 'video id')
        return self.url_result(f'francetv:{video_id}', FranceTVIE, video_id)
