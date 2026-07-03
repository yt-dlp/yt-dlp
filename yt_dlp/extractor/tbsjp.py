from .streaks import StreaksBaseIE
from ..utils import (
    clean_html,
    int_or_none,
    str_or_none,
    unified_timestamp,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class TBSJPBaseIE(StreaksBaseIE):
    def _search_window_app_json(self, webpage, name, item_id, **kwargs):
        return self._search_json(r'window\.app\s*=', webpage, f'{name} info', item_id, **kwargs)


class TBSJPEpisodeIE(TBSJPBaseIE):
    _VALID_URL = r'https?://cu\.tbs\.co\.jp/episode/(?P<id>[\d_]+)'
    _TESTS = [{
        'url': 'https://cu.tbs.co.jp/episode/14694_2094162_1000123656',
        'skip': 'geo-blocked to japan + 7-day expiry',
        'info_dict': {
            'title': 'クロちゃん、寝て起きたら川のほとりにいてその向こう岸に亡くなった父親がいたら死の淵にいるかと思う説 ほか',
            'id': '14694_2094162_1000123656',
            'ext': 'mp4',
            'display_id': 'ref:14694_2094162_1000123656',
            'description': 'md5:1a82fcdeb5e2e82190544bb72721c46e',
            'uploader': 'TBS',
            'uploader_id': 'tbs',
            'duration': 2752,
            'thumbnail': 'md5:d8855c8c292683c95a84cafdb42300bc',
            'categories': ['エンタメ', '水曜日のダウンタウン', 'ダウンタウン', '浜田雅功', '松本人志', '水ダウ', '動画', 'バラエティ'],
            'cast': ['浜田 雅功', '藤本 敏史', 'ビビる 大木', '千原 ジュニア', '横澤 夏子', 'せいや', 'あの', '服部 潤'],
            'genres': ['variety'],
            'series': '水曜日のダウンタウン',
            'series_id': '14694',
            'episode': 'クロちゃん、寝て起きたら川のほとりにいてその向こう岸に亡くなった父親がいたら死の淵にいるかと思う説 ほか',
            'episode_number': 341,
            'episode_id': '14694_2094162_1000123656',
            'timestamp': 1753778992,
            'upload_date': '20250729',
            'release_timestamp': 1753880402,
            'release_date': '20250730',
            'modified_timestamp': 1753880741,
            'modified_date': '20250730',
            'live_status': 'not_live',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        meta = self._search_window_app_json(webpage, 'episode', video_id, fatal=False)
        episode = traverse_obj(meta, ('falcorCache', 'catalog', 'episode', video_id, 'value'))

        return {
            **self._extract_from_streaks_api(
                'tbs', f'ref:{video_id}', headers={'Origin': 'https://cu.tbs.co.jp'}),
            **traverse_obj(episode, {
                'title': ('title', ..., 'value', {str}, any),
                'cast': (
                    'credit', ..., 'name', ..., 'value', {clean_html}, any,
                    {lambda x: x.split(',')}, ..., {str.strip}, filter, all, filter),
                'categories': ('keywords', ..., {str}, filter, all, filter),
                'description': ('description', ..., 'value', {clean_html}, any),
                'duration': ('tv_episode_info', 'duration', {int_or_none}),
                'episode': ('title', lambda _, v: not v.get('is_phonetic'), 'value', {str}, any),
                'episode_id': ('content_id', {str}),
                'episode_number': ('tv_episode_info', 'episode_number', {int_or_none}),
                'genres': ('genre', ..., {str}, filter, all, filter),
                'release_timestamp': ('pub_date', {unified_timestamp}),
                'series': ('custom_data', 'program_name', {str}),
                'tags': ('tags', ..., {str}, filter, all, filter),
                'thumbnail': ('artwork', ..., 'url', {url_or_none}, any),
                'timestamp': ('created_at', {unified_timestamp}),
                'uploader': ('tv_show_info', 'networks', ..., {str}, any),
            }),
            **traverse_obj(episode, ('tv_episode_info', {
                'duration': ('duration', {int_or_none}),
                'episode_number': ('episode_number', {int_or_none}),
                'series_id': ('show_content_id', {str}),
            })),
            'id': video_id,
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
            'categories': ['エンタメ', '水曜日のダウンタウン', 'ダウンタウン', '浜田雅功', '松本人志', '水ダウ', '動画', 'バラエティ'],
            'series': '水曜日のダウンタウン',
        },
    }]

    def _real_extract(self, url):
        programme_id = self._match_id(url)
        webpage = self._download_webpage(url, programme_id)
        meta = self._search_window_app_json(webpage, 'programme', programme_id)
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
        meta = self._search_window_app_json(webpage, 'playlist', playlist_id)
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
