import hashlib
import json
import re
import time

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import ExtractorError, int_or_none, join_nonempty, url_or_none
from ..utils.traversal import traverse_obj


class DangalPlayBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'dangalplay'
    _REGION = 'IN'
    _OTV_USER_ID = None
    _LOGIN_HINT = (
        'Pass credentials as -u "token" -p "USER_ID" '
        '(where USER_ID is the value of "otv_user_id" in your browser local storage). '
        'Your login region can be optionally suffixed to the username as @REGION '
        '(where REGION is the two-letter "region" code found in your browser local storage), '
        'e.g.: -u "token@IN" -p "USER_ID"')
    _API_BASE = 'https://ottapi.dangalplay.com'
    _AUTH_TOKEN = 'jqeGWxRKK7FK5zEk3xCM'  # from https://www.dangalplay.com/main.48ad19e24eb46acccef3.js
    _SECRET_KEY = 'f53d31a4377e4ef31fa0'  # same as above

    def _perform_login(self, username, password):
        if self._OTV_USER_ID:
            return
        mobj = re.fullmatch(r'token(?:@(?P<region>[A-Z]{2}))?', username)
        if not mobj or not re.fullmatch(r'[\da-f]{32}', password):
            raise ExtractorError(self._LOGIN_HINT, expected=True)
        if region := mobj.group('region'):
            self._REGION = region
        self.write_debug(f'Setting login region to "{self._REGION}"')
        self._OTV_USER_ID = password

    def _real_initialize(self):
        if not self._OTV_USER_ID:
            self.raise_login_required(f'Login required. {self._LOGIN_HINT}', method=None)

    def _extract_episode_info(self, metadata, episode_slug, series_slug):
        return {
            'display_id': episode_slug,
            'episode_number': int_or_none(self._search_regex(
                r'ep-(?:number-)?(\d+)', episode_slug, 'episode number', default=None)),
            'season_number': int_or_none(self._search_regex(
                r'season-(\d+)', series_slug, 'season number', default='1')),
            'series': series_slug,
            **traverse_obj(metadata, {
                'id': ('content_id', {str}),
                'title': ('display_title', {str}),
                'episode': ('title', {str}),
                'series': ('show_name', {str}, filter),
                'series_id': ('catalog_id', {str}),
                'duration': ('duration', {int_or_none}),
                'release_timestamp': ('release_date_uts', {int_or_none}),
            }),
        }

    def _call_api(self, path, display_id, note='Downloading JSON metadata', fatal=True, query={}):
        return self._download_json(
            f'{self._API_BASE}/{path}', display_id, note, fatal=fatal,
            headers={'Accept': 'application/json'}, query={
                'auth_token': self._AUTH_TOKEN,
                'region': self._REGION,
                **query,
            })


