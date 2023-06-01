import json
import urllib.error

from .gigya import GigyaBaseIE
from ..utils import (
    ExtractorError,
    clean_html,
    float_or_none,
    int_or_none,
    join_nonempty,
    make_archive_id,
    parse_iso8601,
    str_or_none,
    traverse_obj,
    url_or_none,
    urlencode_postdata,
)


class VrtMaxIE(GigyaBaseIE):
    IE_DESC = 'VRT MAX'
    _VALID_URL = r'https?://(?:www\.)?vrt\.be/vrtnu/a-z/(?:[^/]+/){2}(?P<id>[^/?#&]+)'
    _TESTS = [{
        # CONTENT_IS_AGE_RESTRICTED
        'url': 'https://www.vrt.be/vrtnu/a-z/de-ideale-wereld/2023-vj/de-ideale-wereld-d20230116/',
        'info_dict': {
            'id': 'pbs-pub-855b00a8-6ce2-4032-ac4f-1fcf3ae78524$vid-d2243aa1-ec46-4e34-a55b-92568459906f',
            'ext': 'mp4',
            'title': 'Tom Waes',
            'description': 'Satirisch actualiteitenmagazine met Ella Leyers. Tom Waes is te gast.',
            'timestamp': 1673905125,
            'release_timestamp': 1673905125,
            'series': 'De ideale wereld',
            'season_id': '1672830988794',
            'episode': 'Aflevering 1',
            'episode_number': 1,
            'episode_id': '1672830988861',
            'display_id': 'de-ideale-wereld-d20230116',
            'channel': 'VRT',
            'duration': 1939.0,
            'thumbnail': 'https://images.vrt.be/orig/2023/01/10/1bb39cb3-9115-11ed-b07d-02b7b76bf47f.jpg',
            '_old_archive_ids': ['vrtnu pbs-pub-855b00a8-6ce2-4032-ac4f-1fcf3ae78524$vid-d2243aa1-ec46-4e34-a55b-92568459906f'],
            'release_date': '20230116',
            'upload_date': '20230116',
        },
    }, {
        'url': 'https://www.vrt.be/vrtnu/a-z/buurman--wat-doet-u-nu-/6/buurman--wat-doet-u-nu--s6-trailer/',
        'info_dict': {
            'id': 'pbs-pub-ad4050eb-d9e5-48c2-9ec8-b6c355032361$vid-0465537a-34a8-4617-8352-4d8d983b4eee',
            'ext': 'mp4',
            'title': 'Trailer seizoen 6 \'Buurman, wat doet u nu?\'',
            'description': 'md5:197424726c61384b4e5c519f16c0cf02',
            'timestamp': 1652940000,
            'release_timestamp': 1652940000,
            'series': 'Buurman, wat doet u nu?',
            'season': 'Seizoen 6',
            'season_number': 6,
            'season_id': '1652344200907',
            'episode': 'Aflevering 0',
            'episode_number': 0,
            'episode_id': '1652951873524',
            'display_id': 'buurman--wat-doet-u-nu--s6-trailer',
            'channel': 'VRT',
            'duration': 33.13,
            'thumbnail': 'https://images.vrt.be/orig/2022/05/23/3c234d21-da83-11ec-b07d-02b7b76bf47f.jpg',
            '_old_archive_ids': ['vrtnu pbs-pub-ad4050eb-d9e5-48c2-9ec8-b6c355032361$vid-0465537a-34a8-4617-8352-4d8d983b4eee'],
            'release_date': '20220519',
            'upload_date': '20220519',
        },
        'params': {'skip_download': 'm3u8'},
    }]
    _NETRC_MACHINE = 'vrtmax'
    _authenticated = False

    def _perform_login(self, username, password):
        auth_info = self._gigya_login({
            'APIKey': '3_0Z2HujMtiWq_pkAjgnS2Md2E11a1AwZjYiBETtwNE-EoEHDINgtnvcAOpNgmrVGy',
            'targetEnv': 'jssdk',
            'loginID': username,
            'password': password,
            'authMode': 'cookie',
        })

        if auth_info.get('errorDetails'):
            raise ExtractorError(f'Unable to login. VrtNU said: {auth_info["errorDetails"]}', expected=True)

        # Sometimes authentication fails for no good reason, retry
        for retry in self.RetryManager():
            if retry.attempt > 1:
                self._sleep(1, None)
            try:
                self._request_webpage(
                    'https://token.vrt.be/vrtnuinitlogin', None, note='Requesting XSRF Token',
                    errnote='Could not get XSRF Token', query={
                        'provider': 'site',
                        'destination': 'https://www.vrt.be/vrtnu/',
                    })
                self._request_webpage(
                    'https://login.vrt.be/perform_login', None,
                    note='Performing login', errnote='Login failed',
                    query={'client_id': 'vrtnu-site'}, data=urlencode_postdata({
                        'UID': auth_info['UID'],
                        'UIDSignature': auth_info['UIDSignature'],
                        'signatureTimestamp': auth_info['signatureTimestamp'],
                        '_csrf': self._get_cookies('https://login.vrt.be').get('OIDCXSRF').value,
                    }))
            except ExtractorError as e:
                if isinstance(e.cause, urllib.error.HTTPError) and e.cause.code == 401:
                    retry.error = e
                    continue
                raise

        self._authenticated = True

    def _real_extract(self, url):
        display_id = self._match_id(url)
        details = self._download_json(
            f'{url.strip("/")}.model.json', display_id, 'Downloading asset JSON',
            'Unable to download asset JSON')['details']

        watch_info = traverse_obj(details, (
            'actions', lambda _, v: v['type'] == 'watch-episode', {dict}), get_all=False) or {}
        video_id = join_nonempty(
            'episodePublicationId', 'episodeVideoId', delim='$', from_dict=watch_info)
        if '$' not in video_id:
            raise ExtractorError('Unable to extract video ID')

        vrtnutoken = self._download_json(
            'https://token.vrt.be/refreshtoken', video_id, note='Retrieving vrtnutoken',
            errnote='Token refresh failed')['vrtnutoken'] if self._authenticated else ''

        vrt_player_token = self._download_json(
            'https://media-services-public.vrt.be/vualto-video-aggregator-web/rest/external/v2/tokens',
            video_id, 'Downloading token', headers={
                **self.geo_verification_headers(),
                'Content-Type': 'application/json; charset=utf-8',
            }, data=json.dumps({'identityToken': vrtnutoken}).encode())['vrtPlayerToken']

        video_info = self._download_json(
            f'https://media-services-public.vrt.be/media-aggregator/v2/media-items/{video_id}',
            video_id, 'Downloading video JSON', query={
                'vrtPlayerToken': vrt_player_token,
                'client': 'vrtnu-web@PROD',
            }, expected_status=400)

        if 'title' not in video_info:
            code = video_info.get('code')
            if code in ('AUTHENTICATION_REQUIRED', 'CONTENT_IS_AGE_RESTRICTED'):
                self.raise_login_required(code)
            elif code in ('INVALID_LOCATION', 'CONTENT_AVAILABLE_ONLY_IN_BE'):
                self.raise_geo_restricted(countries=['BE'])
            elif code == 'CONTENT_AVAILABLE_ONLY_FOR_BE_RESIDENTS_AND_EXPATS':
                if not self._authenticated:
                    self.raise_login_required(code)
                self.raise_geo_restricted(countries=['BE'])
            raise ExtractorError(code, expected=True)

        formats = []
        subtitles = {}
        for target in traverse_obj(video_info, ('targetUrls', lambda _, v: url_or_none(v['url']) and v['type'])):
            format_type = target['type'].upper()
            format_url = target['url']
            if format_type in ('HLS', 'HLS_AES'):
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    format_url, video_id, 'mp4', m3u8_id=format_type, fatal=False)
                formats.extend(fmts)
                subtitles = self._merge_subtitles(subtitles, subs)
            elif format_type == 'HDS':
                formats.extend(self._extract_f4m_formats(
                    format_url, video_id, f4m_id=format_type, fatal=False))
            elif format_type == 'MPEG_DASH':
                fmts, subs = self._extract_mpd_formats_and_subtitles(
                    format_url, video_id, mpd_id=format_type, fatal=False)
                formats.extend(fmts)
                subtitles = self._merge_subtitles(subtitles, subs)
            elif format_type == 'HSS':
                fmts, subs = self._extract_ism_formats_and_subtitles(
                    format_url, video_id, ism_id='mss', fatal=False)
                formats.extend(fmts)
                subtitles = self._merge_subtitles(subtitles, subs)
            else:
                formats.append({
                    'format_id': format_type,
                    'url': format_url,
                })

        for sub in traverse_obj(video_info, ('subtitleUrls', lambda _, v: v['url'] and v['type'] == 'CLOSED')):
            subtitles.setdefault('nl', []).append({'url': sub['url']})

        return {
            **traverse_obj(details, {
                'title': 'title',
                'description': ('description', {clean_html}),
                'timestamp': ('data', 'episode', 'onTime', 'raw', {parse_iso8601}),
                'release_timestamp': ('data', 'episode', 'onTime', 'raw', {parse_iso8601}),
                'series': ('data', 'program', 'title'),
                'season': ('data', 'season', 'title', 'value'),
                'season_number': ('data', 'season', 'title', 'raw', {int_or_none}),
                'season_id': ('data', 'season', 'id', {str_or_none}),
                'episode': ('data', 'episode', 'number', 'value', {str_or_none}),
                'episode_number': ('data', 'episode', 'number', 'raw', {int_or_none}),
                'episode_id': ('data', 'episode', 'id', {str_or_none}),
            }),
            'id': video_id,
            'display_id': display_id,
            'channel': 'VRT',
            'formats': formats,
            'duration': float_or_none(video_info.get('duration'), 1000),
            'thumbnail': url_or_none(video_info.get('posterImageUrl')),
            'subtitles': subtitles,
            '_old_archive_ids': [make_archive_id('VrtNU', video_id)],
        }
