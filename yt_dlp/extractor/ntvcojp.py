from .streaks import StreaksBaseIE
from ..utils import (
    int_or_none,
    parse_iso8601,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import require, traverse_obj


class NTVCoJpCUIE(StreaksBaseIE):
    IE_NAME = 'cu.ntv.co.jp'
    IE_DESC = '日テレ無料TADA!'
    _VALID_URL = r'https?://cu\.ntv\.co\.jp/(?!program-list|search)(?P<id>[\w-]+)/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://cu.ntv.co.jp/gaki_20250525/',
        'info_dict': {
            'id': 'gaki_20250525',
            'ext': 'mp4',
            'title': '放送開始36年!方正ココリコが選ぶ神回&地獄回!',
            'cast': 'count:2',
            'description': 'md5:1e1db556224d627d4d2f74370c650927',
            'display_id': 'ref:gaki_20250525',
            'duration': 1450,
            'episode': '放送開始36年!方正ココリコが選ぶ神回&地獄回!',
            'episode_id': '000000010172808',
            'episode_number': 255,
            'genres': ['variety'],
            'live_status': 'not_live',
            'modified_date': '20250525',
            'modified_timestamp': 1748145537,
            'release_date': '20250525',
            'release_timestamp': 1748145539,
            'series': 'ダウンタウンのガキの使いやあらへんで！',
            'series_id': 'gaki',
            'thumbnail': r're:https?://.+\.jpg',
            'timestamp': 1748145197,
            'upload_date': '20250525',
            'uploader': '日本テレビ放送網',
            'uploader_id': '0x7FE2',
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        info = self._search_json(
            r'window\.app\s*=', webpage, 'video info',
            display_id)['falcorCache']['catalog']['episode'][display_id]['value']
        media_id = traverse_obj(info, (
            'streaks_data', 'mediaid', {str_or_none}, {require('Streaks media ID')}))
        non_phonetic = (lambda _, v: v['is_phonetic'] is False, 'value', {str})

        return {
            **self._extract_from_streaks_api('ntv-tada', media_id, headers={
                'X-Streaks-Api-Key': 'df497719056b44059a0483b8faad1f4a',
            }),
            **traverse_obj(info, {
                'id': ('content_id', {str_or_none}),
                'title': ('title', *non_phonetic, any),
                'age_limit': ('is_adult_only_content', {lambda x: 18 if x else None}),
                'cast': ('credit', ..., 'name', *non_phonetic),
                'genres': ('genre', ..., {str}),
                'release_timestamp': ('pub_date', {parse_iso8601}),
                'tags': ('tags', ..., {str}),
                'thumbnail': ('artwork', ..., 'url', any, {url_or_none}),
            }),
            **traverse_obj(info, ('tv_episode_info', {
                'duration': ('duration', {int_or_none}),
                'episode_number': ('episode_number', {int}),
                'series': ('parent_show_title', *non_phonetic, any),
                'series_id': ('show_content_id', {str}),
            })),
            **traverse_obj(info, ('custom_data', {
                'description': ('program_detail', {str}),
                'episode': ('episode_title', {str}),
                'episode_id': ('episode_id', {str_or_none}),
                'uploader': ('network_name', {str}),
                'uploader_id': ('network_id', {str}),
            })),
        }
