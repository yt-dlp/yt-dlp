
from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
    js_to_json,
    url_or_none,
)
from ..utils.traversal import traverse_obj
from datetime import datetime


class XiaoYuZhouIE(InfoExtractor):
    _VALID_URL = r'https?://www\.xiaoyuzhoufm\.com/episode/(?P<id>[\da-f]+)'
    IE_DESC = '小宇宙'
    _TESTS = [{
        'url': 'https://www.xiaoyuzhoufm.com/episode/670f2a7e0d2f24f289727fdc',
        'info_dict': {
            'id': '670f2a7e0d2f24f289727fdc',
            'ext': 'm4a',
            'description': str,
            'title': '是不飘了？研究上私募了？没100万也不耽误听',
            'duration': 6741,
            'uploader': '面基',
            'uploader_id': '6388760f22567e8ea6ad070f',
            'uploader_url': 'https://www.xiaoyuzhoufm.com/podcast/6388760f22567e8ea6ad070f',
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        initial_state = self._search_json(
            r'<script id="__NEXT_DATA__" type="application/json">', webpage, 'json_data', display_id)

        episode_info = traverse_obj(initial_state, ('props', 'pageProps', 'episode'))

        episode_title = traverse_obj(episode_info, ('title', {str}))
        audio_url = traverse_obj(episode_info, ('enclosure', 'url', {url_or_none}))
        description = traverse_obj(episode_info, ('description', {str}))
        duration = traverse_obj(episode_info, ('duration', {float_or_none}))
        pubDateStr = traverse_obj(episode_info, ('pubDate', {str}))

        upload_datetime = datetime.strptime(pubDateStr, "%Y-%m-%dT%H:%M:%S.%fZ")  # `2024-10-16T09:30:00.000Z`格式

        # podcast 是指一个播客节目，包含多个 episode，podcast由多个实际user主持
        podcast_id = traverse_obj(episode_info, ('pid', {str}))
        podcast_title = traverse_obj(episode_info, ('podcast', 'title', {str}))
        podcast_description = traverse_obj(episode_info, ('podcast', 'description', {str}))
        podcast_url = f'https://www.xiaoyuzhoufm.com/podcast/{podcast_id}'

        podcast_user_list = traverse_obj(episode_info, ('podcast', 'podcasters', ...))

        ext = None
        if '.' in audio_url.split('/')[-1]:
            ext = audio_url.split('.')[-1]

        formats = []
        formats.append({
            'url': audio_url,
            'vcodec': 'none',
            'ext': ext,
        })

        return {
            'id': display_id,
            'formats': formats,
            'title': episode_title,
            'description': description,
            'duration': duration,
            'timestamp': upload_datetime.timestamp(),
            'uploader': podcast_title,
            'uploader_id': podcast_id,
            'uploader_url': podcast_url,
        }
