import base64
import json
import time
import urllib.parse

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    js_to_json,
    jwt_decode_hs256,
    parse_iso8601,
    parse_qs,
    update_url,
    update_url_query,
    url_or_none,
)
from ..utils.traversal import require, traverse_obj


class MTVServicesBaseIE(InfoExtractor):
    _GEO_BYPASS = False
    _GEO_COUNTRIES = ['US']
    _CACHE_SECTION = 'mtvservices'
    _ACCESS_TOKEN_KEY = 'access'
    _REFRESH_TOKEN_KEY = 'refresh'
    _MEDIA_TOKEN_KEY = 'media'
    _token_cache = {}

    @staticmethod
    def _jwt_is_expired(token):
        return jwt_decode_hs256(token)['exp'] - time.time() < 120

    @staticmethod
    def _get_auth_suite_data(config):
        return traverse_obj(config, {
            'clientId': ('clientId', {str}),
            'countryCode': ('countryCode', {str}),
        })

    def _call_auth_api(self, path, config, display_id=None, note=None, data=None, headers=None, query=None):
        headers = {
            'Accept': 'application/json',
            'Client-Description': 'deviceName=Chrome Windows;deviceType=desktop;system=Windows NT 10.0',
            'Api-Version': '2025-07-09',
            **(headers or {}),
        }
        if data is not None:
            headers['Content-Type'] = 'application/json'
            if isinstance(data, dict):
                data = json.dumps(data, separators=(',', ':')).encode()

        return self._download_json(
            f'https://auth.mtvnservices.com/{path}', display_id,
            note=note or 'Calling authentication API', data=data,
            headers=headers, query={**self._get_auth_suite_data(config), **(query or {})})

    def _get_fresh_access_token(self, config, display_id=None, force_refresh=False):
        resource_id = config['resourceId']
        # resource_id should already be in _token_cache since _get_media_token is the caller
        tokens = self._token_cache[resource_id]

        access_token = tokens.get(self._ACCESS_TOKEN_KEY)
        if not force_refresh and access_token and not self._jwt_is_expired(access_token):
            return access_token

        if self._REFRESH_TOKEN_KEY not in tokens:
            response = self._call_auth_api(
                'accessToken', config, display_id, 'Retrieving auth tokens', data=b'')
        else:
            response = self._call_auth_api(
                'accessToken/refresh', config, display_id, 'Refreshing auth tokens',
                data={'refreshToken': tokens[self._REFRESH_TOKEN_KEY]},
                headers={'Authorization': f'Bearer {access_token}'})

        tokens[self._ACCESS_TOKEN_KEY] = response['applicationAccessToken']
        tokens[self._REFRESH_TOKEN_KEY] = response['deviceRefreshToken']
        self.cache.store(self._CACHE_SECTION, resource_id, tokens)

        return tokens[self._ACCESS_TOKEN_KEY]

    def _get_media_token(self, video_config, config, display_id=None):
        resource_id = config['resourceId']
        if resource_id in self._token_cache:
            tokens = self._token_cache[resource_id]
        else:
            tokens = self._token_cache[resource_id] = self.cache.load(self._CACHE_SECTION, resource_id) or {}

        media_token = tokens.get(self._MEDIA_TOKEN_KEY)
        if media_token and not self._jwt_is_expired(media_token):
            return media_token

        access_token = self._get_fresh_access_token(config, display_id)
        if not jwt_decode_hs256(access_token).get('accessMethods'):
            # MTVServices uses a custom AdobePass oauth flow which is incompatible with AdobePassIE
            mso_id = self.get_param('ap_mso')
            if not mso_id:
                raise ExtractorError(
                    'This video is only available for users of participating TV providers. '
                    'Use --ap-mso to specify Adobe Pass Multiple-system operator Identifier and pass '
                    'cookies from a browser session where you are signed-in to your provider.', expected=True)

            auth_suite_data = json.dumps(
                self._get_auth_suite_data(config), separators=(',', ':')).encode()
            callback_url = update_url_query(config['callbackURL'], {
                'authSuiteData': urllib.parse.quote(base64.b64encode(auth_suite_data).decode()),
                'mvpdCode': mso_id,
            })
            auth_url = self._call_auth_api(
                f'mvpd/{mso_id}/login', config, display_id,
                'Retrieving provider authentication URL',
                query={'callbackUrl': callback_url},
                headers={'Authorization': f'Bearer {access_token}'})['authenticationUrl']
            res = self._download_webpage_handle(auth_url, display_id, 'Downloading provider auth page')
            # XXX: The following "provider-specific code" likely only works if mso_id == Comcast_SSO
            # BEGIN provider-specific code
            redirect_url = self._search_json(
                r'initInterstitialRedirect\(', res[0], 'redirect JSON',
                display_id, transform_source=js_to_json)['continue']
            urlh = self._request_webpage(redirect_url, display_id, 'Requesting provider redirect page')
            authorization_code = parse_qs(urlh.url)['authorizationCode'][-1]
            # END provider-specific code
            self._call_auth_api(
                f'access/mvpd/{mso_id}', config, display_id,
                'Submitting authorization code to MTVNServices',
                query={'authorizationCode': authorization_code}, data=b'',
                headers={'Authorization': f'Bearer {access_token}'})
            access_token = self._get_fresh_access_token(config, display_id, force_refresh=True)

        tokens[self._MEDIA_TOKEN_KEY] = self._call_auth_api(
            'mediaToken', config, display_id, 'Fetching media token', data={
                'content': {('id' if k == 'videoId' else k): v for k, v in video_config.items()},
                'resourceId': resource_id,
            }, headers={'Authorization': f'Bearer {access_token}'})['mediaToken']

        self.cache.store(self._CACHE_SECTION, resource_id, tokens)
        return tokens[self._MEDIA_TOKEN_KEY]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        try:
            data = self._download_json(
                update_url(url, query=None), display_id,
                query={'json': 'true'})
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 404 and not self.suitable(e.cause.response.url):
                self.raise_geo_restricted(countries=self._GEO_COUNTRIES)
            raise

        flex_wrapper = traverse_obj(data, (
            'children', lambda _, v: v['type'] == 'MainContainer',
            (None, ('children', lambda _, v: v['type'] == 'AviaWrapper')),
            'children', lambda _, v: v['type'] == 'FlexWrapper', {dict}, any))
        video_detail = traverse_obj(flex_wrapper, (
            (None, ('children', lambda _, v: v['type'] == 'AuthSuiteWrapper')),
            'children', lambda _, v: v['type'] == 'Player',
            'props', 'videoDetail', {dict}, any))
        if not video_detail:
            video_detail = traverse_obj(data, (
                'children', ..., ('handleTVEAuthRedirection', None),
                'videoDetail', {dict}, any, {require('video detail')}))

        mgid = video_detail['mgid']
        video_id = mgid.rpartition(':')[2]
        service_url = traverse_obj(video_detail, ('videoServiceUrl', {url_or_none}, {update_url(query=None)}))
        if not service_url:
            raise ExtractorError('This content is no longer available', expected=True)

        headers = {}
        if video_detail.get('authRequired'):
            # The vast majority of provider-locked content has been moved to Paramount+
            # BetIE is the only extractor that is currently known to reach this code path
            video_config = traverse_obj(flex_wrapper, (
                'children', lambda _, v: v['type'] == 'AuthSuiteWrapper',
                'props', 'videoConfig', {dict}, any, {require('video config')}))
            config = traverse_obj(data, (
                'props', 'authSuiteConfig', {dict}, {require('auth suite config')}))
            headers['X-VIA-TVE-MEDIATOKEN'] = self._get_media_token(video_config, config, display_id)

        stream_info = self._download_json(
            service_url, video_id, 'Downloading API JSON', 'Unable to download API JSON',
            query={'clientPlatform': 'desktop'}, headers=headers)['stitchedstream']

        manifest_type = stream_info['manifesttype']
        if manifest_type == 'hls':
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                stream_info['source'], video_id, 'mp4', m3u8_id=manifest_type)
        elif manifest_type == 'dash':
            formats, subtitles = self._extract_mpd_formats_and_subtitles(
                stream_info['source'], video_id, mpd_id=manifest_type)
        else:
            self.raise_no_formats(f'Unsupported manifest type "{manifest_type}"')
            formats, subtitles = [], {}

        return {
            **traverse_obj(video_detail, {
                'title': ('title', {str}),
                'channel': ('channel', 'name', {str}),
                'thumbnails': ('images', ..., {'url': ('url', {url_or_none})}),
                'description': (('fullDescription', 'description'), {str}, any),
                'series': ('parentEntity', 'title', {str}),
                'season_number': ('seasonNumber', {int_or_none}),
                'episode_number': ('episodeAiringOrder', {int_or_none}),
                'duration': ('duration', 'milliseconds', {float_or_none(scale=1000)}),
                'timestamp': ((
                    ('originalPublishDate', {parse_iso8601}),
                    ('publishDate', 'timestamp', {int_or_none})), any),
                'release_timestamp': ((
                    ('originalAirDate', {parse_iso8601}),
                    ('airDate', 'timestamp', {int_or_none})), any),
            }),
            'id': video_id,
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
        }


