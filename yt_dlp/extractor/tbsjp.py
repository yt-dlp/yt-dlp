from .common import InfoExtractor
from .streaks import StreaksBaseIE
from ..utils import (
    clean_html,
    int_or_none,
    str_or_none,
    unified_timestamp,
)
from ..utils.traversal import find_element, traverse_obj


class TBSJPEpisodeIE(StreaksBaseIE):
    _VALID_URL = r'https?://cu\.tbs\.co\.jp/episode/(?P<id>[\d_]+)'
    _GEO_BYPASS = False
    _TESTS = [{
        'url': 'https://cu.tbs.co.jp/episode/23613_2044134_1000049010',
        'skip': 'streams geo-restricted, Japan only. Also, will likely expire eventually',
        'info_dict': {
            'title': 'VIVANT 第三話 誤送金完結へ!絶体絶命の反撃開始',
            'id': '23613_2044134_1000049010',
            'ext': 'mp4',
            'upload_date': '20230728',
            'duration': 3517,
            'release_timestamp': 1691118230,
            'episode': '第三話 誤送金完結へ!絶体絶命の反撃開始',
            'release_date': '20230804',
            'categories': 'count:11',
            'episode_number': 3,
            'timestamp': 1690522538,
            'description': 'md5:2b796341af1ef772034133174ba4a895',
            'series': 'VIVANT',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        meta = self._search_json(r'window\.app\s*=', webpage, 'episode info', video_id, fatal=False)
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


class TBSJPProgramIE(InfoExtractor):
    _VALID_URL = r'https?://cu\.tbs\.co\.jp/program/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://cu.tbs.co.jp/program/23601',
        'playlist_mincount': 4,
        'info_dict': {
            'id': '23601',
            'categories': ['エンタメ', 'ミライカプセル', '会社', '働く', 'バラエティ', '動画'],
            'description': '幼少期の夢は大人になって、どう成長したのだろうか？\nそしてその夢は今後、どのように広がっていくのか？\nいま話題の会社で働く人の「夢の成長」を描く',
            'series': 'ミライカプセル　-I have a dream-',
            'title': 'ミライカプセル　-I have a dream-',
        },
    }]

    def _real_extract(self, url):
        programme_id = self._match_id(url)
        webpage = self._download_webpage(url, programme_id)
        meta = self._search_json(r'window\.app\s*=', webpage, 'programme info', programme_id)

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


class TBSJPPlaylistIE(InfoExtractor):
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
        page = self._download_webpage(url, playlist_id)
        meta = self._search_json(r'window\.app\s*=', page, 'playlist info', playlist_id)
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
