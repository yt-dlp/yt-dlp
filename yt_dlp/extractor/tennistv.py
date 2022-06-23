import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    random_uuidv4,
    unified_timestamp,
    urlencode_postdata,
)


class TennisTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tennistv\.com/videos/(?P<id>[-a-z0-9]+)'
    _TESTS = [{
        'url': 'https://www.tennistv.com/videos/indian-wells-2018-verdasco-fritz',
        'info_dict': {
            'id': 'indian-wells-2018-verdasco-fritz',
            'ext': 'mp4',
            'title': 'Fernando Verdasco v Taylor Fritz',
            'description': 're:^After his stunning victory.{174}$',
            'thumbnail': 'https://atp-prod.akamaized.net/api/images/v1/images/112831/landscape/1242/0',
            'timestamp': 1521017381,
            'upload_date': '20180314',
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Requires email and password of a subscribed account',
    }, {
        'url': 'https://www.tennistv.com/videos/2650480/best-matches-of-2022-part-5',
        'info_dict': {
            'id': '2650480',
            'ext': 'mp4',
            'title': 'Best Matches of 2022 - Part 5',
            'description': 'md5:36dec3bfae7ed74bd79e48045b17264c',
            'thumbnail': 'https://open.http.mp.streamamg.com/p/3001482/sp/300148200/thumbnail/entry_id/0_myef18pd/version/100001/height/1920',
        },
        'params': {'skip_download': 'm3u8'},
        'skip': 'Requires email and password of a subscribed account',
    }]
    _NETRC_MACHINE = 'tennistv'

    access_token, refresh_token = None, None
    _PARTNER_ID = 3001482
    _FORMAT_URL = 'https://open.http.mp.streamamg.com/p/{partner}/sp/{partner}00/playManifest/entryId/{entry}/format/applehttp/protocol/https/a.m3u8?ks={session}'
    _AUTH_BASE_URL = 'https://sso.tennistv.com/auth/realms/TennisTV/protocol/openid-connect'
    _HEADERS = {
        'origin': 'https://www.tennistv.com',
        'referer': 'https://www.tennistv.com/',
        'content-Type': 'application/x-www-form-urlencoded'
    }

    def _perform_login(self, username, password):
        login_page = self._download_webpage(
            f'{self._AUTH_BASE_URL}/auth', None, 'Downloading login page',
            query={
                'client_id': 'tennis-tv-web',
                'redirect_uri': 'https://tennistv.com',
                'response_mode': 'fragment',
                'response_type': 'code',
                'scope': 'openid'
            })

        post_url = self._html_search_regex(r'action=["\']([^"\']+?)["\']\s+method=["\']post["\']', login_page, 'login POST url')
        temp_page = self._download_webpage(
            post_url, None, 'Sending login data', 'Unable to send login data',
            headers=self._HEADERS, data=urlencode_postdata({
                'username': username,
                'password': password,
                'submitAction': 'Log In'
            }))
        if 'Your username or password was incorrect' in temp_page:
            raise ExtractorError('Your username or password was incorrect', expected=True)

        handle = self._request_webpage(
            f'{self._AUTH_BASE_URL}/auth', None, 'Logging in', headers=self._HEADERS,
            query={
                'client_id': 'tennis-tv-web',
                'redirect_uri': 'https://www.tennistv.com/resources/v1.1.10/html/silent-check-sso.html',
                'state': random_uuidv4(),
                'response_mode': 'fragment',
                'response_type': 'code',
                'scope': 'openid',
                'nonce': random_uuidv4(),
                'prompt': 'none'
            })

        self.get_token(None, {
            'code': urllib.parse.parse_qs(handle.geturl())['code'][-1],
            'grant_type': 'authorization_code',
            'client_id': 'tennis-tv-web',
            'redirect_uri': 'https://www.tennistv.com/resources/v1.1.10/html/silent-check-sso.html'
        })

    def get_token(self, video_id, payload):
        res = self._download_json(
            f'{self._AUTH_BASE_URL}/token', video_id, 'Fetching tokens',
            'Unable to fetch tokens', headers=self._HEADERS, data=urlencode_postdata(payload))

        self.access_token = res.get('access_token') or self.access_token
        self.refresh_token = res.get('refresh_token') or self.refresh_token

    def _real_initialize(self):
        if self.access_token and self.refresh_token:
            return

        cookies = self._get_cookies('https://www.tennistv.com/')
        if not cookies.get('access_token') or not cookies.get('refresh_token'):
            self.raise_login_required()
        self.access_token, self.refresh_token = cookies['access_token'].value, cookies['refresh_token'].value

    def _download_session_json(self, video_id, entryid,):
        return self._download_json(
            f'https://atppayments.streamamg.com/api/v1/session/ksession/?lang=en&apijwttoken={self.access_token}&entryId={entryid}',
            video_id, 'Downloading ksession token', 'Failed to download ksession token', headers=self._HEADERS)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        entryid = self._search_regex(r'data-entry-id=["\']([^"\']+)', webpage, 'entryID')
        session_json = self._download_session_json(video_id, entryid)

        k_session = session_json.get('KSession')
        if k_session is None:
            self.get_token(video_id, {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': 'tennis-tv-web'
            })
            k_session = self._download_session_json(video_id, entryid).get('KSession')
            if k_session is None:
                raise ExtractorError('Failed to get KSession, possibly a premium video', expected=True)

        if session_json.get('ErrorMessage'):
            self.report_warning(session_json['ErrorMessage'])

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            self._FORMAT_URL.format(partner=self._PARTNER_ID, entry=entryid, session=k_session), video_id)

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': self._html_extract_title(webpage) or self._og_search_title(webpage),
            'description': self._html_search_regex(
                (r'<span itemprop="description" content=["\']([^"\']+)["\']>', *self._og_regexes('description')),
                webpage, 'description', fatal=False),
            'thumbnail': f'https://open.http.mp.streamamg.com/p/{self._PARTNER_ID}/sp/{self._PARTNER_ID}00/thumbnail/entry_id/{entryid}/version/100001/height/1920',
            'timestamp': unified_timestamp(self._html_search_regex(
                r'<span itemprop="description" content=["\']([^"\']+)["\']>', webpage, 'upload time')),
            'series': self._html_search_regex(r'data-series\s*?=\s*?"(.*?)"', webpage, 'series', fatal=False) or None,
            'season': self._html_search_regex(r'data-tournament-city\s*?=\s*?"(.*?)"', webpage, 'season', fatal=False) or None,
            'episode': self._html_search_regex(r'data-round\s*?=\s*?"(.*?)"', webpage, 'round', fatal=False) or None,
            'formats': formats,
            'subtitles': subtitles,
        }
