import base64
import datetime as dt
import hashlib
import hmac
import json
import os
import time
import uuid

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    js_to_json,
    jwt_decode_hs256,
    strip_or_none,
    unified_strdate,
    url_or_none,
)
from ..utils.traversal import require, traverse_obj


class TubiTvBaseIE(InfoExtractor):
    _GUEST_TOKEN_CACHE_KEY = 'guest_data'
    _SIGNED_HEADERS = 'content-type'
    _DEVICE_ID = None
    _VERFIER = None
    _API_BASE = 'https://account.production-public.tubi.io'
    _GUEST_TOKEN = None

    @property
    def _verifier(self):
        if not self._VERFIER:
            self._VERFIER = os.urandom(16).hex()
        return self._VERFIER

    def _device_id(self, jwt_token=None):
        if jwt_token:
            self._DEVICE_ID = jwt_decode_hs256(jwt_token)['device_id']
        if not self._DEVICE_ID:
            self._DEVICE_ID = str(uuid.uuid4())
        return self._DEVICE_ID

    @staticmethod
    def _hmac_sha256(key, data):
        return hmac.new(key, data, hashlib.sha256)

    @staticmethod
    def sha256_hex(x):
        if isinstance(x, dict):
            x = json.dumps(x)
        return hashlib.sha256(x.encode()).hexdigest()

    @staticmethod
    def _is_jwt_expired(jwt_token):
        return jwt_decode_hs256(jwt_token)['exp'] - time.time() < 300

    @staticmethod
    def _base_headers():
        return {
            'accept': '*/*',
            'content-type': 'application/json',
            'origin': 'https://tubitv.com',
            'referer': 'https://tubitv.com/',
        }

    # Source: https://md0.tubitv.com/web-k8s/dist/main.2e262c30.js
    def get_pub_data(self):
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(self._verifier.encode()).digest(),
        ).decode()
        return self._download_json(
            f'{self._API_BASE}/device/anonymous/signing_key', None, 'Downloading Signing data', data=json.dumps({
                'challenge': challenge,
                'device_id': self._device_id(),
                'platform': 'web',
                'version': '1.0.0',
            }).encode(),
            headers=self._base_headers(),
        )

    # Source: https://md0.tubitv.com/web-k8s/dist/main.2e262c30.js
    def _sign_params(self, payload, key, path):
        algo = 'TUBI-HMAC-SHA256'
        payload_hash = self.sha256_hex(payload)
        canonical_hash = self.sha256_hex(f'POST\n{path}\n\ncontent-type:application/json\n\n{self._SIGNED_HEADERS}\n{payload_hash}')
        ts = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        ket_data = b'TUBI' + base64.b64decode(key)
        signature = self._hmac_sha256(
            self._hmac_sha256(
                self._hmac_sha256(
                    ket_data, ts.split('T')[0].encode(),
                ).digest(), b'tubi_request',
            ).digest(), (f'{algo}\n{ts}\n{canonical_hash}').encode(),
        ).hexdigest()
        return {
            'X-Tubi-Algorithm': algo,
            'X-Tubi-Date': ts,
            'X-Tubi-Expires': 30,
            'X-Tubi-SignedHeaders': self._SIGNED_HEADERS,
            'X-Tubi-Signature': signature,
        }

    def handle_guest_data(self, data=None):
        if data:
            self._GUEST_TOKEN = data.get('access_token')
            if not self._GUEST_TOKEN:
                raise ExtractorError('Unable to get access token')
            self.cache.store('tubitv', self._GUEST_TOKEN_CACHE_KEY, self._GUEST_TOKEN)
            return self._GUEST_TOKEN
        return self.cache.load('tubitv', self._GUEST_TOKEN_CACHE_KEY)

    def get_guest_token(self):
        cached_access_token = self.handle_guest_data()
        if cached_access_token:
            if not self._is_jwt_expired(cached_access_token):
                self._GUEST_TOKEN = cached_access_token
                return self._GUEST_TOKEN

        signing_data = self.get_pub_data()
        signing_key = signing_data.get('key')
        _id = signing_data.get('id')
        if not (signing_key and _id):
            raise ExtractorError('Unable to get signing_data data')
        payload = {
            'device_id': self._device_id(),
            'id': _id,
            'platform': 'web',
            'verifier': self._verifier,
        }
        endpoint = '/device/anonymous/token'
        response = self._download_json(
            f'{self._API_BASE}{endpoint}',
            None,
            'Downloading guest data',
            query=self._sign_params(payload, signing_key, endpoint),
            data=json.dumps(payload).encode(),
            headers=self._base_headers(),
        )
        self.handle_guest_data(response)

    def _parse_metadata(self, video_id, data):
        formats = []
        drm_formats = False

        for resource in traverse_obj(data, ('video_resources', lambda _, v: url_or_none(v['manifest']['url']))) or []:
            resource_type = resource.get('type')
            manifest_url = resource['manifest']['url']
            if resource_type == 'dash':
                formats.extend(self._extract_mpd_formats(manifest_url, video_id, mpd_id=resource_type, fatal=False))
            elif resource_type in ('hlsv3', 'hlsv6'):
                fmts = self._extract_m3u8_formats(manifest_url, video_id, 'mp4', m3u8_id=resource_type, fatal=False)
                for fmt in fmts:
                    if 'Audio Description' in fmt.get('format_note', ''):
                        fmt['language_preference'] = -10
                formats.extend(fmts)
            elif resource_type in self._UNPLAYABLE_FORMATS:
                drm_formats = True
            else:
                self.report_warning(f'Skipping unknown resource type "{resource_type}"')

        if not formats and drm_formats:
            self.report_drm(video_id)
        elif not (formats or data.get('policy_match')):  # policy_match is False if content was removed
            raise ExtractorError('This content is currently unavailable', expected=True)

        subtitles = {}
        for sub in traverse_obj(data, ('subtitles', lambda _, v: url_or_none(v['url']))):
            subtitles.setdefault(sub.get('lang', 'English'), []).append({
                'url': self._proto_relative_url(sub['url']),
            })

        thumbnails = []
        for key in ('hero_images', 'thumbnails', 'hero_images'):
            thumbnails.extend({'url': thumb_url} for thumb_url in (data.get(key) or []))

        title = traverse_obj(data, ('title', {str}))
        season_number, episode_number, episode_title = self._search_regex(
            r'^S(\d+):E(\d+) - (.+)', title, 'episode info', fatal=False, group=(1, 2, 3), default=(None, None, None))

        return {
            'title': strip_or_none(title),
            'season_number': int_or_none(season_number),
            'episode_number': int_or_none(episode_number),
            'episode': strip_or_none(episode_title),
            'thumbnails': thumbnails,
            **traverse_obj(data, {
                'description': ('description', {str}),
                'duration': ('duration', {int_or_none}),
                'uploader_id': ('publisher_id', {str}),
                'release_year': ('year', {int_or_none}),
                'release_date': ('availability_starts', {unified_strdate}),
                'modified_date': ('updated_at', {unified_strdate}),
                'thumbnails': ('thumbnails', ..., {url_or_none}, {'url': {self._proto_relative_url}}),
            }),
            'subtitles': subtitles,
            'formats': formats,
        }

    def get_video_data_from_api(self, video_id):
        guest_token = self.get_guest_token()
        data = self._download_json(
            'https://content-cdn.production-public.tubi.io/api/v3/content', video_id, query={
                'app_id': 'tubitv',
                'platform': 'web',
                'content_id': video_id,
                'device_id': self._device_id(guest_token),
                'limit_resolutions[]': 'h264_1080p',
                'video_resources[]': 'hlsv6',
                'images[posterarts]': 'w408h583_poster',
            }, headers={
                **self._base_headers(),
                'Authorization': f'Bearer {guest_token}',
            },
        )

        return {
            'id': video_id,
            **self._parse_metadata(video_id, data),
        }


