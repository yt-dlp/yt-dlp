# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class StreamanityIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?streamanity\.com/video/(?P<id>[A-Za-z0-9]+)'
    _TEST = {
        'url': 'https://streamanity.com/video/9DFPTnuYi8f2',
        'info_dict': {
            'id': '9DFPTnuYi8f2',
            'ext': 'mp4',
            'title': 'Bitcoin vs The Lighting Network',
            'thumbnail': 'https://res.cloudinary.com/streamanity-next/image/upload/v1631475198/thumb/523908e0-e85b-4555-9050-78a8378835f1.png',
            'description': '',
            'uploader': 'Tom Bombadil (Freddy78)',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_info = self._download_json(
            f'https://app.streamanity.com/api/video/{video_id}', video_id)['data']['video']

        formats = self._extract_m3u8_formats(
            f'https://stream.mux.com/{video_id}.m3u8?token={video_info["token"]}',
            video_id, ext='mp4', m3u8_id='hls')
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': video_info['title'],
            'description': video_info.get('description'),
            'uploader': video_info.get('author_name'),
            'is_live': False,
            'thumbnail': video_info.get('thumbnail'),
            'formats': formats,
        }
