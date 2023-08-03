from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    get_element_text_and_html_by_tag,
    traverse_obj,
    unified_timestamp,
    urljoin,
)


class TBSJPEpisodeIE(InfoExtractor):
    _VALID_URL = r'https://cu\.tbs\.co\.jp/episode/(?P<id>[\d_]+)'
    _TESTS = [{
        'url': 'https://cu.tbs.co.jp/episode/23613_2044134_1000049010',
        'skip': 'streams geo-restricted, Japan only. Also, will likely expire eventually',
        'info_dict': {
            'title': 'VIVANT 第三話 誤送金完結へ！絶体絶命の反撃開始',
            'id': '23613_2044134_1000049010',
            'ext': 'mp4',
            'upload_date': '20230728',
            'duration': 3517,
            'release_timestamp': 1690869448,
            'episode': '第三話 誤送金完結へ！絶体絶命の反撃開始',
            'release_date': '20230801',
            'categories': 'count:11',
            'episode_number': 3,
            'timestamp': 1690522538,
            'description': 'md5:2b796341af1ef772034133174ba4a895',
            'series': 'VIVANT',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        page = self._download_webpage(url, video_id)
        meta = self._search_json('window.app=', page, 'episode info', video_id)

        episode = traverse_obj(meta, ('falcorCache', 'catalog', 'episode', video_id, 'value'))

        episode_meta = traverse_obj(episode, {
            'categories': 'keywords',
            'id': 'content_id',
            'description': ('description', 0, 'value'),
            'timestamp': ('created_at', {unified_timestamp}),
            'release_timestamp': ('pub_date', {unified_timestamp}),
            'duration': ('tv_episode_info', 'duration'),
            'episode_number': ('tv_episode_info', 'episode_number'),
            'series': ('custom_data', 'program_name'),
        })

        tf_url = urljoin(
            url,
            self._search_regex(r'<script src=["\'](/assets/tf\.[^"\']+\.js)["\']', page, 'stream API config')
        )
        tf_js = self._download_webpage(tf_url, video_id, note='Downloading stream API config')
        video_url = self._search_regex(r'videoPlaybackUrl: *[\'"]([^\'"]+)[\'"]', tf_js, 'stream API url')
        api_key = self._search_regex(r'api_key: *[\'"]([^\'"]+)[\'"]', tf_js, 'stream API key')

        try:
            source_meta = self._download_json(f'{video_url}ref:{video_id}', video_id,
                                              headers={"X-Streaks-Api-Key": api_key},
                                              note='Downloading stream metadata')
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 403:
                self.raise_geo_restricted(countries=['JP'])
            raise

        formats = []
        subs = []
        for i in traverse_obj(source_meta, ('sources', ..., 'src')):
            format, sub = self._extract_m3u8_formats_and_subtitles(i, video_id)
            formats.extend(format)
            subs.extend(sub)

        return {
            'title': get_element_text_and_html_by_tag('h3', page)[0],
            'episode': traverse_obj(episode, ('title', lambda _, v: not v.get('is_phonetic'), 'value'), get_all=False),
            **episode_meta,
            'formats': formats,
            'subtitles': sub,
        }


class TBSJPProgramIE(InfoExtractor):
    _VALID_URL = r'https://cu\.tbs\.co\.jp/program/(?P<id>[\d]+)'
    _TESTS = [{
        'url': 'https://cu.tbs.co.jp/program/23601',
        'playlist_mincount': 4,
        'info_dict': {
            'id': '23601',
            'categories': ['エンタメ', 'ミライカプセル', '会社', '働く', 'バラエティ', '動画'],
            'description': '幼少期の夢は大人になって、どう成長したのだろうか？\nそしてその夢は今後、どのように広がっていくのか？\nいま話題の会社で働く人の「夢の成長」を描く',
            'series': 'ミライカプセル　-I have a dream-',
            'title': 'ミライカプセル　-I have a dream-'
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        page = self._download_webpage(url, video_id)
        meta = self._search_json('window.app=', page, 'programme info', video_id)

        programme = traverse_obj(meta, ('falcorCache', 'catalog', 'program', video_id, 'false', 'value'))

        return {
            '_type': 'playlist',
            'entries': [self.url_result(f'https://cu.tbs.co.jp/episode/{id}')
                        for id in traverse_obj(programme, ('custom_data', 'seriesList', 'episodeCode', ...))],
            **traverse_obj(programme, {
                'categories': 'keywords',
                'id': ('tv_episode_info', 'show_content_id'),
                'description': ('custom_data', 'program_description'),
                'series': ('custom_data', 'program_name'),
                'title': ('custom_data', 'program_name'),
            })}


class TBSJPPlaylistIE(InfoExtractor):
    _VALID_URL = r'https://cu\.tbs\.co\.jp/playlist/(?P<id>[\da-f]+)'
    _TESTS = [{
        'url': 'https://cu.tbs.co.jp/playlist/184f9970e7ba48e4915f1b252c55015e',
        'playlist_mincount': 4,
        'info_dict': {
            'title': 'まもなく配信終了',
            'id': '184f9970e7ba48e4915f1b252c55015e',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        page = self._download_webpage(url, video_id)
        meta = self._search_json('window.app=', page, 'playlist info', video_id)

        playlist = traverse_obj(meta, ('falcorCache', 'playList', video_id))

        entries = []
        for entry in traverse_obj(playlist, ('catalogs', 'value')):
            # it's likely possible to get most/all of the metadata from the playlist page json,
            # but just going to go with the lazy solution for now
            content_id = entry.get('content_id')
            content_type = entry.get('content_type')
            if content_type == 'tv_show':
                url = f'https://cu.tbs.co.jp/program/{content_id}'
            elif content_type == 'tv_episode':
                url = f'https://cu.tbs.co.jp/episode/{content_id}'
            else:
                self.report_warning(f'{content_id}: Unexpected content_type: {content_type}. Skipping.')

            if url:
                entries.append(self.url_result(url))

        return {
            '_type': 'playlist',
            **traverse_obj(playlist, {
                'id': ('id', 'value'),
                'title': ('display_name', 'value'),
                'playlist_count': ('total_count', 'value'),
            }),
            'entries': entries,
        }
