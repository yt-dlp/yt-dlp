from .brightcove import BrightcoveNewIE
from .common import InfoExtractor
from ..utils import url_or_none
from ..utils.traversal import traverse_obj


class DrTalksIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?drtalks\.com/videos/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://drtalks.com/videos/six-pillars-of-resilience-tools-for-managing-stress-and-flourishing/',
        'info_dict': {
            'id': '6366193757112',
            'ext': 'mp4',
            'uploader_id': '6314452011001',
            'tags': ['resilience'],
            'description': 'md5:9c6805aee237ee6de8052461855b9dda',
            'timestamp': 1734546659,
            'thumbnail': 'https://drtalks.com/wp-content/uploads/2024/12/Episode-82-Eva-Selhub-DrTalks-Thumbs.jpg',
            'title': 'Six Pillars of Resilience: Tools for Managing Stress and Flourishing',
            'duration': 2800.682,
            'upload_date': '20241218',
        },
    }, {
        'url': 'https://drtalks.com/videos/the-pcos-puzzle-mastering-metabolic-health-with-marcelle-pick/',
        'info_dict': {
            'id': '6364699891112',
            'ext': 'mp4',
            'title': 'The PCOS Puzzle: Mastering Metabolic Health with Marcelle Pick',
            'description': 'md5:e87cbe00ca50135d5702787fc4043aaa',
            'thumbnail': 'https://drtalks.com/wp-content/uploads/2024/11/Episode-34-Marcelle-Pick-OBGYN-NP-DrTalks.jpg',
            'duration': 3515.2,
            'tags': ['pcos'],
            'upload_date': '20241114',
            'timestamp': 1731592119,
            'uploader_id': '6314452011001',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        next_data = self._search_nextjs_data(webpage, video_id)['props']['pageProps']['data']['video']

        return self.url_result(
            next_data['videos']['brightcoveVideoLink'], BrightcoveNewIE, video_id,
            url_transparent=True,
            **traverse_obj(next_data, {
                'title': ('title', {str}),
                'description': ('videos', 'summury', {str}),
                'thumbnail': ('featuredImage', 'node', 'sourceUrl', {url_or_none}),
            }))
