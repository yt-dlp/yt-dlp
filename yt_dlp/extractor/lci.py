from .common import InfoExtractor
from .wat import WatIE
from ..utils import ExtractorError, str_or_none
from ..utils.traversal import traverse_obj


class LCIIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?:lci|tf1info)\.fr/(?:[^/?#]+/)+[\w-]+-(?P<id>\d+)\.html'
    _TESTS = [{
        'url': 'https://www.tf1info.fr/replay-lci/videos/video-24h-pujadas-du-vendredi-24-mai-6708-2300831.html',
        'info_dict': {
            'id': '14113788',
            'ext': 'mp4',
            'title': '24H Pujadas du vendredi 24 mai 2024',
            'thumbnail': 'https://photos.tf1.fr/1280/720/24h-pujadas-du-24-mai-2024-55bf2d-0@1x.jpg',
            'upload_date': '20240524',
            'duration': 6158,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'This content is no longer available',
    }, {
        'url': 'https://www.tf1info.fr/politique/election-presidentielle-2022-second-tour-j-2-marine-le-pen-et-emmanuel-macron-en-interview-de-lci-vendredi-soir-2217486.html',
        'info_dict': {
            'id': 'c5647202-4549-4644-a892-1976e78fc5f8',
            'ext': 'mp4',
            'title': 'md5:660df5481fd418bc3bbb0d070e6fdb5a',
            'thumbnail': 'https://photos.tf1.fr/1280/720/presidentielle-2022-marine-le-pen-et-emmanuel-macron-invites-de-lci-ce-vendredi-9c0e73-e1a036-0@1x.jpg',
            'upload_date': '20220422',
            'duration': 33,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.tf1info.fr/replay-lci/videos/video-24h-pujadas-du-mercredi-2-juillet-2025-73777-2380589.html',
        'info_dict': {
            'id': 'f0550853-c949-4e0e-8ba4-8237cbb512af',
            'ext': 'mp4',
            'title': '24H Pujadas du mercredi 2 juillet 2025',
            'thumbnail': 'https://photos.tf1.fr/1280/720/24h-pujadas-du-mercredi-2-juillet-2025-394752-0@1x.jpg',
            'upload_date': '20250702',
            'duration': 5866,
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        next_data = self._search_nextjs_data(webpage, video_id)
        wat_id = traverse_obj(next_data, (
            'props', 'pageProps', 'page', 'tms', 'videos', {dict.keys}, ..., {str_or_none}, any))
        if wat_id is None:
            raise ExtractorError('Could not find wat_id')

        return self.url_result(f'wat:{wat_id}', WatIE, str(wat_id))
