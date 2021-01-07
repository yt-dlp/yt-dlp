# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    try_get,
    unified_strdate,
)


class AmericasTestKitchenIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?:americastestkitchen|cooks(?:country|illustrated))\.com/(?P<resource_type>episode|videos)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.americastestkitchen.com/episode/582-weeknight-japanese-suppers',
        'md5': 'b861c3e365ac38ad319cfd509c30577f',
        'info_dict': {
            'id': '5b400b9ee338f922cb06450c',
            'title': 'Japanese Suppers',
            'ext': 'mp4',
            'description': 'md5:64e606bfee910627efc4b5f050de92b3',
            'thumbnail': r're:^https?://',
            'timestamp': 1523664000,
            'upload_date': '20180414',
            'release_date': '20180410',
            'series': "America's Test Kitchen",
            'season_number': 18,
            'episode': 'Japanese Suppers',
            'episode_number': 15,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.americastestkitchen.com/videos/3420-pan-seared-salmon',
        'only_matching': True,
    }, {
        'url': 'https://www.cookscountry.com/episode/564-when-only-chocolate-will-do',
        'only_matching': True,
    }, {
        'url': 'https://www.cooksillustrated.com/videos/4478-beef-wellington',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        resource_type, video_id = re.match(self._VALID_URL, url).groups()
        is_episode = resource_type == 'episode'
        if is_episode:
            resource_type = 'episodes'

        resource = self._download_json(
            'https://www.americastestkitchen.com/api/v6/%s/%s' % (resource_type, video_id), video_id)
        video = resource['video'] if is_episode else resource
        episode = resource if is_episode else resource.get('episode') or {}

        return {
            '_type': 'url_transparent',
            'url': 'https://player.zype.com/embed/%s.js?api_key=jZ9GUhRmxcPvX7M3SlfejB6Hle9jyHTdk2jVxG7wOHPLODgncEKVdPYBhuz9iWXQ' % video['zypeId'],
            'ie_key': 'Zype',
            'description': clean_html(video.get('description')),
            'release_date': unified_strdate(video.get('publishDate')),
            'series': try_get(episode, lambda x: x['show']['title']),
            'episode': episode.get('title'),
        }
