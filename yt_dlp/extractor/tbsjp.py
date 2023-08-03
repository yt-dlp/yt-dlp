from .common import InfoExtractor

from ..utils import (
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

        source_meta = self._download_json(f'{video_url}ref:{video_id}', video_id,
            headers={"X-Streaks-Api-Key": api_key}, note='Downloading stream metadata')

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
