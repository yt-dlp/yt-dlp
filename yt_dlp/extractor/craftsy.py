from .brightcove import BrightcoveNewIE
from .common import InfoExtractor

from ..utils import (
    dict_get,
    get_element_by_id,
    js_to_json,
    traverse_obj,
)


class CraftsyIE(InfoExtractor):
    _VALID_URL = r'https?://www\.craftsy\.com/class/(?P<id>[\w-]+)'
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
            'description': 'md5:8270d0ef5427d3c895a27351aeaac276',
        },
        'playlist_mincount': 1,
    }, {
        'url': 'https://www.craftsy.com/class/all-access-estes-park-wool-market/',
        'info_dict': {
            'id': 'all-access-estes-park-wool-market',
            'title': 'All Access: Estes Park Wool Market',
            'description': 'md5:aded1bd8d38ae2fae4dae936c0ae01e7',
        },
        'playlist_count': 6,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        video_data = self._parse_json(self._search_regex(
            r'class_video_player_vars\s*=\s*({.*})\s*;',
            get_element_by_id('vidstore-classes_class-video-player-js-extra', webpage),
            'video data'), video_id, transform_source=js_to_json)

        account_id = traverse_obj(video_data, ('video_player', 'bc_account_id'))

        entries = []
        class_preview = traverse_obj(video_data, ('video_player', 'class_preview'))
        if class_preview:
            v_id = class_preview.get('video_id')
            entries.append(self.url_result(
                f'http://players.brightcove.net/{account_id}/default_default/index.html?videoId={v_id}',
                BrightcoveNewIE, v_id, class_preview.get('title')))

        if dict_get(video_data, ('is_free', 'user_has_access')):
            entries += [
                self.url_result(
                    f'http://players.brightcove.net/{account_id}/default_default/index.html?videoId={lesson["video_id"]}',
                    BrightcoveNewIE, lesson['video_id'], lesson.get('title'))
                for lesson in video_data['lessons']]

        return self.playlist_result(
            entries, video_id, video_data.get('class_title'),
            self._html_search_meta(('og:description', 'description'), webpage, default=None))