class MTVIE(MTVServicesBaseIE):
    IE_NAME = 'mtv'
    _VALID_URL = r'https?://(?:www\.)?mtv\.com/(?:video-clips|episodes)/(?P<id>[\da-z]{6})'
    _TESTS = [{
        'url': 'https://www.mtv.com/video-clips/syolsj',
        'info_dict': {
            'id': '213ea7f8-bac7-4a43-8cd5-8d8cb8c8160f',
            'ext': 'mp4',
            'display_id': 'syolsj',
            'title': 'The Challenge: Vets & New Threats',
            'description': 'md5:c4d2e90a5fff6463740fbf96b2bb6a41',
            'duration': 95.0,
            'thumbnail': r're:https://images\.paramount\.tech/uri/mgid:arc:imageassetref',
            'series': 'The Challenge',
            'season': 'Season 41',
            'season_number': 41,
            'episode': 'Episode 0',
            'episode_number': 0,
            'timestamp': 1753945200,
            'upload_date': '20250731',
            'release_timestamp': 1753945200,
            'release_date': '20250731',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.mtv.com/episodes/uzvigh',
        'info_dict': {
            'id': '364e8b9e-e415-11ef-b405-16fff45bc035',
            'ext': 'mp4',
            'display_id': 'uzvigh',
            'title': 'CT Tamburello and Johnny Bananas',
            'description': 'md5:364cea52001e9c13f92784e3365c6606',
            'channel': 'MTV',
            'duration': 1260.0,
            'thumbnail': r're:https://images\.paramount\.tech/uri/mgid:arc:imageassetref',
            'series': 'Ridiculousness',
            'season': 'Season 47',
            'season_number': 47,
            'episode': 'Episode 19',
            'episode_number': 19,
            'timestamp': 1753318800,
            'upload_date': '20250724',
            'release_timestamp': 1753318800,
            'release_date': '20250724',
        },
        'params': {'skip_download': 'm3u8'},
    }]
