import re

from .common import InfoExtractor
from ..utils import traverse_obj


class WeyyakIE(InfoExtractor):
    _VALID_URL = r'https?://weyyak\.com/(?P<lang>\w+)/player/(?P<type>episode|movie)/(?P<id>\d+)(?:/.+)?'
    _TESTS = [
        {
            'url': 'https://weyyak.com/en/player/episode/1341952/Ribat-Al-Hob-Episode49',
            'md5': '0caf55c1a615531c8fe60f146ae46849',
            'info_dict': {
                'id': '1341952',
                'ext': 'm3u8',
                'title': 'Ribat Al Hob',
                'duration': 2771,
            },
        }
    ]

    def _real_extract(self, url):
        _id, _lang, _type = self._match_valid_url(url).group('id', 'lang', 'type')

        path = 'episode/' if _type == 'episode' else 'contents/moviedetails?contentkey='
        video_info = self._download_json(
            f'https://msapifo-prod-me.weyyak.z5.com/v1/{_lang}/{path}{_id}', _id,
            headers={'Content-Type': 'application/json'})
        video_id = video_info['data']['video_id']
        title = traverse_obj(video_info, ('data', 'title'))

        video_details = self._download_json(
            f'https://api-weyyak.akamaized.net/get_info/{video_id}', _id,
            'Extracting video details', headers={'Content-Type': 'application/json'})
        video_url = video_details.get('url_video')
        video_url = re.sub(r'index\.m3u8', 'master-v1a1.m3u8', video_url)
        video_duration = video_details.get('duration')

        return {
            'id': _id,
            'title': title,
            'url': video_url,
            'duration': video_duration,
        }
