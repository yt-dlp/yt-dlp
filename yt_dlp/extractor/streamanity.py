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
#       Download JSON that contains video information
        video_info = self._download_json('https://app.streamanity.com/api/video/{}'.format(video_id), video_id)

#       All relevant & useful information
        uploader = video_info['data']['video']['author_name']
        description = video_info['data']['video']['description']
        play_id = video_info['data']['video']['play_id']
        title = video_info['data']['video']['title']
        token = video_info['data']['video']['token']
        thumbnail = video_info['data']['video']['thumb']

        actual_master_playlist_url = 'https://stream.mux.com/{}.m3u8?token={}'.format(play_id, token)

        formats = self._extract_m3u8_formats(
            actual_master_playlist_url, video_id, ext='mp4',
            m3u8_id='hls', live=False)
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'uploader': uploader,
            'is_live': False,
            'thumbnail': thumbnail,
            'formats': formats,
        }
