import json
import time
import uuid

from .common import InfoExtractor
from ..compat import compat_str
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    jwt_decode_hs256,
    parse_age_limit,
    traverse_obj,
    try_call,
    try_get,
    unified_strdate,
)


class VootBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'voot'
    _GEO_BYPASS = False
    _LOGIN_HINT = 'Log in with "-u <email_address> -p <password>", or use "-u token -p <auth_token>" to login with auth token.'
    _TOKEN = None
    _EXPIRY = 0
    _API_HEADERS = {'Origin': 'https://www.voot.com', 'Referer': 'https://www.voot.com/'}

    def _perform_login(self, username, password):
        if self._TOKEN and self._EXPIRY:
            return

        if username.lower() == 'token' and try_call(lambda: jwt_decode_hs256(password)):
            VootBaseIE._TOKEN = password
            VootBaseIE._EXPIRY = jwt_decode_hs256(password)['exp']
            self.report_login()

        # Mobile number as username is not supported
        elif not username.isdigit():
            check_username = self._download_json(
                'https://userauth.voot.com/usersV3/v3/checkUser', None, data=json.dumps({
                    'type': 'email',
                    'email': username
                }, separators=(',', ':')).encode(), headers={
                    **self._API_HEADERS,
                    'Content-Type': 'application/json;charset=utf-8',
                }, note='Checking username', expected_status=403)
            if not traverse_obj(check_username, ('isExist', {bool})):
                if traverse_obj(check_username, ('status', 'code', {int})) == 9999:
                    self.raise_geo_restricted(countries=['IN'])
                raise ExtractorError('Incorrect username', expected=True)
            auth_token = traverse_obj(self._download_json(
                'https://userauth.voot.com/usersV3/v3/login', None, data=json.dumps({
                    'type': 'traditional',
                    'deviceId': str(uuid.uuid4()),
                    'deviceBrand': 'PC/MAC',
                    'data': {
                        'email': username,
                        'password': password
                    }
                }, separators=(',', ':')).encode(), headers={
                    **self._API_HEADERS,
                    'Content-Type': 'application/json;charset=utf-8',
                }, note='Logging in', expected_status=400), ('data', 'authToken', {dict}))
            if not auth_token:
                raise ExtractorError('Incorrect password', expected=True)
            VootBaseIE._TOKEN = auth_token['accessToken']
            VootBaseIE._EXPIRY = auth_token['expirationTime']

        else:
            raise ExtractorError(self._LOGIN_HINT, expected=True)

    def _check_token_expiry(self):
        if int(time.time()) >= self._EXPIRY:
            raise ExtractorError('Access token has expired', expected=True)

    def _real_initialize(self):
        if not self._TOKEN:
            self.raise_login_required(self._LOGIN_HINT, method=None)
        self._check_token_expiry()


