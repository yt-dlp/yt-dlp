import json

from .brightcove import BrightcoveNewIE
from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    get_element_html_by_class,
    get_element_text_and_html_by_tag,
)
from ..utils.traversal import traverse_obj


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

        video_player = get_element_html_by_class('class-video-player', webpage)
        video_data = traverse_obj(video_player, (
            {extract_attributes}, 'wire:snapshot', {json.loads}, 'data', {dict})) or {}
        video_js = traverse_obj(video_player, (
            {lambda x: get_element_text_and_html_by_tag('video-js', x)}, 1, {extract_attributes})) or {}

        has_access = video_data.get('userHasAccess')
        lessons = traverse_obj(video_data, ('lessons', ..., ..., lambda _, v: v['video_id']))

        preview_id = video_js.get('data-video-id')
        if preview_id and preview_id not in traverse_obj(lessons, (..., 'video_id')):
            if not lessons and not has_access:
                self.report_warning(
                    'Only extracting preview. For the full class, pass cookies '
                    f'from an account that has access. {self._login_hint()}')
            lessons.append({'video_id': preview_id})

        if not lessons and not has_access:
            self.raise_login_required('You do not have access to this class')

        account_id = video_data.get('accountId') or video_js['data-account']

        def entries(lessons):
            for lesson in lessons:
                yield self.url_result(
                    f'http://players.brightcove.net/{account_id}/default_default/index.html?videoId={lesson["video_id"]}',
                    BrightcoveNewIE, lesson['video_id'], lesson.get('title'))

        return self.playlist_result(
            entries(lessons), video_id, self._html_search_meta(('og:title', 'twitter:title'), webpage),
            self._html_search_meta(('og:description', 'description'), webpage, default=None))
