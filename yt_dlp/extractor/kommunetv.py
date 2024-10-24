from .common import InfoExtractor
from ..utils import update_url


class KommunetvIE(InfoExtractor):
    _VALID_URL = r'https?://\w+\.kommunetv\.no/archive/(?P<id>\w+)'
    _TEST = {
        'url': 'https://oslo.kommunetv.no/archive/921',
        'md5': '5f102be308ee759be1e12b63d5da4bbc',
        'info_dict': {
            'id': '921',
            'title': 'Bystyremøte',
            'ext': 'mp4',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        headers = {
            'Accept': 'application/json',
        }
        data = self._download_json(f'https://oslo.kommunetv.no/api/streams?streamType=1&id={video_id}', video_id, headers=headers)
        title = data['stream']['title']
        file = data['playlist'][0]['playlist'][0]['file']
        url = update_url(file, query=None, fragment=None)
        formats = self._extract_m3u8_formats(url, video_id, ext='mp4', entry_protocol='m3u8_native', m3u8_id='hls', fatal=False)
        return {
            'id': video_id,
            'formats': formats,
            'title': title,
        }
