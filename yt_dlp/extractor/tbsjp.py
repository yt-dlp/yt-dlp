from .streaks import StreaksBaseIE
from ..utils import (
    clean_html,
    int_or_none,
    str_or_none,
    unified_timestamp,
)
from ..utils.traversal import find_element, traverse_obj


class TBSJPBaseIE(StreaksBaseIE):
    def _window_app(self, webpage, name, item_id, fatal=True):
        return self._search_json(r'window\.app\s*=', webpage, f'{name} info', item_id, fatal=fatal)


class TBSJPEpisodeIE(TBSJPBaseIE):
    _VALID_URL = r'https?://cu\.tbs\.co\.jp/episode/(?P<id>[\d_]+)'
    _GEO_BYPASS = False
    _TESTS = [{
        'url': 'https://cu.tbs.co.jp/episode/14694_2090934_1000117476',
        'skip': 'geo-blocked to japan + 7-day expiry',
        'info_dict': {
            'title': '次世代リアクション王発掘トーナメント',
            'id': '14694_2090934_1000117476',
            'ext': 'mp4',
            'display_id': 'ref:14694_2090934_1000117476',
            'description': 'md5:63a2f445387f9d8c50f4e76396df968f',
            'uploader_id': 'tbs',
            'duration': 2761,
            'thumbnail': 'md5:5e044cd3431b1301de1a25911a6a9a4e',
            'categories': ['エンタメ', '水曜日のダウンタウン', 'ダウンタウン', '浜田雅功', '松本人志', '水ダウ', 'バラエティ', '動画'],
            'series': '水曜日のダウンタウン',
            'episode': '次世代リアクション王発掘トーナメント',
            'episode_number': 335,
            'timestamp': 1749547434,
            'upload_date': '20250610',
            'release_timestamp': 1749646802,
            'release_date': '20250611',
            'modified_timestamp': 1749647146,
            'modified_date': '20250611',
            'live_status': 'not_live',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        meta = self._window_app(webpage, 'episode', video_id)
        episode = traverse_obj(meta, ('falcorCache', 'catalog', 'episode', video_id, 'value'))

        return {
            **self._extract_from_streaks_api('tbs', f'ref:{video_id}', headers={'Referer': 'https://cu.tbs.co.jp/'}),
            'title': traverse_obj(webpage, ({find_element(tag='h3')}, {clean_html})),
            'id': video_id,
            **traverse_obj(episode, {
                'categories': ('keywords', {list}),
                'id': ('content_id', {str}),
                'description': ('description', 0, 'value'),
                'timestamp': ('created_at', {unified_timestamp}),
                'release_timestamp': ('pub_date', {unified_timestamp}),
                'duration': ('tv_episode_info', 'duration', {int_or_none}),
                'episode_number': ('tv_episode_info', 'episode_number', {int_or_none}),
                'episode': ('title', lambda _, v: not v.get('is_phonetic'), 'value'),
                'series': ('custom_data', 'program_name'),
            }, get_all=False),
        }


class TBSJPProgramIE(TBSJPBaseIE):
    _VALID_URL = r'https?://cu\.tbs\.co\.jp/program/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://cu.tbs.co.jp/program/14694',
        'playlist_mincount': 1,
        'info_dict': {
            'id': '14694',
            'title': '水曜日のダウンタウン',
            'description': 'md5:cf1d46c76c2755d7f87512498718b837',
            'categories': ['エンタメ', '水曜日のダウンタウン', 'ダウンタウン', '浜田雅功', '松本人志', '水ダウ', 'バラエティ', '動画'],
            'series': '水曜日のダウンタウン',
        },
    }]

    def _real_extract(self, url):
        programme_id = self._match_id(url)
        webpage = self._download_webpage(url, programme_id)
        meta = self._window_app(webpage, 'programme', programme_id)
        programme = traverse_obj(meta, ('falcorCache', 'catalog', 'program', programme_id, 'false', 'value'))

        return {
            '_type': 'playlist',
            'entries': [self.url_result(f'https://cu.tbs.co.jp/episode/{video_id}', TBSJPEpisodeIE, video_id)
                        for video_id in traverse_obj(programme, ('custom_data', 'seriesList', 'episodeCode', ...))],
            'id': programme_id,
            **traverse_obj(programme, {
                'categories': ('keywords', ...),
                'id': ('tv_episode_info', 'show_content_id', {str_or_none}),
                'description': ('custom_data', 'program_description'),
                'series': ('custom_data', 'program_name'),
                'title': ('custom_data', 'program_name'),
            }),
        }


class TBSJPPlaylistIE(TBSJPBaseIE):
    _VALID_URL = r'https?://cu\.tbs\.co\.jp/playlist/(?P<id>[\da-f]+)'
    _TESTS = [{
        'url': 'https://cu.tbs.co.jp/playlist/184f9970e7ba48e4915f1b252c55015e',
        'playlist_mincount': 4,
        'info_dict': {
            'title': 'まもなく配信終了',
            'id': '184f9970e7ba48e4915f1b252c55015e',
        },
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)
        meta = self._window_app(webpage, 'playlist', playlist_id)
        playlist = traverse_obj(meta, ('falcorCache', 'playList', playlist_id))

        def entries():
            for entry in traverse_obj(playlist, ('catalogs', 'value', lambda _, v: v['content_id'])):
                # TODO: it's likely possible to get all metadata from the playlist page json instead
                content_id = entry['content_id']
                content_type = entry.get('content_type')
                if content_type == 'tv_show':
                    yield self.url_result(
                        f'https://cu.tbs.co.jp/program/{content_id}', TBSJPProgramIE, content_id)
                elif content_type == 'tv_episode':
                    yield self.url_result(
                        f'https://cu.tbs.co.jp/episode/{content_id}', TBSJPEpisodeIE, content_id)
                else:
                    self.report_warning(f'Skipping "{content_id}" with unsupported content_type "{content_type}"')

        return self.playlist_result(entries(), playlist_id, traverse_obj(playlist, ('display_name', 'value')))
