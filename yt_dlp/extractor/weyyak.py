import re

from .common import InfoExtractor
from ..utils import traverse_obj, float_or_none


class WeyyakIE(InfoExtractor):
    _VALID_URL = r'https?://weyyak\.com/(?P<lang>\w+)/(?:player/)?(?P<type>episode|movie)/(?P<id>\d+)'
    _TESTS = [
        {
            'url': 'https://weyyak.com/en/player/episode/1341952/Ribat-Al-Hob-Episode49',
            'md5': '0caf55c1a615531c8fe60f146ae46849',
            'info_dict': {
                'id': '1341952',
                'ext': 'mp4',
                'title': 'Ribat Al Hob',
                'duration': 2771,
            },
        },
        {
            'url': 'https://weyyak.com/en/movie/233255/8-Seconds',
            'md5': 'fe740ae0f63e4d1c8a7fc147a410c564',
            'info_dict': {
                'id': '233255',
                'ext': 'mp4',
                'title': '8 Seconds',
                'duration': 6490,
            },
        },
    ]

    def _real_extract(self, url):
        _id, _lang, _type = self._match_valid_url(url).group('id', 'lang', 'type')

        path = 'episode/' if _type == 'episode' else 'contents/moviedetails?contentkey='
        video_info = self._download_json(
            f'https://msapifo-prod-me.weyyak.z5.com/v1/{_lang}/{path}{_id}', _id)
        video_details = self._download_json(
            f'https://api-weyyak.akamaized.net/get_info/{video_info["data"]["video_id"]}',
            _id, 'Extracting video details')
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(video_details['url_video'], _id)

        return {
            'id': _id,
            'title': traverse_obj(video_info, ('data', 'title')),
            'duration': float_or_none(video_details.get('duration')),
            'formats': formats,
            'subtitles': subtitles,
        }
