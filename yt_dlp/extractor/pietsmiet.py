from .common import InfoExtractor
from ..utils import (
    traverse_obj,
)
import base64


class PietsmietIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?pietsmiet\.de/videos/(?P<id>\d+)-.*'
    _TESTS = [{
        'url': 'https://www.pietsmiet.de/videos/77307-brammen-erzahlt-vom-leben-als-geschaftsfuhrer',
        'md5': '9bca7b377a34bfe4d7a437dd499ff46b',
        'info_dict': {
            'id': '77307',
            'ext': 'mp4',
            'title': 'Brammen erzählt vom Leben als Geschäftsführer',
            'thumbnail': 'https://www.pietsmiet.de/storage/media/71/90/03/7161edccc3e3a9f6f78b6d8b637edc2d.jpg'
        }
    }]

    # Pietsmiet.de uses base64 to hide a value needed to make API call
    def _extract_integrity(self, vid):
        integrity = self._search_json('window._i = ', self._web,
                                      name='Extracting Origin Integrity',
                                      video_id=vid,
                                      fatal=True)

        integrity = base64.b64decode(integrity['v']).decode("ascii")

        return integrity

    def _real_extract(self, url):
        video_id = self._match_id(url)

        self._web = self._download_webpage(url, video_id, note='Caching webpage')

        origin_integrity = self._extract_integrity(video_id)

        data_json = self._download_json(
            f'https://www.pietsmiet.de/api/v1/utility/player?video={video_id}&preset=quality',
            video_id=video_id,
            headers={'x-origin-integrity': origin_integrity})

        title = traverse_obj(data_json, ('options', 'tracks', 0, 'full_title'))
        aspect_ratio = traverse_obj(data_json, ('options', 'visual', 'aspect_ratio'))
        thumbnail = traverse_obj(data_json, ('options', 'visual', 'thumbnail'))
        m3u8_url = traverse_obj(data_json, ('options', 'tracks', 0, 'sources', 'hls', 'src'))

        formats = self._extract_m3u8_formats(m3u8_url, video_id)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'aspect_ratio': aspect_ratio,
            'thumbnail': thumbnail,
        }
