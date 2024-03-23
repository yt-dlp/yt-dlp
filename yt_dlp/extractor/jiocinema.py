import base64
import itertools
import json
import random
import re
import string
import time

from .common import InfoExtractor
from ..utils import (
    str_or_none,
    ExtractorError,
    float_or_none,
    int_or_none,
    jwt_decode_hs256,
    parse_age_limit,
    traverse_obj,
    try_call,
    url_or_none,
)


class JioBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'JioCinema'
    _GEO_BYPASS = False
    _LOGIN_HINT = 'Log in with "-u <phone>" to authenticate with OTP, or use "-u token -p <accessToken>" to login with token.'
    _ACCESS_TOKEN = None
    _REFRESH_TOKEN = None
    _GUEST_TOKEN = None
    _USER_ID = None
    _DEVICE_ID = None
    _API_HEADERS = {'Origin': 'https://www.jiocinema.com', 'Referer': 'https://www.jiocinema.com/'}
    _APP_NAME = {'appName': 'RJIL_JioCinema'}
    _APP_VERSION = {'appVersion': '5.0.0'}
    _API_SIGNATURES = 'o668nxgzwff'

    _TAG_FIELDS = {
        'language': 'language',
        'acodec': 'audio_codec',
        'vcodec': 'video_codec',
    }

    def _cache_token(self, token_type):
        if token_type in ('access', 'all'):
            self.cache.store(
                JioBaseIE._NETRC_MACHINE, f'{JioBaseIE._DEVICE_ID}-access', JioBaseIE._ACCESS_TOKEN)
        if token_type in ('refresh', 'all'):
            self.cache.store(
                JioBaseIE._NETRC_MACHINE, f'{JioBaseIE._DEVICE_ID}-refresh', JioBaseIE._REFRESH_TOKEN)

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
        if not JioBaseIE._REFRESH_TOKEN or not JioBaseIE._DEVICE_ID:
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
        if refresh_token and refresh_token != JioBaseIE._REFRESH_TOKEN:
            JioBaseIE._REFRESH_TOKEN = refresh_token
            self._cache_token('refresh')
        JioBaseIE._ACCESS_TOKEN = response['authToken']
        self._cache_token('access')

    def _fetch_guest_token(self):
        JioBaseIE._DEVICE_ID = ''.join(random.choices(string.digits, k=10))
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

        if username.lower() == 'token':
            if try_call(lambda: jwt_decode_hs256(password)):
                JioBaseIE._ACCESS_TOKEN = password
                refresh_token = self._configuration_arg('refresh_token', [''], ie_key=JioCinemaIE)[0]
                if re.fullmatch(r'[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12}', refresh_token):
                    JioBaseIE._REFRESH_TOKEN = refresh_token
                elif refresh_token:
                    self.report_warning(
                        'Invalid refresh_token value. Use the "refreshToken" UUID from browser local storage')

        elif username.lower() == 'device' and password.isdigit():
            JioBaseIE._REFRESH_TOKEN = self.cache.load(JioBaseIE._NETRC_MACHINE, f'{password}-refresh')
            JioBaseIE._ACCESS_TOKEN = self.cache.load(JioBaseIE._NETRC_MACHINE, f'{password}-access')
            if not JioBaseIE._REFRESH_TOKEN or not JioBaseIE._ACCESS_TOKEN:
                raise ExtractorError(f'Failed to load cached tokens for ID "{password}"', expected=True)

        elif re.fullmatch(r'\+?\d+', username):
            self._fetch_guest_token()
            guest_token = jwt_decode_hs256(self._GUEST_TOKEN)
            initial_data = {
                'number': f'{base64.b64encode(username.encode())}',
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
                        'type': 'iOS' if is_iphone else 'Android'
                    }
                },
                **initial_data,
                'otp': self._get_tfa_info('the one-time password sent to your phone')
            }, 'Submitting OTP')
            if traverse_obj(response, 'code') == 1043:
                raise ExtractorError('Wrong OTP', expected=True)
            JioBaseIE._REFRESH_TOKEN = response['refreshToken']
            JioBaseIE._ACCESS_TOKEN = response['authToken']

        else:
            raise ExtractorError(self._LOGIN_HINT, expected=True)

        user_token = jwt_decode_hs256(JioBaseIE._ACCESS_TOKEN)['data']
        JioBaseIE._USER_ID = user_token['userId']
        JioBaseIE._DEVICE_ID = user_token['deviceId']
        if JioBaseIE._REFRESH_TOKEN and username != 'device':
            self._cache_token('all')
        elif not JioBaseIE._REFRESH_TOKEN:
            JioBaseIE._REFRESH_TOKEN = self.cache.load(
                JioBaseIE._NETRC_MACHINE, f'{JioBaseIE._DEVICE_ID}-refresh')
            if JioBaseIE._REFRESH_TOKEN:
                self._cache_token('access')
        self.to_screen(f'Logging in as device {JioBaseIE._DEVICE_ID}')
        if self._is_token_expired(JioBaseIE._ACCESS_TOKEN):
            self._refresh_token()

    def _extract_formats_and_subtitles(self, m3u8_url, video_id):
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(m3u8_url, video_id, m3u8_id='hls')
        self._remove_duplicate_formats(formats)

        return {
            # '/_definst_/smil:vod/' m3u8 manifests claim to have 720p+ formats but max out at 480p
            'formats': traverse_obj(formats, (
                lambda _, v: '/_definst_/smil:vod/' not in v['url'] or v['height'] <= 480)),
            'subtitles': subtitles,
            'http_headers': self._API_HEADERS,
        }


