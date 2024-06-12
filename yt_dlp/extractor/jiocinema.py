import base64
import itertools
import json
import random
import re
import string
import time

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    jwt_decode_hs256,
    parse_age_limit,
    try_call,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class JioCinemaBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'jiocinema'
    _GEO_BYPASS = False
    _ACCESS_TOKEN = None
    _REFRESH_TOKEN = None
    _GUEST_TOKEN = None
    _USER_ID = None
    _DEVICE_ID = None
    _API_HEADERS = {'Origin': 'https://www.jiocinema.com', 'Referer': 'https://www.jiocinema.com/'}
    _APP_NAME = {'appName': 'RJIL_JioCinema'}
    _APP_VERSION = {'appVersion': '5.0.0'}
    _API_SIGNATURES = 'o668nxgzwff'
    _METADATA_API_BASE = 'https://content-jiovoot.voot.com/psapi'
    _ACCESS_HINT = 'the `accessToken` from your browser local storage'
    _LOGIN_HINT = (
        'Log in with "-u phone -p <PHONE_NUMBER>" to authenticate with OTP, '
        f'or use "-u token -p <ACCESS_TOKEN>" to log in with {_ACCESS_HINT}. '
        'If you have previously logged in with yt-dlp and your session '
        'has been cached, you can use "-u device -p <DEVICE_ID>"')

    def _cache_token(self, token_type):
        assert token_type in ('access', 'refresh', 'all')
        if token_type in ('access', 'all'):
            self.cache.store(
                JioCinemaBaseIE._NETRC_MACHINE, f'{JioCinemaBaseIE._DEVICE_ID}-access', JioCinemaBaseIE._ACCESS_TOKEN)
        if token_type in ('refresh', 'all'):
            self.cache.store(
                JioCinemaBaseIE._NETRC_MACHINE, f'{JioCinemaBaseIE._DEVICE_ID}-refresh', JioCinemaBaseIE._REFRESH_TOKEN)

    def _call_api(self, url, video_id, note='Downloading API JSON', headers={}, data={}):
        return self._download_json(
            url, video_id, note, data=json.dumps(data, separators=(',', ':')).encode(), headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                **self._API_HEADERS,
                **headers,
            }, expected_status=(400, 403, 474))

    def _call_auth_api(self, service, endpoint, note, headers={}, data={}):
        return self._call_api(
            f'https://auth-jiocinema.voot.com/{service}service/apis/v4/{endpoint}',
            None, note=note, headers=headers, data=data)

    def _refresh_token(self):
        if not JioCinemaBaseIE._REFRESH_TOKEN or not JioCinemaBaseIE._DEVICE_ID:
            raise ExtractorError('User token has expired', expected=True)
        response = self._call_auth_api(
            'token', 'refreshtoken', 'Refreshing token',
            headers={'accesstoken': self._ACCESS_TOKEN}, data={
                **self._APP_NAME,
                'deviceId': self._DEVICE_ID,
                'refreshToken': self._REFRESH_TOKEN,
                **self._APP_VERSION,
            })
        refresh_token = response.get('refreshTokenId')
        if refresh_token and refresh_token != JioCinemaBaseIE._REFRESH_TOKEN:
            JioCinemaBaseIE._REFRESH_TOKEN = refresh_token
            self._cache_token('refresh')
        JioCinemaBaseIE._ACCESS_TOKEN = response['authToken']
        self._cache_token('access')

    def _fetch_guest_token(self):
        JioCinemaBaseIE._DEVICE_ID = ''.join(random.choices(string.digits, k=10))
        guest_token = self._call_auth_api(
            'token', 'guest', 'Downloading guest token', data={
                **self._APP_NAME,
                'deviceType': 'phone',
                'os': 'ios',
                'deviceId': self._DEVICE_ID,
                'freshLaunch': False,
                'adId': self._DEVICE_ID,
                **self._APP_VERSION,
            })
        self._GUEST_TOKEN = guest_token['authToken']
        self._USER_ID = guest_token['userId']

    def _call_login_api(self, endpoint, guest_token, data, note):
        return self._call_auth_api(
            'user', f'loginotp/{endpoint}', note, headers={
                **self.geo_verification_headers(),
                'accesstoken': self._GUEST_TOKEN,
                **self._APP_NAME,
                **traverse_obj(guest_token, 'data', {
                    'deviceType': ('deviceType', {str}),
                    'os': ('os', {str}),
                })}, data=data)

    def _is_token_expired(self, token):
        return (try_call(lambda: jwt_decode_hs256(token)['exp']) or 0) <= int(time.time() - 180)

    def _perform_login(self, username, password):
        if self._ACCESS_TOKEN and not self._is_token_expired(self._ACCESS_TOKEN):
            return

        UUID_RE = r'[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12}'

        if username.lower() == 'token':
            if try_call(lambda: jwt_decode_hs256(password)):
                JioCinemaBaseIE._ACCESS_TOKEN = password
                refresh_hint = 'the `refreshToken` UUID from your browser local storage'
                refresh_token = self._configuration_arg('refresh_token', [''], ie_key=JioCinemaIE)[0]
                if not refresh_token:
                    self.to_screen(
                        'To extend the life of your login session, in addition to your access token, '
                        'you can pass --extractor-args "jiocinema:refresh_token=REFRESH_TOKEN" '
                        f'where REFRESH_TOKEN is {refresh_hint}')
                elif re.fullmatch(UUID_RE, refresh_token):
                    JioCinemaBaseIE._REFRESH_TOKEN = refresh_token
                else:
                    self.report_warning(f'Invalid refresh_token value. Use {refresh_hint}')
            else:
                raise ExtractorError(
                    f'The password given could not be decoded as a token; use {self._ACCESS_HINT}', expected=True)

        elif username.lower() == 'device' and re.fullmatch(rf'(?:{UUID_RE}|\d+)', password):
            JioCinemaBaseIE._REFRESH_TOKEN = self.cache.load(JioCinemaBaseIE._NETRC_MACHINE, f'{password}-refresh')
            JioCinemaBaseIE._ACCESS_TOKEN = self.cache.load(JioCinemaBaseIE._NETRC_MACHINE, f'{password}-access')
            if not JioCinemaBaseIE._REFRESH_TOKEN or not JioCinemaBaseIE._ACCESS_TOKEN:
                raise ExtractorError(f'Failed to load cached tokens for device ID "{password}"', expected=True)

        elif username.lower() == 'phone' and re.fullmatch(r'\+?\d+', password):
            self._fetch_guest_token()
            guest_token = jwt_decode_hs256(self._GUEST_TOKEN)
            initial_data = {
                'number': base64.b64encode(password.encode()).decode(),
                **self._APP_VERSION,
            }
            response = self._call_login_api('send', guest_token, initial_data, 'Requesting OTP')
            if not traverse_obj(response, ('OTPInfo', {dict})):
                raise ExtractorError('There was a problem with the phone number login attempt')

            is_iphone = guest_token.get('os') == 'ios'
            response = self._call_login_api('verify', guest_token, {
                'deviceInfo': {
                    'consumptionDeviceName': 'iPhone' if is_iphone else 'Android',
                    'info': {
                        'platform': {'name': 'iPhone OS' if is_iphone else 'Android'},
                        'androidId': self._DEVICE_ID,
                        'type': 'iOS' if is_iphone else 'Android',
                    },
                },
                **initial_data,
                'otp': self._get_tfa_info('the one-time password sent to your phone'),
            }, 'Submitting OTP')
            if traverse_obj(response, 'code') == 1043:
                raise ExtractorError('Wrong OTP', expected=True)
            JioCinemaBaseIE._REFRESH_TOKEN = response['refreshToken']
            JioCinemaBaseIE._ACCESS_TOKEN = response['authToken']

        else:
            raise ExtractorError(self._LOGIN_HINT, expected=True)

        user_token = jwt_decode_hs256(JioCinemaBaseIE._ACCESS_TOKEN)['data']
        JioCinemaBaseIE._USER_ID = user_token['userId']
        JioCinemaBaseIE._DEVICE_ID = user_token['deviceId']
        if JioCinemaBaseIE._REFRESH_TOKEN and username != 'device':
            self._cache_token('all')
            if self.get_param('cachedir') is not False:
                self.to_screen(
                    f'NOTE: For subsequent logins you can use "-u device -p {JioCinemaBaseIE._DEVICE_ID}"')
        elif not JioCinemaBaseIE._REFRESH_TOKEN:
            JioCinemaBaseIE._REFRESH_TOKEN = self.cache.load(
                JioCinemaBaseIE._NETRC_MACHINE, f'{JioCinemaBaseIE._DEVICE_ID}-refresh')
            if JioCinemaBaseIE._REFRESH_TOKEN:
                self._cache_token('access')
        self.to_screen(f'Logging in as device ID "{JioCinemaBaseIE._DEVICE_ID}"')
        if self._is_token_expired(JioCinemaBaseIE._ACCESS_TOKEN):
            self._refresh_token()


