from .brightcove import BrightcoveNewIE
from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    random_uuidv4,
    smuggle_url,
    time_seconds,
)


class RevryIE(InfoExtractor):
    _VALID_URL = r'https?://watch\.revry\.tv/player/(?P<id>[0-9]+)'
    _GEO_COUNTRIES = ['US']
    _TESTS = [{
        'url': 'https://watch.revry.tv/player/43772/stream?assetType=episodes',
        'info_dict': {
            'id': '6368611770112',
            'ext': 'mp4',
            'title': 'Full Stop',
            'description': 'md5:4590409cef76b6500f96760c4b658aae',
            'thumbnail': r're:^https?://.*\.jpg$',
            'timestamp': 1739235272,
            'upload_date': '20250211',
            'uploader_id': '6122285389001',
            'duration': 1638.955,
            'tags': 'count:18',
        },
        'params': {
            'skip_download': True,
        },
    }]
    _ACCOUNT_ID = '6122285389001'
    _AUTH_URL = 'https://beacon.playback.api.brightcove.com/revry/api/account/anonymous_login?device_type=web&duid={duid}'
    _ASSET_INFO_URL = 'https://beacon.playback.api.brightcove.com/revry/api/account/{account_token}/asset_info/{video_id}?device_type=web&ngsw-bypass=1'
    _BRIGHTCOVE_URL_TEMPLATE = 'https://players.brightcove.net/{account_id}/default_default/index.html?videoId={video_id}'
    _AUTH_CACHE_NAMESPACE = 'revry'
    _AUTH_CACHE_KEY = 'auth_token'
    _DEVICE_ID_CACHE_KEY = 'device_id'

    def _get_auth_token(self):
        auth_data = self.cache.load(self._AUTH_CACHE_NAMESPACE, self._AUTH_CACHE_KEY)
        if auth_data and auth_data.get('expires_at', 0) > time_seconds():
            return auth_data.get('auth_token'), auth_data.get('account_token')

        device_id = self.cache.load(self._AUTH_CACHE_NAMESPACE, self._DEVICE_ID_CACHE_KEY)
        if not device_id:
            device_id = random_uuidv4()
            self.cache.store(self._AUTH_CACHE_NAMESPACE, self._DEVICE_ID_CACHE_KEY, device_id)

        auth_response = self._download_json(
            self._AUTH_URL.format(duid=device_id),
            None, 'Downloading authentication token', data=b'{}',
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            })

        auth_token = auth_response.get('auth_token')
        account_token = auth_response.get('account_token')

        if not auth_token:
            self.report_warning('Failed to get authentication token')
            return None, None

        expires_at = time_seconds(seconds=auth_response.get('expires_in', 604800))  # Default to 7 days
        auth_data = {
            'auth_token': auth_token,
            'account_token': account_token,
            'expires_at': expires_at,
        }
        self.cache.store(self._AUTH_CACHE_NAMESPACE, self._AUTH_CACHE_KEY, auth_data)

        return auth_token, account_token

    def _real_extract(self, url):
        video_id = self._match_id(url)

        auth_token, account_token = self._get_auth_token()
        if not auth_token:
            self.raise_login_required('Failed to get authentication token')

        try:
            asset_info = self._download_json(
                self._ASSET_INFO_URL.format(account_token=account_token, video_id=video_id),
                video_id, 'Downloading asset info',
                headers={
                    'Authorization': f'Bearer {auth_token}',
                    'Accept': 'application/json, text/plain, */*',
                })
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 404:
                self.raise_geo_restricted(countries=self._GEO_COUNTRIES)
            raise

        video_playback_details = asset_info.get('data', {}).get('video_playback_details', [])
        if not video_playback_details:
            raise ExtractorError('No video playback details found', expected=True)

        brightcove_video_id = video_playback_details[0].get('video_id')
        if not brightcove_video_id:
            raise ExtractorError('No Brightcove video ID found', expected=True)

        brightcove_url = self._BRIGHTCOVE_URL_TEMPLATE.format(
            account_id=self._ACCOUNT_ID,
            video_id=brightcove_video_id)

        return self.url_result(
            smuggle_url(brightcove_url, {'referrer': url}),
            ie=BrightcoveNewIE.ie_key(), video_id=brightcove_video_id)
