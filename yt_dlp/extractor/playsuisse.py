import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_qs,
    traverse_obj,
    update_url_query,
    urlencode_postdata,
)


class PlaySuisseIE(InfoExtractor):
    _NETRC_MACHINE = 'playsuisse'
    _VALID_URL = r'https?://(?:www\.)?playsuisse\.ch/(?:watch|detail)/(?:[^#]*[?&]episodeId=)?(?P<id>[0-9]+)'
    
    _GRAPHQL_QUERY = '''
        query AssetWatch($assetId: ID!) {
            assetV2(id: $assetId) {
                ...Asset
                episodes {
                    ...Asset
                }
            }
        }
        fragment Asset on AssetV2 {
            id
            name
            description
            duration
            episodeNumber
            seasonNumber
            seriesName
            medias {
                type
                url
            }
            thumbnail16x9 {
                ...ImageDetails
            }
            thumbnail2x3 {
                ...ImageDetails
            }
            thumbnail16x9WithTitle {
                ...ImageDetails
            }
            thumbnail2x3WithTitle {
                ...ImageDetails
            }
        }
        fragment ImageDetails on AssetImage {
            id
            url
        }'''
    _LOGIN_BASE_URL = 'https://login.srgssr.ch/srgssrlogin.onmicrosoft.com'
    _LOGIN_PATH = 'B2C_1A__SignInV2'
    _ID_TOKEN = None

    def _perform_login(self, username, password):
        login_page = self._download_webpage(
            'https://www.playsuisse.ch/api/sso/login', None, note='Downloading login page',
            query={'x': 'x', 'locale': 'de', 'redirectUrl': 'https://www.playsuisse.ch/'})
        settings = self._search_json(r'var\s+SETTINGS\s*=', login_page, 'settings', None)

        csrf_token = settings['csrf']
        query = {'tx': settings['transId'], 'p': self._LOGIN_PATH}

        status = traverse_obj(self._download_json(
            f'{self._LOGIN_BASE_URL}/{self._LOGIN_PATH}/SelfAsserted', None, 'Logging in',
            query=query, headers={'X-CSRF-TOKEN': csrf_token}, data=urlencode_postdata({
                'request_type': 'RESPONSE',
                'signInName': username,
                'password': password,
            }), expected_status=400), ('status', {int_or_none}))
        if status == 400:
            raise ExtractorError('Invalid username or password', expected=True)

        urlh = self._request_webpage(
            f'{self._LOGIN_BASE_URL}/{self._LOGIN_PATH}/api/CombinedSigninAndSignup/confirmed',
            None, 'Downloading ID token', query={
                'rememberMe': 'false',
                'csrf_token': csrf_token,
                **query,
                'diags': '',
            })

        self._ID_TOKEN = traverse_obj(parse_qs(urlh.url), ('id_token', 0))
        if not self._ID_TOKEN:
            raise ExtractorError('Login failed')

    def _get_media_data(self, media_id):
        response = self._download_json(
            'https://www.playsuisse.ch/api/graphql',
            media_id, data=json.dumps({
                'operationName': 'AssetWatch',
                'query': self._GRAPHQL_QUERY,
                'variables': {'assetId': media_id},
            }).encode(),
            headers={'Content-Type': 'application/json', 'locale': 'fr'})

        return response['data']['assetV2']

    def _real_extract(self, url):
        if not self._ID_TOKEN:
            self.raise_login_required(method='password')

        media_id = self._match_id(url)
        media_data = self._get_media_data(media_id)
        info = self._extract_single(media_data)
        
        if info is None:
            raise ExtractorError('Unable to extract media information')
        
        if media_data.get('episodes'):
            info.update({
                '_type': 'playlist',
                'entries': [
                    self._extract_single(episode)
                    for episode in media_data['episodes']
                    if self._extract_single(episode) is not None
                ],
            })
        return info

    def _extract_single(self, media_data):
        if not media_data or 'id' not in media_data:
            return None

        thumbnails = traverse_obj(media_data, lambda k, _: k.startswith('thumbnail'))

        formats, subtitles = [], {}
        for media in traverse_obj(media_data, 'medias', default=[]):
            if not media.get('url') or media.get('type') != 'HLS':
                continue
            f, subs = self._extract_m3u8_formats_and_subtitles(
                update_url_query(media['url'], {'id_token': self._ID_TOKEN}),
                media_data['id'], 'mp4', m3u8_id='HLS', fatal=False)
            formats.extend(f)
            self._merge_subtitles(subs, target=subtitles)

        series_name = media_data.get('seriesName', '')
        episode_name = media_data.get('name', '')
        
        if series_name and episode_name:
            title = f"{series_name} - {episode_name}"
        else:
            title = episode_name or series_name or 'Unknown Title'

        return {
            'id': media_data['id'],
            'title': title,
            'description': media_data.get('description'),
            'thumbnails': thumbnails,
            'duration': int_or_none(media_data.get('duration')),
            'formats': formats,
            'subtitles': subtitles,
            'series': series_name,
            'season_number': int_or_none(media_data.get('seasonNumber')),
            'episode': episode_name if media_data.get('episodeNumber') else None,
            'episode_number': int_or_none(media_data.get('episodeNumber')),
        }
