from .brightcove import BrightcoveNewIE
from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    int_or_none,
    random_uuidv4,
    smuggle_url,
    time_seconds,
    traverse_obj,
)


class RevryIE(InfoExtractor):
    _VALID_URL = r'https?://watch\.revry\.tv/player/(?P<id>[0-9]+)'
    _GEO_COUNTRIES = ['US']
    _TESTS = [{
        # Series test
        'url': 'https://watch.revry.tv/player/43767/stream?assetType=series',
        'info_dict': {
            'id': '43767',
            'title': 'Unconventional',
            'description': 'Two eccentric queer siblings and their significant others try to start an unconventional family.',
        },
        'playlist_mincount': 9,
        'params': {
            'skip_download': True,
            'extract_flat': False,
        },
    }, {
        # Movie test
        'url': 'https://watch.revry.tv/player/43987/stream?assetType=movies',
        'info_dict': {
            'id': r're:\d+',
            'ext': 'mp4',
            'title': 'Cowboys',
            'description': 'md5:b5c7d5f8a8a89f87e5adde6fb50c77c0',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader_id': '6122285389001',
        },
        'params': {
            'skip_download': True,
        },
    }]
    _ACCOUNT_ID = '6122285389001'
    _AUTH_URL = 'https://beacon.playback.api.brightcove.com/revry/api/account/anonymous_login?device_type=web&duid={duid}'
    _ASSET_URL = 'https://beacon.playback.api.brightcove.com/revry/api/assets/{asset_id}?device_type=web&device_layout=web&asset_id={asset_id}'
    _ASSET_INFO_URL = 'https://beacon.playback.api.brightcove.com/revry/api/account/{account_token}/asset_info/{video_id}?device_type=web&ngsw-bypass=1'
    _EPISODES_URL = 'https://beacon.playback.api.brightcove.com/revry/api/tvshow/{series_id}/season/{season_id}/episodes?device_type=web&device_layout=web&layout_id=320&limit=1000'
    _BRIGHTCOVE_URL_TEMPLATE = 'https://players.brightcove.net/{account_id}/default_default/index.html?videoId={video_id}'
    _AUTH_CACHE_NAMESPACE = 'revry'
    _AUTH_CACHE_KEY = 'auth_data'

    def _get_auth_token(self):
        auth_data = self.cache.load(self._AUTH_CACHE_NAMESPACE, self._AUTH_CACHE_KEY)
        if auth_data and auth_data.get('expires_at', 0) > time_seconds():
            return auth_data.get('auth_token'), auth_data.get('account_token')

        # Generate or retrieve device ID
        device_id = auth_data.get('device_id') if auth_data else None
        if not device_id:
            device_id = random_uuidv4()

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
            'device_id': device_id,
            'auth_token': auth_token,
            'account_token': account_token,
            'expires_at': expires_at,
        }
        self.cache.store(self._AUTH_CACHE_NAMESPACE, self._AUTH_CACHE_KEY, auth_data)

        return auth_token, account_token

    def _get_headers(self, auth_token):
        return {
            'Authorization': f'Bearer {auth_token}',
            'Accept': 'application/json, text/plain, */*',
        }

    def _get_asset_data(self, asset_id, headers):
        try:
            asset_data = self._download_json(
                self._ASSET_URL.format(asset_id=asset_id),
                asset_id, 'Downloading asset data',
                headers=headers)
            return traverse_obj(asset_data, ('data', 'asset'), default={})
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 404:
                self.raise_geo_restricted(countries=self._GEO_COUNTRIES)
            raise

    def _get_brightcove_url(self, brightcove_video_id):
        return self._BRIGHTCOVE_URL_TEMPLATE.format(
            account_id=self._ACCOUNT_ID,
            video_id=brightcove_video_id)

    def _extract_video_id(self, asset_info):
        video_playback_details = traverse_obj(asset_info, ('data', 'video_playback_details'), default=[])
        if not video_playback_details:
            raise ExtractorError('No video playback details found', expected=True)

        brightcove_video_id = video_playback_details[0].get('video_id')
        if not brightcove_video_id:
            raise ExtractorError('No Brightcove video ID found', expected=True)

        return brightcove_video_id

    def _extract_series(self, asset_id, asset, url, headers, account_token):
        entries = []
        seasons = traverse_obj(asset, 'seasons', default=[])
        if not seasons:
            raise ExtractorError('No seasons found for series', expected=True)

        for season in seasons:
            season_id = season.get('id')
            if not season_id:
                continue

            # Get episodes for this season
            episodes_data = self._download_json(
                self._EPISODES_URL.format(series_id=asset_id, season_id=season_id),
                season_id, f'Downloading episodes for season {season.get("name", season_id)}',
                headers=headers)

            episodes = traverse_obj(episodes_data, 'data', default=[])
            for episode in episodes:
                episode_id = episode.get('id')
                if not episode_id:
                    continue

                # Get video playback details for this episode
                try:
                    episode_info = self._download_json(
                        self._ASSET_INFO_URL.format(account_token=account_token, video_id=episode_id),
                        episode_id, f'Downloading info for episode {episode.get("name", episode_id)}',
                        headers=headers)
                except ExtractorError as e:
                    self.report_warning(f'Failed to get info for episode {episode_id}: {e}')
                    continue

                try:
                    brightcove_video_id = self._extract_video_id(episode_info)
                except ExtractorError as e:
                    self.report_warning(f'{e.msg} for episode {episode_id}')
                    continue

                brightcove_url = self._get_brightcove_url(brightcove_video_id)

                entries.append({
                    '_type': 'url_transparent',
                    'url': smuggle_url(brightcove_url, {'referrer': url}),
                    'ie_key': BrightcoveNewIE.ie_key(),
                    'id': brightcove_video_id,
                    'title': episode.get('name'),
                    'description': episode.get('short_description'),
                    'thumbnail': traverse_obj(episode, ('image', 'url')),
                    'series': asset.get('name'),
                    'season': season.get('name'),
                    'season_number': int_or_none(episode.get('season_number')),
                    'episode': episode.get('name'),
                    'episode_number': int_or_none(episode.get('episode_number')),
                    'duration': int_or_none(episode.get('length')),
                })

        return self.playlist_result(entries, asset_id, asset.get('name'), asset.get('short_description'))

    def _extract_movie(self, asset_id, url, headers, account_token):
        try:
            asset_info = self._download_json(
                self._ASSET_INFO_URL.format(account_token=account_token, video_id=asset_id),
                asset_id, 'Downloading asset info',
                headers=headers)
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 404:
                self.raise_geo_restricted(countries=self._GEO_COUNTRIES)
            raise

        brightcove_video_id = self._extract_video_id(asset_info)
        brightcove_url = self._get_brightcove_url(brightcove_video_id)

        return self.url_result(
            smuggle_url(brightcove_url, {'referrer': url}),
            ie=BrightcoveNewIE.ie_key(), video_id=brightcove_video_id)

    def _real_extract(self, url):
        asset_id = self._match_id(url)

        auth_token, account_token = self._get_auth_token()
        if not auth_token:
            self.raise_login_required('Failed to get authentication token')

        headers = self._get_headers(auth_token)
        asset = self._get_asset_data(asset_id, headers)
        asset_type = asset.get('type')

        if asset_type == 'series':
            return self._extract_series(asset_id, asset, url, headers, account_token)
        else:
            return self._extract_movie(asset_id, url, headers, account_token)
