import base64
import datetime as dt
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
    IE_DESC = 'インターネットラジオステーション＜音泉＞'

    _BASE_URL = 'https://www.onsen.ag/'
    _HEADERS = {'Referer': _BASE_URL}
    _NETRC_MACHINE = 'onsen'
    _VALID_URL = r'https?://(?:(?:share|www)\.)onsen\.ag/program/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://share.onsen.ag/program/onsenking?p=90&c=MTA0NjI',
        'info_dict': {
            'id': '10462',
            'ext': 'm4a',
            'title': '第SP回',
            'cast': ['下野紘', '佐藤元', '守屋亨香'],
            'description': 'md5:083c1eddf198694cd3cc83f4d5c03863',
            'display_id': 'MTA0NjI=',
            'http_headers': {'Referer': 'https://www.onsen.ag/'},
            'media_type': 'sound',
            'section_start': 0,
            'series': '音泉キング「下野紘」のラジオ きみはもちろん、＜音泉＞ファミリーだよね？',
            'series_id': 'onsenking',
            'tags': ['音泉キング', '音泉ジュニア'],
            'thumbnail': r're:https://d3bzklg4lms4gh\.cloudfront\.net/program_info/image/default/production/.+$',
            'upload_date': '20220627',
            'webpage_url': 'https://www.onsen.ag/program/onsenking?c=MTA0NjI=',
        },
    }, {
        'url': 'https://share.onsen.ag/program/girls-band-cry-radio?p=370&c=MTgwMDE',
        'info_dict': {
            'id': '18001',
            'ext': 'mp4',
            'title': '第4回',
            'cast': ['夕莉', '理名', '朱李', '凪都', '美怜'],
            'description': 'md5:1d7f6a2f1f5a3e2a8ada4e9f652262dd',
            'display_id': 'MTgwMDE=',
            'http_headers': {'Referer': 'https://www.onsen.ag/'},
            'media_type': 'movie',
            'section_start': 0,
            'series': 'TVアニメ『ガールズバンドクライ』WEBラジオ「ガールズバンドクライ～ラジオにも全部ぶち込め。～」',
            'series_id': 'girls-band-cry-radio',
            'tags': ['ガールズバンドクライ', 'ガルクラ', 'ガルクラジオ'],
            'thumbnail': r're:https://d3bzklg4lms4gh\.cloudfront\.net/program_info/image/default/production/.+$',
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
        display_id = base64.b64encode(str(program['id']).encode()).decode()
        if ud := self._search_regex(rf'{program_id}0?(\d{{6}})', m3u8, 'upload_date', default=None):
            try:
                ud = dt.datetime.strptime(f'20{ud}', '%Y%m%d').strftime('%Y%m%d')
            except ValueError:
                ud = None

        return {
            'display_id': display_id,
            'formats': self._extract_m3u8_formats(m3u8, program_id, headers=self._HEADERS),
            'http_headers': self._HEADERS,
            'upload_date': ud,
            'webpage_url': f'{self._BASE_URL}program/{program_id}?c={display_id}',
            **metadata,
            **traverse_obj(program, {
                'id': ('id', {str_or_none}),
                'title': ('title', {strip_or_none}),
                'media_type': ('media_type', {str}),
                'thumbnail': ('poster_image_url', {lambda x: x.split('?')[0]}),
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
