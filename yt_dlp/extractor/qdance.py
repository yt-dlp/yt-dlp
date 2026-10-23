import json
import time

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    jwt_decode_hs256,
    str_or_none,
    traverse_obj,
    try_call,
    url_or_none,
)


class QDanceIE(InfoExtractor):
    _NETRC_MACHINE = 'qdance'
    _VALID_URL = r'https?://(?:www\.)?q-dance\.com/network/(?:library|live)/(?P<id>[\w-]+)'
    _TESTS = [{
        'note': 'vod',
        'url': 'https://www.q-dance.com/network/library/146542138',
        'info_dict': {
            'id': '146542138',
            'ext': 'mp4',
            'title': 'Sound Rush [LIVE] | Defqon.1 Weekend Festival 2022 | Friday | RED',
            'display_id': 'sound-rush-live-v3-defqon-1-weekend-festival-2022-friday-red',
            'description': 'Relive Defqon.1 - Primal Energy 2022 with the sounds of Sound Rush LIVE at the RED on Friday! 🔥',
            'season': 'Defqon.1 Weekend Festival 2022',
            'season_id': '31840632',
            'series': 'Defqon.1',
            'series_id': '31840378',
            'thumbnail': 'https://images.q-dance.network/1674829540-20220624171509-220624171509_delio_dn201093-2.jpg',
            'availability': 'premium_only',
            'duration': 1829,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'note': 'livestream',
        'url': 'https://www.q-dance.com/network/live/149170353',
        'info_dict': {
            'id': '149170353',
            'ext': 'mp4',
            'title': r're:^Defqon\.1 2023 - Friday - RED',
            'display_id': 'defqon-1-2023-friday-red',
            'description': 'md5:3c73fbbd4044e578e696adfc64019163',
            'season': 'Defqon.1 Weekend Festival 2023',
            'season_id': '141735599',
            'series': 'Defqon.1',
            'series_id': '31840378',
            'thumbnail': 'https://images.q-dance.network/1686849069-area-thumbs_red.png',
            'availability': 'subscriber_only',
            'live_status': 'is_live',
            'channel_id': 'qdancenetwork.video_149170353',
        },
        'skip': 'Completed livestream',
    }, {
        'note': 'vod with alphanumeric id',
        'url': 'https://www.q-dance.com/network/library/WhDleSIWSfeT3Q9ObBKBeA',
        'info_dict': {
            'id': 'WhDleSIWSfeT3Q9ObBKBeA',
            'ext': 'mp4',
            'title': 'Aftershock I Defqon.1 Weekend Festival 2023 I Sunday I BLUE',
            'display_id': 'naam-i-defqon-1-weekend-festival-2023-i-dag-i-podium',
            'description': 'Relive Defqon.1 Path of the Warrior with Aftershock at the BLUE 🔥',
            'series': 'Defqon.1',
            'series_id': '31840378',
            'season': 'Defqon.1 Weekend Festival 2023',
            'season_id': '141735599',
            'duration': 3507,
            'availability': 'premium_only',
            'thumbnail': 'https://images.q-dance.network/1698158361-230625-135716-defqon-1-aftershock.jpg',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.q-dance.com/network/library/-uRFKXwmRZGVnve7av9uqA',
        'only_matching': True,
    }]

    _access_token = None
    _refresh_token = None

    def _call_login_api(self, data, note='Logging in'):
        login = self._download_json(
            'https://members.id-t.com/api/auth/login', None, note, headers={
                'content-type': 'application/json',
                'brand': 'qdance',
                'origin': 'https://www.q-dance.com',
                'referer': 'https://www.q-dance.com/',
            }, data=json.dumps(data, separators=(',', ':')).encode(),
            expected_status=lambda x: True)

        tokens = traverse_obj(login, ('data', {
            '_id-t-accounts-token': ('accessToken', {str}),
            '_id-t-accounts-refresh': ('refreshToken', {str}),
            '_id-t-accounts-id-token': ('idToken', {str}),
        }))

        if not tokens.get('_id-t-accounts-token'):
            error = ': '.join(traverse_obj(login, ('error', ('code', 'message'), {str})))
            if 'validation_error' not in error:
                raise ExtractorError(f'Q-Dance API said "{error}"')
            msg = 'Invalid username or password' if 'email' in data else 'Refresh token has expired'
            raise ExtractorError(msg, expected=True)

        for name, value in tokens.items():
            self._set_cookie('.q-dance.com', name, value)

    def _perform_login(self, username, password):
        self._call_login_api({'email': username, 'password': password})

    def _real_initialize(self):
        cookies = self._get_cookies('https://www.q-dance.com/')
        self._refresh_token = try_call(lambda: cookies['_id-t-accounts-refresh'].value)
        self._access_token = try_call(lambda: cookies['_id-t-accounts-token'].value)
        if not self._access_token:
            self.raise_login_required()

    def _get_auth(self):
        if (try_call(lambda: jwt_decode_hs256(self._access_token)['exp']) or 0) <= int(time.time() - 120):
            if not self._refresh_token:
                raise ExtractorError(
                    'Cannot refresh access token, login with yt-dlp or refresh cookies in browser')
            self._call_login_api({'refreshToken': self._refresh_token}, note='Refreshing access token')
            self._real_initialize()

        return {'Authorization': self._access_token}

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        data = self._search_nuxt_data(webpage, video_id, traverse=('data', 0, 'data'))

        def extract_availability(level):
            level = int_or_none(level) or 0
            return self._availability(
                needs_premium=(level >= 20), needs_subscription=(level >= 15), needs_auth=True)

        info = traverse_obj(data, {
            'title': ('title', {str.strip}),
            'description': ('description', {str.strip}),
            'display_id': ('slug', {str}),
            'thumbnail': ('thumbnail', {url_or_none}),
            'duration': ('durationInSeconds', {int_or_none}, filter),
            'availability': ('subscription', 'level', {extract_availability}),
            'is_live': ('type', {lambda x: x.lower() == 'live'}),
            'artist': ('acts', ..., {str}),
            'series': ('event', 'title', {str.strip}),
            'series_id': ('event', 'id', {str_or_none}),
            'season': ('eventEdition', 'title', {str.strip}),
            'season_id': ('eventEdition', 'id', {str_or_none}),
            'channel_id': ('pubnub', 'channelName', {str}),
        })

        stream = self._download_json(
            f'https://dc9h6qmsoymbq.cloudfront.net/api/content/videos/{video_id}/url',
            video_id, headers=self._get_auth(), expected_status=401)

        m3u8_url = traverse_obj(stream, ('data', 'url', {url_or_none}))
        if not m3u8_url and traverse_obj(stream, ('error', 'code')) == 'unauthorized':
            raise ExtractorError('Your account does not have access to this content', expected=True)

        formats = self._extract_m3u8_formats(
            m3u8_url, video_id, fatal=False, live=True) if m3u8_url else []
        if not formats:
            self.raise_no_formats('No active streams found', expected=bool(info.get('is_live')))

        return {
            **info,
            'id': video_id,
            'formats': formats,
        }
