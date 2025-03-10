from yt_dlp.utils import traverse_obj

from .common import InfoExtractor


class TV8StreamingIE(InfoExtractor):
    IE_NAME = 'tv8.it/streaming'
    IE_DESC = 'tv8 live'
    _VALID_URL = r'https?://(?:www\.)?tv8\.it/streaming'
    _TESTS = [{
        'url': 'https://www.tv8.it/streaming',
        'info_dict': {
            'id': 'tv8',
            'ext': 'mp4',
            'title': str,
            'description': str,
            'is_live': True,
            'live_status': 'is_live',
        },
    }]

    def _real_extract(self, url):
        streaming = self._download_json('https://www.tv8.it/api/getStreaming', 'tv8', 'Downloading streaming data')
        livestream = self._download_json('https://apid.sky.it/vdp/v1/getLivestream?id=7', 'tv8')

        return {
            'id': 'tv8',
            'title': traverse_obj(streaming, ('info', 'title', 'text')),
            'description': traverse_obj(streaming, ('info', 'description', 'html')),
            'is_live': True,
            'formats': self._extract_m3u8_formats(livestream['streaming_url'], 'tv8'),
        }
