import base64
import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    parse_qs,
    str_or_none,
    strip_or_none,
)
from ..utils.traversal import traverse_obj


class OnsenIE(InfoExtractor):
    IE_NAME = 'onsen'
    IE_DESC = '音泉'

    _BASE_URL = 'https://www.onsen.ag/'
    _HEADERS = {'Referer': _BASE_URL}
    _NETRC_MACHINE = 'onsen'
    _VALID_URL = r'https?://(?:(?:share|www)\.)onsen\.ag/program/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://share.onsen.ag/program/tricolor?p=393&c=MTk2NjE',
        'info_dict': {
            'id': '19661',
            'title': '第0回',
            'cast': ['礒部花凜', '土屋李央', '林鼓子'],
            'ext': 'm4a',
            'description': 'md5:8435d68dcb7a43bc2c993911b0db245b',
            'display_id': 'MTk2NjE=',
            'http_headers': {'Referer': 'https://www.onsen.ag/'},
            'media_type': 'sound',
            'tags': ['かりこ'],
            'thumbnail': 'https://d3bzklg4lms4gh.cloudfront.net/program_info/image/default/production/31/ea/c1db117c9b41655120d3a212b2038d15811f/image',
            'section_start': 0,
            'series': '礒部花凜・土屋李央・林鼓子 トリコロールカラー',
            'series_id': 'tricolor',
            'upload_date': '20240907',
            'webpage_url': 'https://www.onsen.ag/program/tricolor?c=MTk2NjE=',
        },
    }, {
        'url': 'https://share.onsen.ag/program/girls-band-cry-radio?p=370&c=MTgwMDE',
        'info_dict': {
            'id': '18001',
            'title': '第4回',
            'cast': ['夕莉', '理名', '朱李', '凪都', '美怜'],
            'ext': 'mp4',
            'description': 'md5:1d7f6a2f1f5a3e2a8ada4e9f652262dd',
            'display_id': 'MTgwMDE=',
            'http_headers': {'Referer': 'https://www.onsen.ag/'},
            'media_type': 'movie',
            'tags': ['ガールズバンドクライ', 'ガルクラ', 'ガルクラジオ'],
            'thumbnail': 'https://d3bzklg4lms4gh.cloudfront.net/program_info/image/default/production/95/a7/6a848c87bebf3ec085d8890f3ce038f9b4dd/image',
            'section_start': 0,
            'series': 'TVアニメ『ガールズバンドクライ』WEBラジオ「ガールズバンドクライ～ラジオにも全部ぶち込め。～」',
            'series_id': 'girls-band-cry-radio',
            'upload_date': '20240425',
            'webpage_url': 'https://www.onsen.ag/program/girls-band-cry-radio?c=MTgwMDE=',
        },
        'skip': 'Only available for premium supporters',
    }, {
        'url': 'https://www.onsen.ag/program/g-witch',
        'info_dict': {
            'id': 'g-witch',
            'title': '機動戦士ガンダム 水星の魔女～アスティカシア高等専門学園 ラジオ委員会～',
        },
        'playlist_mincount': 7,
    }]

    def _perform_login(self, username, password):
        signin = self._download_json(
            f'{self._BASE_URL}web_api/signin', None, 'Logging in', headers={
                'content-type': 'application/json; charset=UTF-8',
            }, data=json.dumps({
                'session': {
                    'email': username,
                    'password': password,
                },
            }).encode(), expected_status=401)

        if signin.get('error'):
            raise ExtractorError('Invalid username or password', expected=True)

    def _get_info(self, program, program_id, metadata):
        m3u8 = program['streaming_url']
        rd = self._search_regex(f'{program_id}(\\d{{6}})', m3u8, 'release_date', default=None)
        display_id = base64.b64encode(str(program['id']).encode()).decode()

        return {
            'display_id': display_id,
            'formats': self._extract_m3u8_formats(m3u8, program_id, headers=self._HEADERS),
            'http_headers': self._HEADERS,
            'upload_date': f'20{rd}' if rd else None,
            'webpage_url': f'{self._BASE_URL}program/{program_id}?c={display_id}',
            **metadata,
            **traverse_obj(program, {
                'id': ('id', {str_or_none}),
                'title': ('title', {strip_or_none}),
                'thumbnail': ('poster_image_url', {lambda x: x.split('?')[0]}),
                'media_type': ('media_type', {str}),
            }),
            'cast': metadata['cast'] + traverse_obj(program, ('guests', ..., 'name', {str})),
        }

    def _real_extract(self, url):
        program_id = self._match_id(url)
        qs = {k: v[0] for k, v in parse_qs(url).items() if v}
        programs = self._download_json(
            f'{self._BASE_URL}web_api/programs/{program_id}', program_id)

        metadata = {
            'cast': traverse_obj(programs, ('performers', ..., 'name', {str})),
            'section_start': int(qs.get('t', 0)),
            'series_id': program_id,
            **traverse_obj(programs['program_info'], {
                'description': ('description', {str}),
                'series': ('title', {str}),
                'tags': ('hashtag_list', {list}),
            }),
        }

        if 'c' in qs:
            p_id = base64.b64decode(qs['c'] + '=' * (-len(qs['c']) % 4)).decode()
            program = traverse_obj(
                programs, ('contents', lambda _, v: v['id'] == int(p_id)), get_all=False)
            if not program:
                raise ExtractorError('This program is no longer available', expected=True)
            if not program['streaming_url']:
                self.raise_login_required('This program is only available for premium supporters')

            return self._get_info(program, program_id, metadata)
        else:
            entries = [
                self._get_info(program, program_id, metadata)
                for program in programs['contents'] if program['streaming_url']
            ]

            return self.playlist_result(entries, program_id, metadata['series'])
