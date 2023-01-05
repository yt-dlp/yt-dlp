from .common import InfoExtractor
from ..utils import traverse_obj


class SYVDKIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?24syv\.dk/episode/(?P<id>[\w-]+)'

    _TESTS = [{
        'url': 'https://24syv.dk/episode/isabella-arendt-stiller-op-for-de-konservative-2',
        'md5': '429ce5a423dd4b1e1d0bf3a569558089',
        'info_dict': {
            'id': '12215',
            'display_id': 'isabella-arendt-stiller-op-for-de-konservative-2',
            'ext': 'mp3',
            'title': 'Isabella Arendt stiller op for De Konservative',
            'description': 'md5:f5fa6a431813bf37284f3412ad7c6c06'
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        info_data = self._search_nextjs_data(webpage, video_id)['props']['pageProps']['episodeDetails'][0]

        return {
            'id': str(info_data['id']),
            'vcodec': 'none',
            'ext': 'mp3',
            'url': info_data['details']['enclosure'],
            'display_id': video_id,
            'title': traverse_obj(info_data, ('title', 'rendered')),
            'description': traverse_obj(info_data, ('details', 'post_title')),
        }