class VootIE(VootBaseIE):
    _VALID_URL = r'''(?x)
                    (?:
                        voot:|
                        https?://(?:www\.)?voot\.com/?
                        (?:
                            movies?/[^/]+/|
                            (?:shows|kids)/(?:[^/]+/){4}
                        )
                     )
                    (?P<id>\d{3,})
                    '''
    _TESTS = [{
        'url': 'https://www.voot.com/shows/ishq-ka-rang-safed/1/360558/is-this-the-end-of-kamini-/441353',
        'info_dict': {
            'id': '441353',
            'ext': 'mp4',
            'title': 'Is this the end of Kamini?',
            'description': 'md5:06291fbbbc4dcbe21235c40c262507c1',
            'timestamp': 1472103000,
            'upload_date': '20160825',
            'series': 'Ishq Ka Rang Safed',
            'season_number': 1,
            'episode': 'Is this the end of Kamini?',
            'episode_number': 340,
            'release_date': '20160825',
            'season': 'Season 1',
            'age_limit': 13,
            'duration': 1146.0,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.voot.com/kids/characters/mighty-cat-masked-niyander-e-/400478/school-bag-disappears/440925',
        'only_matching': True,
    }, {
        'url': 'https://www.voot.com/movies/pandavas-5/424627',
        'only_matching': True,
    }, {
        'url': 'https://www.voot.com/movie/fight-club/621842',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        media_info = self._download_json(
            'https://psapi.voot.com/jio/voot/v1/voot-web/content/query/asset-details', video_id,
            query={'ids': f'include:{video_id}', 'responseType': 'common'}, headers={'accesstoken': self._TOKEN})

        try:
            m3u8_url = self._download_json(
                'https://vootapi.media.jio.com/playback/v1/playbackrights', video_id,
                'Downloading playback JSON', data=b'{}', headers={
                    **self.geo_verification_headers(),
                    **self._API_HEADERS,
                    'Content-Type': 'application/json;charset=utf-8',
                    'platform': 'androidwebdesktop',
                    'vootid': video_id,
                    'voottoken': self._TOKEN,
                })['m3u8']
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 400:
                self._check_token_expiry()
            raise

        formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', m3u8_id='hls')
        self._remove_duplicate_formats(formats)

        return {
            'id': video_id,
            # '/_definst_/smil:vod/' m3u8 manifests claim to have 720p+ formats but max out at 480p
            'formats': traverse_obj(formats, (
                lambda _, v: '/_definst_/smil:vod/' not in v['url'] or v['height'] <= 480)),
            'http_headers': self._API_HEADERS,
            **traverse_obj(media_info, ('result', 0, {
                'title': ('fullTitle', {str}),
                'description': ('fullSynopsis', {str}),
                'series': ('showName', {str}),
                'season_number': ('season', {int_or_none}),
                'episode': ('fullTitle', {str}),
                'episode_number': ('episode', {int_or_none}),
                'timestamp': ('uploadTime', {int_or_none}),
                'release_date': ('telecastDate', {unified_strdate}),
                'age_limit': ('ageNemonic', {parse_age_limit}),
                'duration': ('duration', {float_or_none}),
            })),
        }


class VootSeriesIE(VootBaseIE):
    _VALID_URL = r'https?://(?:www\.)?voot\.com/shows/[^/]+/(?P<id>\d{3,})'
    _TESTS = [{
        'url': 'https://www.voot.com/shows/chakravartin-ashoka-samrat/100002',
        'playlist_mincount': 442,
        'info_dict': {
            'id': '100002',
        },
    }, {
        'url': 'https://www.voot.com/shows/ishq-ka-rang-safed/100003',
        'playlist_mincount': 341,
        'info_dict': {
            'id': '100003',
        },
    }]
    _SHOW_API = 'https://psapi.voot.com/media/voot/v1/voot-web/content/generic/season-by-show?sort=season%3Aasc&id={}&responseType=common'
    _SEASON_API = 'https://psapi.voot.com/media/voot/v1/voot-web/content/generic/series-wise-episode?sort=episode%3Aasc&id={}&responseType=common&page={:d}'

    def _entries(self, show_id):
        show_json = self._download_json(self._SHOW_API.format(show_id), video_id=show_id)
        for season in show_json.get('result', []):
            page_num = 1
            season_id = try_get(season, lambda x: x['id'], compat_str)
            season_json = self._download_json(self._SEASON_API.format(season_id, page_num),
                                              video_id=season_id,
                                              note='Downloading JSON metadata page %d' % page_num)
            episodes_json = season_json.get('result', [])
            while episodes_json:
                page_num += 1
                for episode in episodes_json:
                    video_id = episode.get('id')
                    yield self.url_result(
                        'voot:%s' % video_id, ie=VootIE.ie_key(), video_id=video_id)
                episodes_json = self._download_json(self._SEASON_API.format(season_id, page_num),
                                                    video_id=season_id,
                                                    note='Downloading JSON metadata page %d' % page_num)['result']

    def _real_extract(self, url):
        show_id = self._match_id(url)
        return self.playlist_result(self._entries(show_id), playlist_id=show_id)