class TubiTvIE(TubiTvBaseIE):
    IE_NAME = 'tubitv'
    _VALID_URL = r'https?://(?:www\.)?tubitv\.com/(?:[a-z]{2}-[a-z]{2}/)?(?P<type>video|movies|tv-shows)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://tubitv.com/movies/100004539/the-39-steps',
        'info_dict': {
            'id': '100004539',
            'ext': 'mp4',
            'title': 'The 39 Steps',
            'description': 'md5:bb2f2dd337f0dc58c06cb509943f54c8',
            'uploader_id': 'abc2558d54505d4f0f32be94f2e7108c',
            'release_year': 1935,
            'thumbnail': r're:^https?://canvas-lb\.tubitv\.com/.+',
            'duration': 5187,
            'modified_date': '20260723',
            'release_date': '20230701',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://tubitv.com/tv-shows/554628/s01-e01-rise-of-the-snakes',
        'info_dict': {
            'id': '554628',
            'ext': 'mp4',
            'title': 'S01:E01 - Rise of the Snakes',
            'description': 'md5:ba136f586de53af0372811e783a3f57d',
            'episode': 'Rise of the Snakes',
            'episode_number': 1,
            'season': 'Season 1',
            'season_number': 1,
            'uploader_id': '2a9273e728c510d22aa5c57d0646810b',
            'release_year': 2011,
            'thumbnail': r're:^https?://canvas-lb\.tubitv\.com/.+',
            'duration': 1376,
            'modified_date': '20260922',
            'release_date': '20220613',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'http://tubitv.com/video/283829/the_comedian_at_the_friday',
        'md5': '43ac06be9326f41912dc64ccf7a80320',
        'info_dict': {
            'id': '283829',
            'ext': 'mp4',
            'title': 'The Comedian at The Friday',
            'description': 'A stand up comedian is forced to look at the decisions in his life while on a one week trip to the west coast.',
            'uploader_id': 'bc168bee0d18dd1cb3b86c68706ab434',
        },
        'skip': 'Content Unavailable',
    }, {
        'url': 'http://tubitv.com/tv-shows/321886/s01_e01_on_nom_stories',
        'only_matching': True,
    }, {
        'url': 'https://tubitv.com/movies/560057/penitentiary?start=true',
        'info_dict': {
            'id': '560057',
            'ext': 'mp4',
            'title': 'Penitentiary',
            'description': 'md5:8d2fc793a93cc1575ff426fdcb8dd3f9',
            'uploader_id': 'd8fed30d4f24fcb22ec294421b9defc2',
            'release_year': 1979,
        },
        'skip': 'Content Unavailable',
    }, {
        'url': 'https://tubitv.com/movies/100049199/cruel-intentions',
        'info_dict': {
            'id': '100049199',
            'ext': 'mp4',
            'title': 'Cruel Intentions',
            'description': 'md5:529c3dd0166a4435f46052f113f781f8',
            'uploader_id': '0c7e281b894a98de249c3bcf61c16e29',
            'duration': 5858,
            'thumbnail': r're:^https?://canvas-lb\.tubitv\.com/.+',
            'release_year': 1999,
            'modified_date': '20260929',
            'release_date': '20260901',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://tubitv.com/es-mx/tv-shows/477363/s01-e03-jacob-dos-dos-y-la-tarjets-de-hockey-robada',
        'only_matching': True,
    }]

    # DRM formats are included only to raise appropriate error
    _UNPLAYABLE_FORMATS = ('hlsv6_widevine', 'hlsv6_widevine_nonclearlead', 'hlsv6_playready_psshv0',
                           'hlsv6_fairplay', 'dash_widevine', 'dash_widevine_nonclearlead')

    def _real_extract(self, url):
        video_id, video_type = self._match_valid_url(url).group('id', 'type')
        webpage = self._download_webpage(
            f'https://tubitv.com/{video_type}/{video_id}/', video_id,
            headers=self.geo_verification_headers())
        video_data = self._search_json(
            r'window\.__data\s*=', webpage, 'data', video_id,
            transform_source=js_to_json)['video']['byId'].get(video_id)
        if not video_data:
            return self.get_video_data_from_api(video_id)

        return {
            'id': video_id,
            **self._parse_metadata(video_id, video_data),
        }


class TubiTvShowIE(InfoExtractor):
    IE_NAME = 'tubitv:series'
    _VALID_URL = r'https?://(?:www\.)?tubitv\.com/series/\d+/(?P<show_name>[^/?#]+)(?:/season-(?P<season>\d+))?'
    _TESTS = [{
        'url': 'https://tubitv.com/series/3936/the-joy-of-painting-with-bob-ross?start=true',
        'playlist_mincount': 389,
        'info_dict': {
            'id': 'the-joy-of-painting-with-bob-ross',
        },
    }, {
        'url': 'https://tubitv.com/series/300000435/the-saddle-club/season-1',
        'playlist_count': 26,
        'info_dict': {
            'id': 'the-saddle-club-season-1',
        },
    }, {
        'url': 'https://tubitv.com/series/300000435/the-saddle-club/season-2',
        'playlist_count': 26,
        'info_dict': {
            'id': 'the-saddle-club-season-2',
        },
    }, {
        'url': 'https://tubitv.com/series/300000435/the-saddle-club/',
        'playlist_mincount': 52,
        'info_dict': {
            'id': 'the-saddle-club',
        },
    }]

    def _entries(self, show_url, playlist_id, selected_season):
        webpage = self._download_webpage(show_url, playlist_id, headers=self.geo_verification_headers())

        react_query_state = self._search_json(
            r'window\.__REACT_QUERY_STATE__\s*=', webpage,
            'react query state', playlist_id, transform_source=js_to_json)
        data = traverse_obj(react_query_state, (
            'queries', lambda _, v: v['state']['data']['seasons'][0],
            'state', 'data', any, {require('season data')}))

        # v['number'] is already a decimal string, but stringify to protect against API changes
        path = [lambda _, v: str(v['number']) == selected_season] if selected_season else [..., {dict}]

        for season in traverse_obj(data, ('seasons', *path)):
            season_number = int_or_none(season.get('number'))
            for episode in traverse_obj(season, ('episodes', lambda _, v: v['id'])):
                episode_id = episode['id']
                yield self.url_result(
                    f'https://tubitv.com/tv-shows/{episode_id}/', TubiTvIE, episode_id,
                    season_number=season_number, episode_number=int_or_none(episode.get('num')))

    def _real_extract(self, url):
        playlist_id, selected_season = self._match_valid_url(url).group('show_name', 'season')
        if selected_season:
            playlist_id = f'{playlist_id}-season-{selected_season}'
        return self.playlist_result(self._entries(url, playlist_id, selected_season), playlist_id)