class JioCinemaIE(JioCinemaBaseIE):
    IE_NAME = 'jiocinema'
    _VALID_URL = r'https?://(?:www\.)?jiocinema\.com/?(?:movies?/[^/?#]+/|tv-shows/(?:[^/?#]+/){3})(?P<id>\d{3,})'
    _TESTS = [{
        'url': 'https://www.jiocinema.com/tv-shows/agnisakshi-ek-samjhauta/1/pradeep-to-stop-the-wedding/3759931',
        'info_dict': {
            'id': '3759931',
            'ext': 'mp4',
            'title': 'Pradeep to stop the wedding?',
            'description': 'md5:75f72d1d1a66976633345a3de6d672b1',
            'episode': 'Pradeep to stop the wedding?',
            'episode_number': 89,
            'season': 'Agnisakshi…Ek Samjhauta-S1',
            'season_number': 1,
            'series': 'Agnisakshi Ek Samjhauta',
            'duration': 1238.0,
            'thumbnail': r're:https?://.+\.jpg',
            'age_limit': 13,
            'season_id': '3698031',
            'upload_date': '20230606',
            'timestamp': 1686009600,
            'release_date': '20230607',
            'genres': ['Drama'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.jiocinema.com/movies/bhediya/3754021/watch',
        'info_dict': {
            'id': '3754021',
            'ext': 'mp4',
            'title': 'Bhediya',
            'description': 'md5:a6bf2900371ac2fc3f1447401a9f7bb0',
            'episode': 'Bhediya',
            'duration': 8500.0,
            'thumbnail': r're:https?://.+\.jpg',
            'age_limit': 13,
            'upload_date': '20230525',
            'timestamp': 1685026200,
            'release_date': '20230524',
            'genres': ['Comedy'],
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _extract_formats_and_subtitles(self, playback, video_id):
        m3u8_url = traverse_obj(playback, (
            'data', 'playbackUrls', lambda _, v: v['streamtype'] == 'hls', 'url', {url_or_none}, any))
        if not m3u8_url:  # DRM-only content only serves dash urls
            self.report_drm(video_id)
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(m3u8_url, video_id, m3u8_id='hls')
        self._remove_duplicate_formats(formats)

        return {
            # '/_definst_/smil:vod/' m3u8 manifests claim to have 720p+ formats but max out at 480p
            'formats': traverse_obj(formats, (
                lambda _, v: '/_definst_/smil:vod/' not in v['url'] or v['height'] <= 480)),
            'subtitles': subtitles,
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        if not self._ACCESS_TOKEN and self._is_token_expired(self._GUEST_TOKEN):
            self._fetch_guest_token()
        elif self._ACCESS_TOKEN and self._is_token_expired(self._ACCESS_TOKEN):
            self._refresh_token()

        playback = self._call_api(
            f'https://apis-jiovoot.voot.com/playbackjv/v3/{video_id}', video_id,
            'Downloading playback JSON', headers={
                **self.geo_verification_headers(),
                'accesstoken': self._ACCESS_TOKEN or self._GUEST_TOKEN,
                **self._APP_NAME,
                'deviceid': self._DEVICE_ID,
                'uniqueid': self._USER_ID,
                'x-apisignatures': self._API_SIGNATURES,
                'x-platform': 'androidweb',
                'x-platform-token': 'web',
            }, data={
                '4k': False,
                'ageGroup': '18+',
                'appVersion': '3.4.0',
                'bitrateProfile': 'xhdpi',
                'capability': {
                    'drmCapability': {
                        'aesSupport': 'yes',
                        'fairPlayDrmSupport': 'none',
                        'playreadyDrmSupport': 'none',
                        'widevineDRMSupport': 'none',
                    },
                    'frameRateCapability': [{
                        'frameRateSupport': '30fps',
                        'videoQuality': '1440p',
                    }],
                },
                'continueWatchingRequired': False,
                'dolby': False,
                'downloadRequest': False,
                'hevc': False,
                'kidsSafe': False,
                'manufacturer': 'Windows',
                'model': 'Windows',
                'multiAudioRequired': True,
                'osVersion': '10',
                'parentalPinValid': True,
                'x-apisignatures': self._API_SIGNATURES,
            })

        status_code = traverse_obj(playback, ('code', {int}))
        if status_code == 474:
            self.raise_geo_restricted(countries=['IN'])
        elif status_code == 1008:
            error_msg = 'This content is only available for premium users'
            if self._ACCESS_TOKEN:
                raise ExtractorError(error_msg, expected=True)
            self.raise_login_required(f'{error_msg}. {self._LOGIN_HINT}', method=None)
        elif status_code == 400:
            raise ExtractorError('The requested content is not available', expected=True)
        elif status_code is not None and status_code != 200:
            raise ExtractorError(
                f'JioCinema says: {traverse_obj(playback, ("message", {str})) or status_code}')

        metadata = self._download_json(
            f'{self._METADATA_API_BASE}/voot/v1/voot-web/content/query/asset-details',
            video_id, fatal=False, query={
                'ids': f'include:{video_id}',
                'responseType': 'common',
                'devicePlatformType': 'desktop',
            })

        return {
            'id': video_id,
            'http_headers': self._API_HEADERS,
            **self._extract_formats_and_subtitles(playback, video_id),
            **traverse_obj(playback, ('data', {
                # fallback metadata
                'title': ('name', {str}),
                'description': ('fullSynopsis', {str}),
                'series': ('show', 'name', {str}, {lambda x: x or None}),
                'season': ('tournamentName', {str}, {lambda x: x if x != 'Season 0' else None}),
                'season_number': ('episode', 'season', {int_or_none}, {lambda x: x or None}),
                'episode': ('fullTitle', {str}),
                'episode_number': ('episode', 'episodeNo', {int_or_none}, {lambda x: x or None}),
                'age_limit': ('ageNemonic', {parse_age_limit}),
                'duration': ('totalDuration', {float_or_none}),
                'thumbnail': ('images', {url_or_none}),
            })),
            **traverse_obj(metadata, ('result', 0, {
                'title': ('fullTitle', {str}),
                'description': ('fullSynopsis', {str}),
                'series': ('showName', {str}, {lambda x: x or None}),
                'season': ('seasonName', {str}, {lambda x: x or None}),
                'season_number': ('season', {int_or_none}),
                'season_id': ('seasonId', {str}, {lambda x: x or None}),
                'episode': ('fullTitle', {str}),
                'episode_number': ('episode', {int_or_none}),
                'timestamp': ('uploadTime', {int_or_none}),
                'release_date': ('telecastDate', {str}),
                'age_limit': ('ageNemonic', {parse_age_limit}),
                'duration': ('duration', {float_or_none}),
                'genres': ('genres', ..., {str}),
                'thumbnail': ('seo', 'ogImage', {url_or_none}),
            })),
        }


class JioCinemaSeriesIE(JioCinemaBaseIE):
    IE_NAME = 'jiocinema:series'
    _VALID_URL = r'https?://(?:www\.)?jiocinema\.com/tv-shows/(?P<slug>[\w-]+)/(?P<id>\d{3,})'
    _TESTS = [{
        'url': 'https://www.jiocinema.com/tv-shows/naagin/3499917',
        'info_dict': {
            'id': '3499917',
            'title': 'naagin',
        },
        'playlist_mincount': 120,
    }]

    def _entries(self, series_id):
        seasons = self._download_json(
            f'{self._METADATA_API_BASE}/voot/v1/voot-web/content/generic/season-by-show', series_id,
            'Downloading series metadata JSON', query={
                'sort': 'season:asc',
                'id': series_id,
                'responseType': 'common',
            })

        for season_num, season in enumerate(traverse_obj(seasons, ('result', lambda _, v: v['id'])), 1):
            season_id = season['id']
            label = season.get('season') or season_num
            for page_num in itertools.count(1):
                episodes = traverse_obj(self._download_json(
                    f'{self._METADATA_API_BASE}/voot/v1/voot-web/content/generic/series-wise-episode',
                    season_id, f'Downloading season {label} page {page_num} JSON', query={
                        'sort': 'episode:asc',
                        'id': season_id,
                        'responseType': 'common',
                        'page': page_num,
                    }), ('result', lambda _, v: v['id'] and url_or_none(v['slug'])))
                if not episodes:
                    break
                for episode in episodes:
                    yield self.url_result(
                        episode['slug'], JioCinemaIE, **traverse_obj(episode, {
                            'video_id': 'id',
                            'video_title': ('fullTitle', {str}),
                            'season_number': ('season', {int_or_none}),
                            'episode_number': ('episode', {int_or_none}),
                        }))

    def _real_extract(self, url):
        slug, series_id = self._match_valid_url(url).group('slug', 'id')
        return self.playlist_result(self._entries(series_id), series_id, slug)
