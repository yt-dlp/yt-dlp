# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class StreamanityIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?streamanity\.com/video/(?P<id>[A-Za-z0-9]+)'
    _TESTS = [{
        'url': 'https://streamanity.com/video/9DFPTnuYi8f2',
        'md5': '6ab171e8d4a02ad5dcbff6bea44cf5a1',
        'info_dict': {
            'id': '9DFPTnuYi8f2',
            'ext': 'mp4',
            'title': 'Bitcoin vs The Lighting Network',
            'thumbnail': r're:https://res\.cloudinary\.com/.+\.png',
            'description': '',
            'uploader': 'Tom Bombadil (Freddy78)',
        }
    }, {
        'url': 'https://streamanity.com/video/JktOUjSlfzTD',
        'md5': '31f131e28abd3377c38be586a59532dc',
        'info_dict': {
            'id': 'JktOUjSlfzTD',
            'ext': 'mp4',
            'title': 'Share data when you see it',
            'thumbnail': r're:https://res\.cloudinary\.com/.+\.png',
            'description': 'Reposting as data should be public and stored on blockchain',
            'uploader': 'digitalcurrencydaily',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_info = self._download_json(
            f'https://app.streamanity.com/api/video/{video_id}', video_id)['data']['video']

        formats = self._extract_m3u8_formats(
            f'https://stream.mux.com/{video_info["play_id"]}.m3u8?token={video_info["token"]}',
            video_id, ext='mp4', m3u8_id='hls')
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': video_info['title'],
            'description': video_info.get('description'),
            'uploader': video_info.get('author_name'),
            'is_live': False,
            'thumbnail': video_info.get('thumb'),
            'formats': formats,
        }