class JioCinemaIE(JioBaseIE):
    _VALID_URL = r'''(?x)
                    (?:
                        https?://(?:www\.)?jiocinema\.com/?
                        (?:
                            movies?/[^/]+/|
                            tv-shows/(?:[^/]+/){3}
                        )
                     )
                    (?P<id>\d{3,})
                    '''
    _TESTS = [{
        'url': 'https://www.jiocinema.com/tv-shows/agnisakshi-ek-samjhauta/1/pradeep-to-stop-the-wedding/3759931',
        'info_dict': {
            'id': '3759931',
            'ext': 'mp4',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.jiocinema.com/movies/bhediya/3754021/watch',
        'info_dict': {
            'id': '3754021',
            'ext': 'mp4',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        formats, subs = [], {}
        if not self._ACCESS_TOKEN and self._is_token_expired(self._GUEST_TOKEN):
            self._fetch_guest_token()
        elif self._ACCESS_TOKEN and self._is_token_expired(self._ACCESS_TOKEN):
            self._refresh_token()

        meta = 'https://content-jiovoot.voot.com/psapi/voot/v1/voot-web/content/query/asset-details?&ids=include:{video_id}&responseType=common&devicePlatformType=desktop'
        meta_formate = meta.format(video_id=video_id)
        video_data = self._download_json(meta_formate, None, 'Fetching Metadata')

        playback = self._call_api(
            f'https://apis-jiovoot.voot.com/playbackjv/v5/{video_id}', video_id,
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
                '4k': True,
                'ageGroup': '18+',
                'appVersion': '3.4.0',
                'bitrateProfile': 'xhdpi',
                'capability': {
                    'drmCapability': {
                        'aesSupport': 'yes',
                        'fairPlayDrmSupport': 'none',
                        'playreadyDrmSupport': 'none',
                        'widevineDRMSupport': 'none'
                    },
                    'frameRateCapability': [{
                        'frameRateSupport': '30fps',
                        'videoQuality': '1440p'
                    }]
                },
                'continueWatchingRequired': False,
                'dolby': True,
                'downloadRequest': False,
                'hevc': True,
                'kidsSafe': False,
                'manufacturer': 'Windows',
                'model': 'Windows',
                'multiAudioRequired': True,
                'osVersion': '10',
                'parentalPinValid': True
            })['data']['playbackUrls']

        current_formats, current_subs = [], {}
        for url_data in playback:
            if not self.get_param('allow_unplayable_formats') and url_data.get('encryption'):
                self.report_drm(video_id)
            format_url = url_or_none(url_data.get('url'))
            if not format_url:
                continue
            if url_data['streamtype'] == 'dash':
                current_formats, current_subs = self._extract_mpd_formats_and_subtitles(format_url, video_id, headers=self._API_HEADERS)
            elif url_data['streamtype'] == 'hls':
                current_formats, current_subs = self._extract_m3u8_formats_and_subtitles(format_url, video_id, ext='mp4', m3u8_id='hls', headers=self._API_HEADERS)

            formats.extend(current_formats)
            subs = self._merge_subtitles(subs, current_subs)
        return {
            'id': video_id,
            'formats': formats,
            **traverse_obj(video_data, ('result', 0, {
                'title': ('name', {str}),
                'description': ('fullSynopsis', {str}),
                'series': ('showName', {str}),
                'season': ('seasonName', {str}),
                'season_number': ('season', {int_or_none}),
                'season_id': ('seasonId', {int_or_none}),
                'episode': ('fullTitle', {str}),
                'episode_number': ('episode', {int_or_none}),
                'timestamp': ('uploadTime', {int_or_none}),
                'release_date': ('telecastDate', {int_or_none}),
                'release_year': ('releaseYear', {int_or_none}),
                'age_limit': ('ageNemonic', {parse_age_limit}),
                'duration': ('totalDuration', {float_or_none}),
                'parentalRating': ('ageNumeric', {int_or_none}),
                'languages': ('languages'),
                'genre': ('genres', {str_or_none}),
                'thumbnail': ('seo', 'ogImage', {str})
            })),
        }


class JioVootSeriesBaseIE(JioBaseIE):
    def _entries(self, series_id):
        seasons = self._download_json(
            f'{self._SERIES_API_BASE}/voot/v1/voot-web/content/generic/season-by-show', series_id,
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
                    f'{self._SERIES_API_BASE}/voot/v1/voot-web/content/generic/series-wise-episode',
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
                        episode['slug'], self._RESULT_IE, **traverse_obj(episode, {
                            'video_id': 'id',
                            'video_title': ('fullTitle', {str}),
                            'season_number': ('season', {int_or_none}),
                            'episode_number': ('episode', {int_or_none}),
                        }))

    def _real_extract(self, url):
        slug, series_id = self._match_valid_url(url).group('slug', 'id')
        return self.playlist_result(self._entries(series_id), series_id, slug)


class JioVootSeriesIE(JioVootSeriesBaseIE):
    _VALID_URL = r'https?://(?:www\.)?jiocinema\.com/tv-shows/(?P<slug>[\w-]+)/(?P<id>\d{3,})'
    _TESTS = [{
        'url': 'https://www.jiocinema.com/tv-shows/naagin/3499917',
        'info_dict': {
            'id': '3499917',
            'title': 'naagin',
        },
        'playlist_mincount': 120,
    }]
    _SERIES_API_BASE = 'https://content-jiovoot.voot.com/psapi'
    _RESULT_IE = JioCinemaIE
