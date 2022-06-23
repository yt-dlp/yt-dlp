from .common import InfoExtractor
from ..utils import traverse_obj


class FuyinTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)fuyin\.(?:tv)/(?:html)/(?P<mov_id>\w+)/(?P<url_id>\d+)(?:\.html)'
    _TESTS = [{
        'url': 'https://www.fuyin.tv/html/2733/44129.html',
        'info_dict': {
            'id': '44129',
            'ext': 'mp4',
            'title': '第1集',
        }
    }]

    def _real_extract(self, url):
        playlist_id, video_id = self._match_valid_url(url).group('mov_id', 'url_id')
        json_data = self._download_json(
            'https://www.fuyin.tv/api/api/tv.movie/url',
            video_id, query={'urlid': f'{video_id}'})

        return {
            'id': video_id,
            'title': traverse_obj(json_data, ('data', 'title')),
            'url': json_data['data']['url'],
            'ext': 'mp4',
        }
