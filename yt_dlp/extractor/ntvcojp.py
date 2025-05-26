from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    clean_html,
    int_or_none,
    unified_timestamp,
    urljoin,
)
from ..utils.traversal import find_element, traverse_obj


class NTVCoJpCUIE(InfoExtractor):
    IE_NAME = 'cu.ntv.co.jp'
    IE_DESC = 'Nippon Television Network'
    _VALID_URL = r'https?://cu\.ntv\.co\.jp/(?!program)(?P<id>[^/?&#]+)'
    _TEST = {
        'url': 'https://cu.ntv.co.jp/gaki_20250525/',
        'info_dict': {
            'title': '放送開始36年!方正ココリコが選ぶ神回&地獄回!',
            'id': 'gaki_20250525',
            'ext': 'mp4',
            'categories': ['ダウンタウンのガキの使いやあらへんで！'],
            'description': '神回地獄回座談会!レギュラー放送1756回の中からココリコと方正が神回と地獄回をそれぞれ選んで発表!若手時代の遠藤がガキ使メンバーに振り回される!?田中が好きな懐かしの番組名物キャラに爆笑!?方正が思い出に残っている持ち込み回とは?笑ってはいけないシリーズから遠藤が大汗をかくほど追い詰められる企画が誕生していた!?3人のトラウマになっている過酷罰ゲームを振り返り!方正記念企画のはずがまさかの展開で涙!?',
            'timestamp': 1748145124,
            'release_timestamp': 1748145539,
            'duration': 1450,
            'episode_number': 255,
            'episode': '放送開始36年!方正ココリコが選ぶ神回&地獄回!',
            'upload_date': '20250525',
            'release_date': '20250525',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        meta = self._search_json(r'window\.app\s*=', webpage, 'episode info', video_id, fatal=False)
        episode = traverse_obj(meta, ('falcorCache', 'catalog', 'episode', video_id, 'value'))

        nt_path = self._search_regex(r'<script[^>]+src=["\'](/assets/nt\.[^"\']+\.js)["\']', webpage, 'stream API config')
        nt_js = self._download_webpage(urljoin(url, nt_path), video_id, note='Downloading stream API config')
        video_url = self._search_regex(r'videoPlaybackUrl:\s*[\'"]([^\'"]+)[\'"]', nt_js, 'stream API url')
        api_key = self._search_regex(r'api_key:\s*[\'"]([^\'"]+)[\'"]', nt_js, 'stream API key')

        try:
            source_meta = self._download_json(
                f'{video_url}ref:{video_id}',
                video_id,
                headers={'X-Streaks-Api-Key': api_key},
                note='Downloading stream metadata',
            )
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 403:
                self.raise_geo_restricted(countries=['JP'])
            raise

        formats, subtitles = [], {}
        for src in traverse_obj(source_meta, ('sources', ..., 'src')):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(src, video_id, fatal=False)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        return {
            'title': traverse_obj(webpage, ({find_element(tag='h3')}, {clean_html})),
            'id': video_id,
            **traverse_obj(
                episode,
                {
                    'categories': ('keywords', {list}),
                    'id': ('content_id', {str}),
                    'description': ('description', 0, 'value'),
                    'timestamp': ('created_at', {unified_timestamp}),
                    'release_timestamp': ('pub_date', {unified_timestamp}),
                    'duration': ('tv_episode_info', 'duration', {int_or_none}),
                    'episode_number': ('tv_episode_info', 'episode_number', {int_or_none}),
                    'episode': ('title', lambda _, v: not v.get('is_phonetic'), 'value'),
                    'series': ('custom_data', 'program_name'),
                },
                get_all=False,
            ),
            'formats': formats,
            'subtitles': subtitles,
        }
