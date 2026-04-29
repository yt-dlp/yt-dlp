from .common import InfoExtractor
from ..utils import traverse_obj


class FuyinTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?fuyin\.tv/html/(?:\d+)/(?P<id>\d+)\.html'
    _TESTS = [{
        'url': 'https://www.fuyin.tv/html/2733/44129.html',
        'info_dict': {
            'id': '44129',
            'ext': 'mp4',
            'title': '第1集',
            'description': 'md5:21a3d238dc8d49608e1308e85044b9c3',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        json_data = self._download_json(
            'https://www.fuyin.tv/api/api/tv.movie/url',
            video_id, query={'urlid': f'{video_id}'})
        webpage = self._download_webpage(url, video_id, fatal=False)

        return {
            'id': video_id,
            'title': traverse_obj(json_data, ('data', 'title')),
            'url': json_data['data']['url'],
            'ext': 'mp4',
            'description': self._html_search_meta('description', webpage),
        }
