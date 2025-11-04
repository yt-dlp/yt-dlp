import base64
import datetime as dt
import itertools
import json
import re
import time

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    encode_data_uri,
    filter_dict,
    int_or_none,
    jwt_decode_hs256,
    url_or_none,
    urlencode_postdata,
    urljoin,
)
from ..utils.traversal import traverse_obj


class TenPlayIE(InfoExtractor):
    IE_NAME = '10play'
    _VALID_URL = r'https?://(?:www\.)?10(?:play)?\.com\.au/(?:[^/?#]+/)+(?P<id>tpv\d{6}[a-z]{5})'
    _NETRC_MACHINE = '10play'
    _TESTS = [{
        # Geo-restricted to Australia
        'url': 'https://10.com.au/australian-survivor/web-extras/season-10-brains-v-brawn-ii/myless-journey/tpv250414jdmtf',
        'info_dict': {
            'id': '7440980000013868',
            'ext': 'mp4',
            'title': 'Myles\'s Journey',
            'alt_title': 'Myles\'s Journey',
            'description': 'Relive Myles\'s epic Brains V Brawn II journey to reach the game\'s final two',
            'uploader': 'Channel 10',
            'uploader_id': '2199827728001',
            'age_limit': 15,
            'duration': 249,
            'thumbnail': r're:https://.+/.+\.jpg',
            'series': 'Australian Survivor',
            'season': 'Season 10',
            'season_number': 10,
            'timestamp': 1744629420,
            'upload_date': '20250414',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # Geo-restricted to Australia
        'url': 'https://10.com.au/neighbours/episodes/season-42/episode-9107/tpv240902nzqyp',
        'info_dict': {
            'id': '9000000000091177',
            'ext': 'mp4',
            'title': 'Neighbours - S42 Ep. 9107',
            'alt_title': 'Thu 05 Sep',
            'description': 'md5:37a1f4271be34b9ee2b533426a5fbaef',
            'duration': 1388,
            'episode': 'Episode 9107',
            'episode_number': 9107,
            'season': 'Season 42',
            'season_number': 42,
            'series': 'Neighbours',
            'thumbnail': r're:https://.+/.+\.jpg',
            'age_limit': 15,
            'timestamp': 1725517860,
            'upload_date': '20240905',
            'uploader': 'Channel 10',
            'uploader_id': '2199827728001',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # Geo-restricted to Australia; upgrading the m3u8 quality fails and we need the fallback
        'url': 'https://10.com.au/tiny-chef-show/episodes/season-1/episode-2/tpv240228pofvt',
        'info_dict': {
            'id': '9000000000084116',
            'ext': 'mp4',
            'uploader': 'Channel 10',
            'uploader_id': '2199827728001',
            'duration': 1297,
            'title': 'The Tiny Chef Show - S1 Ep. 2',
            'alt_title': 'S1 Ep. 2 - Popcorn/banana',
            'description': 'md5:d4758b52b5375dfaa67a78261dcb5763',
            'age_limit': 0,
            'series': 'The Tiny Chef Show',
            'season_number': 1,
            'episode_number': 2,
            'timestamp': 1747957740,
            'thumbnail': r're:https://.+/.+\.jpg',
            'upload_date': '20250522',
            'season': 'Season 1',
            'episode': 'Episode 2',
        },
        'params': {'skip_download': 'm3u8'},
        'expected_warnings': ['Failed to download m3u8 information: HTTP Error 502'],
        'skip': 'video unavailable',
    }, {
        'url': 'https://10play.com.au/how-to-stay-married/web-extras/season-1/terrys-talks-ep-1-embracing-change/tpv190915ylupc',
        'only_matching': True,
    }]
    _GEO_BYPASS = False
    _GEO_COUNTRIES = ['AU']
    _AUS_AGES = {
        'G': 0,
        'PG': 15,
        'M': 15,
        'MA': 15,
        'MA15+': 15,
        'R': 18,
        'X': 18,
    }
    _TOKEN_CACHE_KEY = 'token_data'
    _SEGMENT_BITRATE_RE = r'(?m)-(?:300|150|75|55)0000-(\d+(?:-[\da-f]+)?)\.ts$'

    _refresh_token = None
    _access_token = None

    @staticmethod
    def _filter_ads_from_m3u8(m3u8_doc):
        out = []
        for line in m3u8_doc.splitlines():
            if line.startswith('https://redirector.googlevideo.com/'):
                out.pop()
                continue
            out.append(line)

        return '\n'.join(out)

    @staticmethod
    def _generate_xnetwork_ten_auth_token():
        ts = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d%H%M%S')
        return base64.b64encode(ts.encode()).decode()

    @staticmethod
    def _is_jwt_expired(token):
        return jwt_decode_hs256(token)['exp'] - time.time() < 300

    def _refresh_access_token(self):
        try:
            refresh_data = self._download_json(
                'https://10.com.au/api/token/refresh', None, 'Refreshing access token',
                headers={
                    'Content-Type': 'application/json',
                }, data=json.dumps({
                    'accessToken': self._access_token,
                    'refreshToken': self._refresh_token,
                }).encode())
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 400:
                self._refresh_token = self._access_token = None
                self.cache.store(self._NETRC_MACHINE, self._TOKEN_CACHE_KEY, [None, None])
                self.report_warning('Refresh token has been invalidated; retrying with credentials')
                self._perform_login(*self._get_login_info())
                return
            raise
        self._access_token = refresh_data['accessToken']
        self._refresh_token = refresh_data['refreshToken']
        self.cache.store(self._NETRC_MACHINE, self._TOKEN_CACHE_KEY, [self._refresh_token, self._access_token])

    def _perform_login(self, username, password):
        if not self._refresh_token:
            self._refresh_token, self._access_token = self.cache.load(
                self._NETRC_MACHINE, self._TOKEN_CACHE_KEY, default=[None, None])
        if self._refresh_token and self._access_token:
            self.write_debug('Using cached refresh token')
            return

        try:
            auth_data = self._download_json(
                'https://10.com.au/api/user/auth', None, 'Logging in',
                headers={
                    'Content-Type': 'application/json',
                    'X-Network-Ten-Auth': self._generate_xnetwork_ten_auth_token(),
                    'Referer': 'https://10.com.au/',
                }, data=json.dumps({
                    'email': username,
                    'password': password,
                }).encode())
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 400:
                raise ExtractorError('Invalid username/password', expected=True)
            raise

        self._refresh_token = auth_data['jwt']['refreshToken']
        self._access_token = auth_data['jwt']['accessToken']
        self.cache.store(self._NETRC_MACHINE, self._TOKEN_CACHE_KEY, [self._refresh_token, self._access_token])

    def _call_playback_api(self, content_id):
        if self._access_token and self._is_jwt_expired(self._access_token):
            self._refresh_access_token()
        for is_retry in (False, True):
            try:
                return self._download_json_handle(
                    f'https://10.com.au/api/v1/videos/playback/{content_id}/', content_id,
                    note='Downloading video JSON', query={'platform': 'samsung'},
                    headers=filter_dict({
                        'TP-AcceptFeature': 'v1/fw;v1/drm',
                        'Authorization': f'Bearer {self._access_token}' if self._access_token else None,
                    }))
            except ExtractorError as e:
                if not is_retry and isinstance(e.cause, HTTPError) and e.cause.status == 403:
                    if self._access_token:
                        self.to_screen('Access token has expired; refreshing')
                        self._refresh_access_token()
                        continue
                    elif not self._get_login_info()[0]:
                        self.raise_login_required('Login required to access this video', method='password')
                raise

    def _real_extract(self, url):
        content_id = self._match_id(url)
        try:
            data = self._download_json(f'https://10.com.au/api/v1/videos/{content_id}', content_id)
        except ExtractorError as e:
            if (
                isinstance(e.cause, HTTPError) and e.cause.status == 403
                and 'Error 54113' in e.cause.response.read().decode()
            ):
                self.raise_geo_restricted(countries=self._GEO_COUNTRIES)
            raise

        video_data, urlh = self._call_playback_api(content_id)
        content_source_id = video_data['dai']['contentSourceId']
        video_id = video_data['dai']['videoId']
        auth_token = urlh.get_header('x-dai-auth')
        if not auth_token:
            raise ExtractorError('Failed to get DAI auth token')

        dai_data = self._download_json(
            f'https://pubads.g.doubleclick.net/ondemand/hls/content/{content_source_id}/vid/{video_id}/streams',
            content_id, note='Downloading DAI JSON',
            data=urlencode_postdata({'auth-token': auth_token}))

        # Ignore subs to avoid ad break cleanup
        formats, _ = self._extract_m3u8_formats_and_subtitles(
            dai_data['stream_manifest'], content_id, 'mp4')

        already_have_1080p = False
        for fmt in formats:
            m3u8_doc = self._download_webpage(
                fmt['url'], content_id, note='Downloading m3u8 information')
            m3u8_doc = self._filter_ads_from_m3u8(m3u8_doc)
            fmt['hls_media_playlist_data'] = m3u8_doc
            if fmt.get('height') == 1080:
                already_have_1080p = True

        # Attempt format upgrade
        if not already_have_1080p and m3u8_doc and re.search(self._SEGMENT_BITRATE_RE, m3u8_doc):
            m3u8_doc = re.sub(self._SEGMENT_BITRATE_RE, r'-5000000-\1.ts', m3u8_doc)
            m3u8_doc = re.sub(r'-(?:300|150|75|55)0000\.key"', r'-5000000.key"', m3u8_doc)
            formats.append({
                'format_id': 'upgrade-attempt-1080p',
                'url': encode_data_uri(m3u8_doc.encode(), 'application/x-mpegurl'),
                'hls_media_playlist_data': m3u8_doc,
                'width': 1920,
                'height': 1080,
                'ext': 'mp4',
                'protocol': 'm3u8_native',
                '__needs_testing': True,
            })

        return {
            'id': content_id,
            'formats': formats,
            'subtitles': {'en': [{'url': data['captionUrl']}]} if url_or_none(data.get('captionUrl')) else None,
            'uploader': 'Channel 10',
            'uploader_id': '2199827728001',
            **traverse_obj(data, {
                'id': ('altId', {str}),
                'duration': ('duration', {int_or_none}),
                'title': ('subtitle', {str}),
                'alt_title': ('title', {str}),
                'description': ('description', {str}),
                'age_limit': ('classification', {self._AUS_AGES.get}),
                'series': ('tvShow', {str}),
                'season_number': ('season', {int_or_none}),
                'episode_number': ('episode', {int_or_none}),
                'timestamp': ('published', {int_or_none}),
                'thumbnail': ('imageUrl', {url_or_none}),
            }),
        }


class TenPlaySeasonIE(InfoExtractor):
    IE_NAME = '10play:season'
    _VALID_URL = r'https?://(?:www\.)?10(?:play)?\.com\.au/(?P<show>[^/?#]+)/episodes/(?P<season>[^/?#]+)/?(?:$|[?#])'
    _TESTS = [{
        'url': 'https://10.com.au/masterchef/episodes/season-15',
        'info_dict': {
            'title': 'Season 15',
            'id': 'MTQ2NjMxOQ==',
        },
        'playlist_mincount': 50,
    }, {
        'url': 'https://10.com.au/the-bold-and-the-beautiful-fast-tracked/episodes/season-2024',
        'info_dict': {
            'title': 'Season 2024',
            'id': 'Mjc0OTIw',
        },
        'playlist_mincount': 159,
    }, {
        'url': 'https://10play.com.au/the-bold-and-the-beautiful-fast-tracked/episodes/season-2024',
        'only_matching': True,
    }]

    def _entries(self, load_more_url, display_id=None):
        skip_ids = []
        for page in itertools.count(1):
            episodes_carousel = self._download_json(
                load_more_url, display_id, query={'skipIds[]': skip_ids},
                note=f'Fetching episodes page {page}')

            episodes_chunk = episodes_carousel['items']
            skip_ids.extend(ep['id'] for ep in episodes_chunk)

            for ep in episodes_chunk:
                yield ep['cardLink']
            if not episodes_carousel['hasMore']:
                break

    def _real_extract(self, url):
        show, season = self._match_valid_url(url).group('show', 'season')
        season_info = self._download_json(
            f'https://10.com.au/api/shows/{show}/episodes/{season}', f'{show}/{season}')

        episodes_carousel = traverse_obj(season_info, (
            'content', 0, 'components', (
                lambda _, v: v['title'].lower() == 'episodes',
                (..., {dict}),
            )), get_all=False) or {}

        playlist_id = episodes_carousel['tpId']

        return self.playlist_from_matches(
            self._entries(urljoin(url, episodes_carousel['loadMoreUrl']), playlist_id),
            playlist_id, traverse_obj(season_info, ('content', 0, 'title', {str})),
            getter=urljoin(url))
