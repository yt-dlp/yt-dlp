# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor

from ..utils import (
    ExtractorError,
    unified_timestamp,
    urlencode_postdata,
    random_uuidv4,
    update_url_query
)

from ..compat import compat_urlparse


class TennisTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tennistv\.com/videos/(?P<id>[-a-z0-9]+)'
    _TEST = {
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
    }
    _NETRC_MACHINE = 'tennistv'

    ACCESS_TOKEN = None
    REFRESH_TOKEN = None
    PARTNER_ID = 3001482
    headers = {
        'origin': 'https://www.tennistv.com',
        'referer': 'https://www.tennistv.com/',
        'content-Type': 'application/x-www-form-urlencoded'
    }

    def _login(self):

        BASE_URL = 'https://sso.tennistv.com/auth/realms/TennisTV/protocol/openid-connect/auth'

        cookies = self._get_cookies('https://www.tennistv.com/')
        username, password = self._get_login_info()

        if username and password:

            login_form = {
                'username': username,
                'password': password,
                'submitAction': 'Log In'
            }

            login_page = self._download_webpage(update_url_query(BASE_URL, {'client_id': 'tennis-tv-web',
                        'redirect_uri': 'https://tennistv.com',
                        'response_mode': 'fragment',
                        'response_type': 'code',
                        'scope': 'openid'}),
                        '')
            post_url = self._html_search_regex(r'action=["\'](.+?)["\']\s+?method=["\']post["\']', login_page, None)

            self._download_webpage(post_url, None, 'Sending login data', 'Unable to send login data',
                                   data=urlencode_postdata(login_form), headers=self.headers)

            _, handle = self._download_webpage_handle(update_url_query(BASE_URL, {'client_id': 'tennis-tv-web',
                            'redirect_uri': 'https://www.tennistv.com/resources/v1.1.10/html/silent-check-sso.html',
                            'state': random_uuidv4(),
                            'response_mode': 'fragment',
                            'response_type': 'code',
                            'scope': 'openid',
                            'nonce': random_uuidv4(),
                            'prompt': 'none'}), '',
                            headers=self.headers)

            self.token_util(None, {
                'code': compat_urlparse.parse_qs(handle.geturl()).get('code')[-1],  # There can be multiple, always use the last one
                'grant_type': 'authorization_code',
                'client_id': 'tennis-tv-web',
                'redirect_uri': 'https://www.tennistv.com/resources/v1.1.10/html/silent-check-sso.html'
            })
            return

        if cookies is not None:
            self.ACCESS_TOKEN = cookies.get('access_token').value
            self.REFRESH_TOKEN = cookies.get('refresh_token').value
            return

        else:
            self.report_warning('Site requires a sbuscribed account. Either pass in the cookies or login credentials')

    def token_util(self, video_id, payload):
        res = self._download_json('https://sso.tennistv.com/auth/realms/TennisTV/protocol/openid-connect/token', video_id,
                                  'Fetching tokens', 'Unable to fetch tokens', headers=self.headers,
                                  data=urlencode_postdata(payload))

        self.ACCESS_TOKEN = res.get('access_token')
        self.REFRESH_TOKEN = res.get('refresh_token')

    def _real_initialize(self):
        self._login()

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._html_search_regex(r'<title>(.+?)</title>', webpage, 'Title',
                                        fatal=False) or self._og_search_title(webpage)

        entryid = self._search_regex(r'data-entry-id=["\']([^"\']+)', webpage, 'entryID')

        session_json = self._download_json(f'https://atppayments.streamamg.com/api/v1/session/ksession/?lang=en&apijwttoken={self.ACCESS_TOKEN}&entryId={entryid}',
                                           video_id, 'Downloading ksession token', 'Failed to download ksession token', headers=self.headers)

        k_session = session_json.get('KSession')
        if k_session is None:

            k_session = self.token_util(video_id, {
                'grant_type': 'refresh_token',
                'refresh_token': self.REFRESH_TOKEN,
                'client_id': 'tennis-tv-web'
            })
            if k_session is None:
                raise ExtractorError('Failed to get KSession, possible premium video', expected=True)

        if session_json.get('ErrorMessage'):
            self.to_screen(session_json['ErrorMessage'])

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(f'https://open.http.mp.streamamg.com/p/{self.PARTNER_ID}/sp/{self.PARTNER_ID}00/playManifest/entryId/{entryid}/format/applehttp/protocol/https/a.m3u8?ks={k_session}', video_id)

        return {
            'id': video_id,
            'title': title,
            'description': self._html_search_regex(r'<span itemprop="description" content=["\'](.+?)["\']>', webpage, 'description', fatal=False) or self._og_search_description(webpage),
            'formats': formats,
            'thumbnail': f'https://open.http.mp.streamamg.com/p/{self.PARTNER_ID}/sp/{self.PARTNER_ID}00/thumbnail/entry_id/{entryid}/version/100001/height/1080',
            'timestamp': unified_timestamp(self._html_search_regex(r'<span itemprop="description" content=["\'](.+?)["\']>', webpage, 'upload time')),
            'subtitles': subtitles,
        }
