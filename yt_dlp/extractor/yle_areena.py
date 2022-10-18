from .common import InfoExtractor
from .kaltura import KalturaIE
from ..utils import traverse_obj


class YleAreenaIE(InfoExtractor):
    _VALID_URL = r'https?://areena\.yle\.fi/(?P<id>[\d-]+)'
    _TESTS = [{
        'url': 'https://areena.yle.fi/1-4371942',
        'md5': '932edda0ecf5dfd6423804182d32f8ac',
        'info_dict': {
            'id': '0_a3tjk92c',
            'ext': 'mp4',
            'title': 'K1, J2: Pouchit | Modernit miehet',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader_id': 'ovp@yle.fi',
            'duration': 1435,
            'view_count': int,
            'upload_date': '20181204',
            'timestamp': 1543916210,
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video_data = self._download_json(
            f'https://player.api.yle.fi/v1/preview/{video_id}.json?app_id=player_static_prod&app_key=8930d72170e48303cf5f3867780d549b',
            video_id)
        kaltura_id = traverse_obj(video_data, ('data', 'ongoing_ondemand', 'kaltura', 'id'))

        webpage = self._download_webpage(url, video_id)
        info = self._search_json_ld(webpage, video_id, default={})

        return {
            '_type': 'url_transparent',
            'url': f'kaltura:1955031:{kaltura_id}',
            'ie_key': KalturaIE.ie_key(),
            'title': info.get('title'),
            'thumbnail': False,
            'thumbnails': traverse_obj(info, ('thumbnails', ..., {'url': 'url'})),
        }
