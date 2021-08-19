from __future__ import unicode_literals

import re
import json

from .common import InfoExtractor
from .youtube import YoutubeIE
from ..compat import compat_b64decode
from ..utils import (
    clean_html,
    ExtractorError
)


class ChilloutzoneIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?chilloutzone\.net/video/(?P<id>[\w|-]+)\.html'
    _TESTS = [{
        'url': 'http://www.chilloutzone.net/video/enemene-meck-alle-katzen-weg.html',
        'md5': 'a76f3457e813ea0037e5244f509e66d1',
        'info_dict': {
            'id': 'enemene-meck-alle-katzen-weg',
            'ext': 'mp4',
            'title': 'Enemene Meck - Alle Katzen weg',
            'description': 'Ist das der Umkehrschluss des Niesenden Panda-Babys?',
        },
    }, {
        'note': 'Video hosted at YouTube',
        'url': 'http://www.chilloutzone.net/video/eine-sekunde-bevor.html',
        'info_dict': {
            'id': '1YVQaAgHyRU',
            'ext': 'mp4',
            'title': '16 Photos Taken 1 Second Before Disaster',
            'description': 'md5:58a8fcf6a459fe0a08f54140f0ad1814',
            'uploader': 'BuzzFeedVideo',
            'uploader_id': 'BuzzFeedVideo',
            'upload_date': '20131105',
        },
    }, {
        'note': 'Video hosted at Vimeo',
        'url': 'http://www.chilloutzone.net/video/icon-blending.html',
        'md5': '2645c678b8dc4fefcc0e1b60db18dac1',
        'info_dict': {
            'id': '85523671',
            'ext': 'mp4',
            'title': 'The Sunday Times - Icons',
            'description': 're:(?s)^Watch the making of - makingoficons.com.{300,}',
            'uploader': 'Us',
            'uploader_id': 'usfilms',
            'upload_date': '20140131'
        },
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id')

        webpage = self._download_webpage(url, video_id)

        base64_video_info = self._html_search_regex(
            r'var cozVidData = "(.+?)";', webpage, 'video data')
        decoded_video_info = compat_b64decode(base64_video_info).decode('utf-8')
        video_info_dict = json.loads(decoded_video_info)

        # get video information from dict
        video_url = video_info_dict['mediaUrl']
        description = clean_html(video_info_dict.get('description'))
        title = video_info_dict['title']
        native_platform = video_info_dict['nativePlatform']
        native_video_id = video_info_dict['nativeVideoId']
        source_priority = video_info_dict['sourcePriority']

        # If nativePlatform is None a fallback mechanism is used (i.e. youtube embed)
        if native_platform is None:
            youtube_url = YoutubeIE._extract_url(webpage)
            if youtube_url:
                return self.url_result(youtube_url, ie=YoutubeIE.ie_key())

        # Non Fallback: Decide to use native source (e.g. youtube or vimeo) or
        # the own CDN
        if source_priority == 'native':
            if native_platform == 'youtube':
                return self.url_result(native_video_id, ie='Youtube')
            if native_platform == 'vimeo':
                return self.url_result(
                    'http://vimeo.com/' + native_video_id, ie='Vimeo')

        if not video_url:
            raise ExtractorError('No video found')

        return {
            'id': video_id,
            'url': video_url,
            'ext': 'mp4',
            'title': title,
            'description': description,
        }