class DangalPlayIE(DangalPlayBaseIE):
    IE_NAME = 'dangalplay'
    _VALID_URL = r'https?://(?:www\.)?dangalplay.com/shows/(?P<series>[^/?#]+)/(?P<id>(?!episodes)[^/?#]+)/?(?:$|[?#])'
    _TESTS = [{
        'url': 'https://www.dangalplay.com/shows/kitani-mohabbat-hai-season-2/kitani-mohabbat-hai-season-2-ep-number-01',
        'info_dict': {
            'id': '647c61dc1e7171310dcd49b4',
            'ext': 'mp4',
            'release_timestamp': 1262304000,
            'episode_number': 1,
            'episode': 'EP 1 | KITANI MOHABBAT HAI SEASON 2',
            'series': 'kitani-mohabbat-hai-season-2',
            'season_number': 2,
            'title': 'EP 1 | KITANI MOHABBAT HAI SEASON 2',
            'release_date': '20100101',
            'duration': 2325,
            'season': 'Season 2',
            'display_id': 'kitani-mohabbat-hai-season-2-ep-number-01',
            'series_id': '645c9ea41e717158ca574966',
        },
    }, {
        'url': 'https://www.dangalplay.com/shows/milke-bhi-hum-na-mile/milke-bhi-hum-na-mile-ep-number-01',
        'info_dict': {
            'id': '65d31d9ba73b9c3abd14a7f3',
            'ext': 'mp4',
            'episode': 'EP 1 | MILKE BHI HUM NA MILE',
            'release_timestamp': 1708367411,
            'episode_number': 1,
            'season': 'Season 1',
            'title': 'EP 1 | MILKE BHI HUM NA MILE',
            'duration': 156048,
            'release_date': '20240219',
            'season_number': 1,
            'series': 'MILKE BHI HUM NA MILE',
            'series_id': '645c9ea41e717158ca574966',
            'display_id': 'milke-bhi-hum-na-mile-ep-number-01',
        },
    }]

    def _generate_api_data(self, data):
        catalog_id = data['catalog_id']
        content_id = data['content_id']
        timestamp = str(int(time.time()))
        unhashed = ''.join((catalog_id, content_id, self._OTV_USER_ID, timestamp, self._SECRET_KEY))

        return json.dumps({
            'catalog_id': catalog_id,
            'content_id': content_id,
            'category': '',
            'region': self._REGION,
            'auth_token': self._AUTH_TOKEN,
            'id': self._OTV_USER_ID,
            'md5': hashlib.md5(unhashed.encode()).hexdigest(),
            'ts': timestamp,
        }, separators=(',', ':')).encode()

    def _real_extract(self, url):
        series_slug, episode_slug = self._match_valid_url(url).group('series', 'id')
        metadata = self._call_api(
            f'catalogs/shows/{series_slug}/episodes/{episode_slug}.gzip',
            episode_slug, query={'item_language': ''})['data']

        try:
            details = self._download_json(
                f'{self._API_BASE}/v2/users/get_all_details.gzip', episode_slug,
                'Downloading playback details JSON', headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                }, data=self._generate_api_data(metadata))['data']
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 422:
                error_info = traverse_obj(e.cause.response.read().decode(), ({json.loads}, 'error', {dict})) or {}
                error_code = error_info.get('code')
                if error_code == '1016':
                    self.raise_login_required(
                        f'Your token has expired or is invalid. {self._LOGIN_HINT}', method=None)
                elif error_code == '4028':
                    self.raise_login_required(
                        f'Your login region is unspecified or incorrect. {self._LOGIN_HINT}', method=None)
                raise ExtractorError(join_nonempty(error_code, error_info.get('message'), delim=': '))
            raise

        m3u8_url = traverse_obj(details, (
            ('adaptive_url', ('adaptive_urls', 'hd', 'hls', ..., 'playback_url')), {url_or_none}, any))
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(m3u8_url, episode_slug, 'mp4')

        return {
            'formats': formats,
            'subtitles': subtitles,
            **self._extract_episode_info(metadata, episode_slug, series_slug),
        }


class DangalPlaySeasonIE(DangalPlayBaseIE):
    IE_NAME = 'dangalplay:season'
    _VALID_URL = r'https?://(?:www\.)?dangalplay.com/shows/(?P<id>[^/?#]+)(?:/(?P<sub>ep-[^/?#]+)/episodes)?/?(?:$|[?#])'
    _TESTS = [{
        'url': 'https://www.dangalplay.com/shows/kitani-mohabbat-hai-season-1',
        'playlist_mincount': 170,
        'info_dict': {
            'id': 'kitani-mohabbat-hai-season-1',
        },
    }, {
        'url': 'https://www.dangalplay.com/shows/kitani-mohabbat-hai-season-1/ep-01-30-1/episodes',
        'playlist_count': 30,
        'info_dict': {
            'id': 'kitani-mohabbat-hai-season-1-ep-01-30-1',
        },
    }, {
        # 1 season only, series page is season page
        'url': 'https://www.dangalplay.com/shows/milke-bhi-hum-na-mile',
        'playlist_mincount': 15,
        'info_dict': {
            'id': 'milke-bhi-hum-na-mile',
        },
    }]

    def _entries(self, subcategories, series_slug):
        for subcategory in subcategories:
            data = self._call_api(
                f'catalogs/shows/items/{series_slug}/subcategories/{subcategory}/episodes.gzip',
                series_slug, f'Downloading episodes JSON for {subcategory}', fatal=False, query={
                    'order_by': 'asc',
                    'status': 'published',
                })
            for ep in traverse_obj(data, ('data', 'items', lambda _, v: v['friendly_id'])):
                episode_slug = ep['friendly_id']
                yield self.url_result(
                    f'https://www.dangalplay.com/shows/{series_slug}/{episode_slug}',
                    DangalPlayIE, **self._extract_episode_info(ep, episode_slug, series_slug))

    def _real_extract(self, url):
        series_slug, subcategory = self._match_valid_url(url).group('id', 'sub')
        subcategories = [subcategory] if subcategory else traverse_obj(
            self._call_api(
                f'catalogs/shows/items/{series_slug}.gzip', series_slug,
                'Downloading season info JSON', query={'item_language': ''}),
            ('data', 'subcategories', ..., 'friendly_id', {str}))

        return self.playlist_result(
            self._entries(subcategories, series_slug), join_nonempty(series_slug, subcategory))
