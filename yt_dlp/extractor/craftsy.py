# coding: utf-8
from __future__ import unicode_literals

import json

from .common import InfoExtractor
from ..utils import (
    get_element_by_id,
    js_to_json,
    traverse_obj,
)


class CraftsyIE(InfoExtractor):
    _VALID_URL = r'https?://www.craftsy.com/class/(?P<id>[a-z0-9_-]+)/'
    _TESTS = [{
        'url': 'https://www.craftsy.com/class/the-midnight-quilt-show-season-5/',
        'info_dict': {
            'id': 'the-midnight-quilt-show-season-5',
            'title': 'The Midnight Quilt Show Season 5',
            'description': 'md5:113eda818e985d1a566625fb2f833b7a',
        },
        'playlist_count': 10,
    }, {
        'url': 'https://www.craftsy.com/class/sew-your-own-designer-handbag/',
        'info_dict': {
            'id': 'sew-your-own-designer-handbag',
            'title': 'Sew Your Own Designer Handbag',
            'description': 'md5::8270d0ef5427d3c895a27351aeaac276',
        },
        'playlist_mincount': 1,
    }]

    def _real_extract(self, url):
        video_name = self._match_id(url)
        webpage = self._download_webpage(url, video_name)

        extra_data = get_element_by_id('vidstore-classes_class-video-player-js-extra', webpage)
        video_data = json.loads(js_to_json(self._search_regex(
            r'class_video_player_vars\s*=\s*({.*})\s*;',
            extra_data, 'video data')))

        account_id = traverse_obj(video_data, ('video_player', 'bc_account_id'))
        class_title = video_data.get('class_title')
        description = self._html_search_meta(['og:description', 'description'], webpage, default=None)

        class_preview = traverse_obj(video_data, ('video_player', 'class_preview'))
        entries = []
        if class_preview:
            video_id = class_preview.get('video_id')
            title = class_preview.get('title')
            url = f'http://players.brightcove.net/{account_id}/default_default/index.html?videoId={video_id}'
            entries.append(self.url_result(url, 'BrightcoveNew', video_id, title))
        else:
            lessons = video_data.get('lessons')
            for lesson in lessons:
                video_id = lesson.get('video_id')
                title = lesson.get('title')
#               url = 'https://edge.api.brightcove.com/playback/v1/accounts/%s/videos/%s' % (account_id,video_id)
                url = f'http://players.brightcove.net/{account_id}/default_default/index.html?videoId={video_id}'
                entries.append(self.url_result(url, 'BrightcoveNew', video_id, title))

        return self.playlist_result(entries, video_name, class_title, description)
