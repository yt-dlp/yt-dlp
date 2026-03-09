import functools
import math

from .streaks import StreaksBaseIE
from ..networking import HEADRequest
from ..utils import (
    InAdvancePagedList,
    clean_html,
    js_to_json,
    parse_iso8601,
    parse_qs,
    str_or_none,
)
from ..utils.traversal import require, traverse_obj


class LocipoBaseIE(StreaksBaseIE):
    _API_BASE = 'https://web-api.locipo.jp'
    _BASE_URL = 'https://locipo.jp'
    _UUID_RE = r'[\da-f]{8}(?:-[\da-f]{4}){3}-[\da-f]{12}'

    def _call_api(self, path, item_id, note, fatal=True):
        return self._download_json(
            f'{self._API_BASE}/{path}', item_id,
            f'Downloading {note} API JSON',
            f'Unable to download {note} API JSON',
            fatal=fatal)


class LocipoIE(LocipoBaseIE):
    _VALID_URL = [
        fr'https?://locipo\.jp/creative/(?P<id>{LocipoBaseIE._UUID_RE})',
        fr'https?://locipo\.jp/embed/?\?(?:[^#]+&)?id=(?P<id>{LocipoBaseIE._UUID_RE})',
    ]
    _TESTS = [{
        'url': 'https://locipo.jp/creative/fb5ffeaa-398d-45ce-bb49-0e221b5f94f1',
        'info_dict': {
            'id': 'fb5ffeaa-398d-45ce-bb49-0e221b5f94f1',
            'ext': 'mp4',
            'title': 'リアルカレカノ#4 ～伊達さゆりと勉強しよっ？～',
            'description': 'md5:70a40c202f3fb7946b61e55fa015094c',
            'display_id': '5a2947fe596441f5bab88a61b0432d0d',
            'live_status': 'not_live',
            'modified_date': r're:\d{8}',
            'modified_timestamp': int,
            'release_timestamp': 1711789200,
            'release_date': '20240330',
            'series': 'リアルカレカノ',
            'series_id': '1142',
            'tags': 'count:4',
            'thumbnail': r're:https?://.+\.(?:jpg|png)',
            'timestamp': 1756984919,
            'upload_date': '20250904',
            'uploader': '東海テレビ',
            'uploader_id': 'locipo-prod',
        },
    }, {
        'url': 'https://locipo.jp/embed/?id=71a334a0-2b25-406f-9d96-88f341f571c2',
        'info_dict': {
            'id': '71a334a0-2b25-406f-9d96-88f341f571c2',
            'ext': 'mp4',
            'title': '#1 オーディション／ゲスト伊藤美来、豊田萌絵',
            'description': 'md5:5bbcf532474700439cf56ceb6a15630e',
            'display_id': '0ab32634b884499a84adb25de844c551',
            'live_status': 'not_live',
            'modified_date': r're:\d{8}',
            'modified_timestamp': int,
            'release_timestamp': 1751623200,
            'release_date': '20250704',
            'series': '声優ラジオのウラカブリ～Locipo出張所～',
            'series_id': '1454',
            'tags': 'count:6',
            'thumbnail': r're:https?://.+\.(?:jpg|png)',
            'timestamp': 1757002966,
            'upload_date': '20250904',
            'uploader': 'テレビ愛知',
            'uploader_id': 'locipo-prod',
        },
    }, {
        'url': 'https://locipo.jp/creative/bff9950d-229b-4fe9-911a-7fa71a232f35?list=69a5b15c-901f-4828-a336-30c0de7612d3',
        'info_dict': {
            'id': '69a5b15c-901f-4828-a336-30c0de7612d3',
            'title': '見て・乗って・語りたい。 東海の鉄道沼',
        },
        'playlist_mincount': 3,
    }, {
        'url': 'https://locipo.jp/creative/a0751a7f-c7dd-4a10-a7f1-e12720bdf16c?list=006cff3f-ba74-42f0-b4fd-241486ebda2b',
        'info_dict': {
            'id': 'a0751a7f-c7dd-4a10-a7f1-e12720bdf16c',
            'ext': 'mp4',
            'title': '#839 人間真空パック',
            'description': 'md5:9fe190333b6975c5001c8c9cbe20d276',
            'display_id': 'c2b4c9f4a6d648bd8e3c320e384b9d56',
            'live_status': 'not_live',
            'modified_date': r're:\d{8}',
            'modified_timestamp': int,
            'release_timestamp': 1746239400,
            'release_date': '20250503',
            'series': 'でんじろう先生のはぴエネ！',
            'series_id': '202',
            'tags': 'count:3',
            'thumbnail': r're:https?://.+\.(?:jpg|png)',
            'timestamp': 1756975909,
            'upload_date': '20250904',
            'uploader': '中京テレビ',
            'uploader_id': 'locipo-prod',
        },
        'params': {'noplaylist': True},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        playlist_id = traverse_obj(parse_qs(url), ('list', -1, {str}))
        if self._yes_playlist(playlist_id, video_id):
            return self.url_result(
                f'{self._BASE_URL}/playlist/{playlist_id}', LocipoPlaylistIE)

        creatives = self._call_api(f'creatives/{video_id}', video_id, 'Creatives')
        media_id = traverse_obj(creatives, ('media_id', {str}, {require('Streaks media ID')}))

        webpage = self._download_webpage(url, video_id)
        config = self._search_json(
            r'window\.__NUXT__\.config\s*=', webpage, 'config', video_id, transform_source=js_to_json)
        api_key = traverse_obj(config, ('public', 'streaksVodPlaybackApiKey', {str}, {require('api key')}))

        return {
            **self._extract_from_streaks_api('locipo-prod', media_id, headers={
                'Origin': 'https://locipo.jp',
                'X-Streaks-Api-Key': api_key,
            }),
            **traverse_obj(creatives, {
                'title': ('name', {clean_html}),
                'description': ('description', {clean_html}, filter),
                'release_timestamp': ('publication_started_at', {parse_iso8601}),
                'tags': ('keyword', {clean_html}, {lambda x: x.split(',')}, ..., {str.strip}, filter),
                'uploader': ('company', 'name', {clean_html}, filter),
            }),
            **traverse_obj(creatives, ('series', {
                'series': ('name', {clean_html}, filter),
                'series_id': ('id', {str_or_none}),
            })),
            'id': video_id,
        }


class LocipoPlaylistIE(LocipoBaseIE):
    _VALID_URL = [
        fr'https?://locipo\.jp/(?P<type>playlist)/(?P<id>{LocipoBaseIE._UUID_RE})',
        r'https?://locipo\.jp/(?P<type>series)/(?P<id>\d+)',
    ]
    _TESTS = [{
        'url': 'https://locipo.jp/playlist/35d3dd2b-531d-4824-8575-b1c527d29538',
        'info_dict': {
            'id': '35d3dd2b-531d-4824-8575-b1c527d29538',
            'title': 'レシピ集',
        },
        'playlist_mincount': 135,
    }, {
        # Redirects to https://locipo.jp/series/1363
        'url': 'https://locipo.jp/playlist/fef7c4fb-741f-4d6a-a3a6-754f354302a2',
        'info_dict': {
            'id': '1363',
            'title': 'CBCアナウンサー公式【みてちょてれび】',
            'description': 'md5:50a1b23e63112d5c06c882835c8c1fb1',
        },
        'playlist_mincount': 38,
    }, {
        'url': 'https://locipo.jp/series/503',
        'info_dict': {
            'id': '503',
            'title': 'FishingLover東海',
            'description': '東海地区の釣り場でフィッシングの魅力を余すところなくご紹介！！',
        },
        'playlist_mincount': 223,
    }]
    _PAGE_SIZE = 100

    def _fetch_page(self, path, playlist_id, page):
        creatives = self._download_json(
            f'{self._API_BASE}/{path}/{playlist_id}/creatives',
            playlist_id, f'Downloading page {page + 1}', query={
                'premium': False,
                'live': False,
                'limit': self._PAGE_SIZE,
                'offset': page * self._PAGE_SIZE,
            })

        for video_id in traverse_obj(creatives, ('items', ..., 'id', {str})):
            yield self.url_result(f'{self._BASE_URL}/creative/{video_id}', LocipoIE)

    def _real_extract(self, url):
        playlist_type, playlist_id = self._match_valid_url(url).group('type', 'id')
        if urlh := self._request_webpage(HEADRequest(url), playlist_id, fatal=False):
            playlist_type, playlist_id = self._match_valid_url(urlh.url).group('type', 'id')

        path = 'playlists' if playlist_type == 'playlist' else 'series'
        creatives = self._call_api(
            f'{path}/{playlist_id}/creatives', playlist_id, path.capitalize())

        entries = InAdvancePagedList(
            functools.partial(self._fetch_page, path, playlist_id),
            math.ceil(int(creatives['total']) / self._PAGE_SIZE), self._PAGE_SIZE)

        return self.playlist_result(
            entries, playlist_id,
            **traverse_obj(creatives, ('items', ..., playlist_type, {
                'title': ('name', {clean_html}, filter),
                'description': ('description', {clean_html}, filter),
            }, any)))
