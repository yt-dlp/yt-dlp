from .common import InfoExtractor
from ..utils import int_or_none, urljoin


class SkylineWebcamsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?skylinewebcams\.com/[^/]+/webcam/(?:[^/]+/)+(?P<id>[^/]+)\.html'
    _TEST = {
        'url': 'https://www.skylinewebcams.com/en/webcam/espana/comunidad-valenciana/alicante/benidorm-playa-levante.html',
        'info_dict': {
            'id': 'benidorm-playa-levante',
            'ext': 'mp4',
            'title': 're:^【LIVE】 Webcam Benidorm - Levante Beach | SkylineWebcams [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'description': 'View over the beach of the summer destination in Costa Blanca.',
            'live_status': 'is_live',
            'view_count': int,
            'timestamp': int,
            'thumbnail': 'https://cdn.skylinewebcams.com/social642.jpg',
            'upload_date': '20240226'
        },
        'params': {
            'skip_download': True,
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        stream_url = urljoin('https://hd-auth.skylinewebcams.com', self._search_regex(
            r'(?:url|source)\s*:\s*(["\'])(?P<url>.+?\.m3u8.*?)\1', webpage,
            'stream url', group='url'))
        video_data = self._search_json_ld(webpage, video_id)

        return {
            'id': video_id,
            'url': stream_url,
            'ext': 'mp4',
            'title': video_data.get('title') or self._og_search_title(webpage),
            'description': video_data.get('description') or self._og_search_description(webpage),
            'thumbnails': video_data.get('thumbnails'),
            'timestamp': int_or_none(video_data.get('timestamp')),
            'view_count': int_or_none(video_data.get('view_count')),
            'is_live': True,
        }
