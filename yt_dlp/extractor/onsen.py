import base64
import json

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    clean_html,
    int_or_none,
    parse_qs,
    str_or_none,
    strftime_or_none,
    update_url,
    update_url_query,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class OnsenIE(InfoExtractor):
    IE_NAME = 'onsen'
    IE_DESC = 'インターネットラジオステーション＜音泉＞'

    _BASE_URL = 'https://www.onsen.ag'
    _HEADERS = {'Referer': f'{_BASE_URL}/'}
    _NETRC_MACHINE = 'onsen'
    _VALID_URL = r'https?://(?:(?:share|www)\.)onsen\.ag/program/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://share.onsen.ag/program/onsenking?p=90&c=MTA0NjI',
        'info_dict': {
            'id': '10462',
            'ext': 'm4a',
            'title': '第SP回',
            'cast': 'count:3',
            'description': 'md5:de62c80a41c4c8d84da53a1ee681ad18',
            'display_id': 'MTA0NjI=',
            'media_type': 'sound',
            'section_start': 0,
            'series': '音泉キング「下野紘」のラジオ きみはもちろん、＜音泉＞ファミリーだよね？',
            'series_id': 'onsenking',
            'tags': 'count:2',
            'thumbnail': r're:https?://d3bzklg4lms4gh\.cloudfront\.net/program_info/image/default/production/.+',
            'upload_date': '20220627',
            'webpage_url': 'https://www.onsen.ag/program/onsenking?c=MTA0NjI=',
        },
    }, {
        'url': 'https://share.onsen.ag/program/girls-band-cry-radio?p=370&c=MTgwMDE',
        'info_dict': {
            'id': '18001',
            'ext': 'mp4',
            'title': '第4回',
            'cast': 'count:5',
            'description': 'md5:bbca8a389d99c90cbbce8f383c85fedd',
            'display_id': 'MTgwMDE=',
            'media_type': 'movie',
            'section_start': 0,
            'series': 'TVアニメ『ガールズバンドクライ』WEBラジオ「ガールズバンドクライ～ラジオにも全部ぶち込め。～」',
            'series_id': 'girls-band-cry-radio',
            'tags': 'count:3',
            'thumbnail': r're:https?://d3bzklg4lms4gh\.cloudfront\.net/program_info/image/default/production/.+',
            'upload_date': '20240425',
            'webpage_url': 'https://www.onsen.ag/program/girls-band-cry-radio?c=MTgwMDE=',
        },
        'skip': 'Only available for premium supporters',
    }, {
        'url': 'https://www.onsen.ag/program/uma',
        'info_dict': {
            'id': 'uma',
            'title': 'UMA YELL RADIO',
        },
        'playlist_mincount': 35,
    }]

    @staticmethod
    def _get_encoded_id(program):
        return base64.urlsafe_b64encode(str(program['id']).encode()).decode()

    def _perform_login(self, username, password):
        sign_in = self._download_json(
            f'{self._BASE_URL}/web_api/signin', None, 'Logging in', headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            }, data=json.dumps({
                'session': {
                    'email': username,
                    'password': password,
                },
            }).encode(), expected_status=401)

        if sign_in.get('error'):
            raise ExtractorError('Invalid username or password', expected=True)

    def _real_extract(self, url):
        program_id = self._match_id(url)
        try:
            programs = self._download_json(
                f'{self._BASE_URL}/web_api/programs/{program_id}', program_id)
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 404:
                raise ExtractorError('Invalid URL', expected=True)
            raise

        query = {k: v[-1] for k, v in parse_qs(url).items() if v}
        if 'c' not in query:
            entries = [
                self.url_result(update_url_query(url, {'c': self._get_encoded_id(program)}), OnsenIE)
                for program in traverse_obj(programs, ('contents', lambda _, v: v['id']))
            ]

            return self.playlist_result(
                entries, program_id, traverse_obj(programs, ('program_info', 'title', {clean_html})))

        raw_id = base64.urlsafe_b64decode(f'{query["c"]}===').decode()
        p_keys = ('contents', lambda _, v: v['id'] == int(raw_id))

        program = traverse_obj(programs, (*p_keys, any))
        if not program:
            raise ExtractorError(
                'This program is no longer available', expected=True)
        m3u8_url = traverse_obj(program, ('streaming_url', {url_or_none}))
        if not m3u8_url:
            self.raise_login_required(
                'This program is only available for premium supporters')

        display_id = self._get_encoded_id(program)
        date_str = self._search_regex(
            rf'{program_id}0?(\d{{6}})', m3u8_url, 'date string', default=None)

        return {
            'display_id': display_id,
            'formats': self._extract_m3u8_formats(m3u8_url, raw_id, headers=self._HEADERS),
            'http_headers': self._HEADERS,
            'section_start': int_or_none(query.get('t', 0)),
            'upload_date': strftime_or_none(f'20{date_str}'),
            'webpage_url': f'{self._BASE_URL}/program/{program_id}?c={display_id}',
            **traverse_obj(program, {
                'id': ('id', {int}, {str_or_none}),
                'title': ('title', {clean_html}),
                'media_type': ('media_type', {str}),
                'thumbnail': ('poster_image_url', {url_or_none}, {update_url(query=None)}),
            }),
            **traverse_obj(programs, {
                'cast': (('performers', (*p_keys, 'guests')), ..., 'name', {str}, filter),
                'series_id': ('directory_name', {str}),
            }),
            **traverse_obj(programs, ('program_info', {
                'description': ('description', {clean_html}, filter),
                'series': ('title', {clean_html}),
                'tags': ('hashtag_list', ..., {str}, filter),
            })),
        }
