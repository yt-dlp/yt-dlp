# coding: utf-8
import json
import math
import itertools
import datetime
import re
import urllib.parse
import random
from .common import InfoExtractor, SearchInfoExtractor
from ..utils import (
    unified_timestamp,
    variadic,
    try_get,
    traverse_obj,
    int_or_none,
    bool_or_none,
    float_or_none,
    str_or_none,
    url_or_none,
    unescapeHTML,
    urlencode_postdata,
    ExtractorError,
)


class RokfinIE(InfoExtractor):
    _NETRC_MACHINE = 'rokfin'
    _SINGLE_VIDEO_META_DATA_BASE_URL = 'https://prod-api-v2.production.rokfin.com/api/v2/public/'
    _SINGLE_VIDEO_BASE_WEB_URL = 'https://rokfin.com/'
    access_mgmt_tokens = None  # OAuth 2.0: RFC 6749, Sec. 1.4-5

    def _real_initialize(self):
        self._login()

    def _login(self):
        LOGIN_PAGE_URL = 'https://secure.rokfin.com/auth/realms/rokfin-web/protocol/openid-connect/auth?client_id=web&redirect_uri=https%3A%2F%2Frokfin.com%2Ffeed&response_mode=fragment&response_type=code&scope=openid'
        AUTHENTICATION_URL_REGEX_STEP_1 = r'\<form\s+[^>]+action\s*=\s*"(?P<authentication_point_url>https://secure\.rokfin\.com/auth/realms/rokfin-web/login-actions/authenticate\?[^"]+)"[^>]*>'

        username, password = self._get_login_info()
        if username is None or self._logged_in():
            return

        # In OpenID terms (https://openid.net/specs/), this program acts as a (public) Client (a.k.a. Client Application),
        # the User Agent, and the Relying Party (RP) simultaneously, with the Identity Provider (IDP) being secure.rokfin.com.
        # Rokfin uses KeyCloak (https://www.keycloak.org) as the OpenID implementation of choice.
        #
        # ---------------------------- CODE FLOW AUTHORIZATION ----------------------------
        # https://openid.net/specs/openid-connect-core-1_0.html#CodeFlowAuth (Sec. 3.1.1)
        #
        # Authentication phase:
        #
        # Step 1: preparation
        login_page, urlh = self._download_webpage_handle(LOGIN_PAGE_URL, None, note='loading login page', fatal=False) or (None, None)
        authentication_point_url = try_get(login_page, lambda html: unescapeHTML(re.search(AUTHENTICATION_URL_REGEX_STEP_1, html).group('authentication_point_url')))
        if authentication_point_url is None:
            self.report_warning('login failed unexpectedly: Rokfin extractor must be updated')
            self._clear_cookies()
            return

        # Step 2 & 3: authentication
        resp_body, urlh = self._download_webpage_handle(
            authentication_point_url, None, note='logging in', fatal=False, expected_status=404, encoding='utf-8',
            data=urlencode_postdata({'username': username, 'password': password, 'rememberMe': 'off', 'credentialId': ''})) or (None, None)
        # rememberMe=off resets the session when yt-dlp exits:
        # https://web.archive.org/web/20220218003425/https://wjw465150.gitbooks.io/keycloak-documentation/content/server_admin/topics/login-settings/remember-me.html
        if not self._logged_in():
            self._clear_cookies()
            self.report_warning('login failed' + (': invalid username or password.' if type(resp_body) is str and re.search(r'invalid\s+username\s+or\s+password', resp_body, re.IGNORECASE) else ''))

            if urlh:
                self.write_debug(f'HTTP status: {urlh.code}')

            return

        # Authorization phase:
        #
        # Steps 4-7:
        access_mgmt_tokens = self._get_OAuth_tokens()
        if not access_mgmt_tokens:
            self._logout()
            return

        # No validation phase (step 8):
        #
        # (1) the client-side ID-token validation skipped;
        # (2) Rokfin does not supply Subject Identifier.

        RokfinIE.access_mgmt_tokens = access_mgmt_tokens

    def _logout(self):
        LOGOUT_URL = 'https://secure.rokfin.com/auth/realms/rokfin-web/protocol/openid-connect/logout?redirect_uri=https%3A%2F%2Frokfin.com%2F'
        if self._get_login_info()[0] is None:  # username is None
            return
        self._download_webpage_handle(LOGOUT_URL, None, note='logging out', fatal=False, encoding='utf-8')
        if self._logged_in():
            self.write_debug('logout failed')
        self._clear_cookies()
        RokfinIE.access_mgmt_tokens = None
        # No token revocation takes place during logout, as KEYCLOAK does not -- and has no plans to -- support individual token
        # revocation on external party's request. See
        # https://web.archive.org/web/20220215040021/https://keycloak.discourse.group/t/revoking-or-invalidating-an-authorization-token/1032

    # Are we logged in?
    def _logged_in(self):
        current_time_utc = datetime.datetime.utcnow().timestamp()
        SESSION_COOKIE_NAMES = set(('KEYCLOAK_IDENTITY', 'KEYCLOAK_IDENTITY_LEGACY', 'KEYCLOAK_SESSION', 'KEYCLOAK_SESSION_LEGACY'))
        return set([cookie.name for cookie in self._downloader.cookiejar if (cookie.name in SESSION_COOKIE_NAMES)
                    and (cookie.name not in ('KEYCLOAK_SESSION', 'KEYCLOAK_SESSION_LEGACY')
                         or cookie.expires > current_time_utc)]) == SESSION_COOKIE_NAMES

    def _download_json_handle(
            self, url_or_request, video_id, note='Downloading JSON metadata',
            errnote='Unable to download JSON metadata', transform_source=None,
            fatal=True, encoding=None, data=None, headers={}, query={},
            expected_status=None):
        # Testing only:
        if False and RokfinIE.access_mgmt_tokens and 'access_token' in RokfinIE.access_mgmt_tokens and 'token_type' in RokfinIE.access_mgmt_tokens and headers and 'authorization' in headers:
            headers = headers.copy()
            headers['authorization'] = RokfinIE.access_mgmt_tokens['token_type'] + ' eyJh'
            self.write_debug('Invalidated access token')
        res = super()._download_webpage_handle(
            url_or_request, video_id, note=note, errnote=errnote, fatal=False,
            encoding=encoding, data=data, headers=headers, query=query,
            expected_status=(401,) if expected_status is None else (tuple(variadic(expected_status)) + (401,)))  # 401=Unauthorized
        if 'authorization' not in headers or try_get(res, lambda x: x[1].code) != 401 or (RokfinIE.access_mgmt_tokens or {}).get('refresh_token') is None:
            if res is False:
                return res
            json_string, urlh = res
            return self._parse_json(json_string, video_id, transform_source=transform_source, fatal=fatal), urlh
        headers = headers.copy()
        del headers['authorization']
        RokfinIE.access_mgmt_tokens = dict([(key, val) for (key, val) in RokfinIE.access_mgmt_tokens.items() if key not in ('access_token', 'expires_in', 'token_type')])
        RokfinIE.access_mgmt_tokens.update(self._refresh_OAuth_tokens(video_id, encoding=encoding) or {})
        self.write_debug(f'Updated tokens: {RokfinIE.access_mgmt_tokens.keys()}')
        if next((key for key in ['access_token', 'expires_in', 'refresh_expires_in', 'refresh_token', 'token_type', 'id_token', 'not-before-policy', 'session_state', 'scope'] if key not in RokfinIE.access_mgmt_tokens.keys()), None) is not None:
            self._logout()
            self._login()
        authorization_hdr_val = try_get(RokfinIE.access_mgmt_tokens, lambda tokens: tokens['token_type'] + ' ' + tokens['access_token'])
        if authorization_hdr_val:
            headers['authorization'] = authorization_hdr_val
            self.to_screen('authorization restored')
        else:
            self.to_screen('unable to restore authorization. Premium features may not be available')
        return super()._download_json_handle(
            url_or_request, video_id, note=note, errnote=errnote, transform_source=transform_source, fatal=fatal,
            encoding=encoding, data=data, headers=headers, query=query, expected_status=expected_status)

    def _authorized_download_json(
            self, url_or_request, video_id, transform_source=None, fatal=False,
            encoding=None, data=None, headers={}, query={}, expected_status=None):
        authorization_hdr_val = try_get(RokfinIE.access_mgmt_tokens, lambda tokens: tokens['token_type'] + ' ' + tokens['access_token'])
        if 'authorization' not in headers and authorization_hdr_val is not None:
            headers = headers.copy()
            headers['authorization'] = authorization_hdr_val
        return self._download_json(
            url_or_request, video_id, note='Downloading JSON metadata' + (' [logged in]' if 'authorization' in headers else ''),
            errnote='Unable to download JSON metadata' + (' [logged in]' if 'authorization' in headers else ''),
            transform_source=transform_source, fatal=fatal, encoding=encoding, data=data, headers=headers,
            query=query, expected_status=expected_status) or {}

    def _get_OAuth_tokens(self):
        PARTIAL_USER_CONSENT_URL_STEP_4_5 = urllib.parse.urlparse('https://secure.rokfin.com/auth/realms/rokfin-web/protocol/openid-connect/auth?client_id=web&redirect_uri=https%3A%2F%2Frokfin.com%2Fsilent-check-sso.html&response_mode=fragment&response_type=code&scope=openid&prompt=none')
        TOKEN_DISTRIBUTION_POINT_URL_STEP_6_7 = 'https://secure.rokfin.com/auth/realms/rokfin-web/protocol/openid-connect/token'

        # ---------------------------- CODE FLOW AUTHORIZATION ----------------------------
        # https://openid.net/specs/openid-connect-core-1_0.html#CodeFlowAuth (Sec. 3.1.1)

        # Steps 4 & 5 authorize yt-dlp to act on user's behalf.

        # random_str() came from https://www.rokfin.com/static/js/2.*.chunk.js
        def random_str():
            rnd_lst = [random.choice('0123456789abcdef') for _ in range(36)]
            rnd_lst[14] = '4'
            rnd_lst[19] = '0123456789abcdef'[3 & ord(rnd_lst[19]) | 8]
            rnd_lst[8] = rnd_lst[13] = rnd_lst[18] = rnd_lst[23] = '-'
            return ''.join(rnd_lst)

        user_consent_url_step_4_5 = PARTIAL_USER_CONSENT_URL_STEP_4_5._replace(query=urllib.parse.urlencode((lambda d: d.update(state=random_str(), nonce=random_str()) or d)(dict(urllib.parse.parse_qsl(PARTIAL_USER_CONSENT_URL_STEP_4_5.query))))).geturl()

        # By making this HTTP request, the user authorizes yt-dlp to act on the user's behalf:
        urlh = (self._download_webpage_handle(
            user_consent_url_step_4_5, None, note='granting user authorization', errnote='user authorization rejected by Rokfin', fatal=False, encoding='utf-8') or (None, None))[1]

        authorization_code = try_get(urlh, lambda http_resp: dict(urllib.parse.parse_qsl(urllib.parse.urldefrag(http_resp.geturl()).fragment))['code'])

        # Steps 6 & 7 request and acquire ID Token & Access Token:
        access_token = self._download_json(
            TOKEN_DISTRIBUTION_POINT_URL_STEP_6_7, None, note='getting access credentials', fatal=False, encoding='utf-8',
            data=urlencode_postdata({'code': authorization_code, 'grant_type': 'authorization_code', 'client_id': 'web', 'redirect_uri': 'https://rokfin.com/silent-check-sso.html'})) or {}

        if next((key for key in ['access_token', 'expires_in', 'refresh_expires_in', 'refresh_token', 'token_type', 'id_token', 'not-before-policy', 'session_state', 'scope'] if key not in access_token.keys()), None) is not None:
            self.report_warning('premium content may not be available: bad access token sent by Rokfin')
        else:
            try_get(datetime.datetime.now(), lambda current_time: self.write_debug(f'access token expires {datetime.datetime.strftime(current_time + datetime.timedelta(seconds=int_or_none(access_token["expires_in"])), "%d-%b-%Y %H:%M:%S")} (local time); refresh token expires {datetime.datetime.strftime(current_time + datetime.timedelta(seconds=int_or_none(access_token["refresh_expires_in"])), "%d-%b-%Y %H:%M:%S")} (local time)'))

        # Usage: --extractor-args "rokfin:print-user-info"'  # Mainly intended for testing.
        if self._configuration_arg('print_user_info', ie_key='rokfin'):
            self.to_screen(self._download_json('https://prod-api-v2.production.rokfin.com/api/v2/user/me', None, note='obtaining user info', errnote='could not obtain user info', fatal=False, headers={'authorization': f'{access_token["token_type"]} {access_token["access_token"]}'}))

        return access_token

    def _refresh_OAuth_tokens(
            self, video_id, note='Restoring lost authorization', errnote='Unable to restore authorization', fatal=False, encoding=None):
        TOKEN_DISTRIBUTION_POINT_URL_STEP_6_7 = 'https://secure.rokfin.com/auth/realms/rokfin-web/protocol/openid-connect/token'
        refresh_token = (RokfinIE.access_mgmt_tokens or {}).get('refresh_token')
        if not refresh_token:
            return False
        return super()._download_json(
            TOKEN_DISTRIBUTION_POINT_URL_STEP_6_7, video_id, note, errnote, fatal=fatal, encoding=encoding,
            data=urlencode_postdata({'grant_type': 'refresh_token', 'refresh_token': refresh_token, 'client_id': 'web'}))

    def _clear_cookies(self):
        try_get(self._downloader.cookiejar.clear, lambda f: f(domain='secure.rokfin.com'))


class RokfinPostIE(RokfinIE):
    IE_NAME = 'rokfin:post'
    _VALID_URL = r'https?://(?:www\.)?rokfin\.com/(?P<id>post/[^/]+)'
    _TESTS = [{
        'url': 'https://www.rokfin.com/post/57548/Mitt-Romneys-Crazy-Solution-To-Climate-Change',
        'info_dict': {
            'id': 'post/57548',
            'ext': 'mp4',
            'title': 'Mitt Romney\'s Crazy Solution To Climate Change',
            'thumbnail': 're:https://img.production.rokfin.com/.+',
            'upload_date': '20211023',
            'timestamp': 1634998029,
            'creator': 'Jimmy Dore',
            'channel': 'Jimmy Dore',
            'channel_id': 65429,
            'channel_url': 'https://rokfin.com/TheJimmyDoreShow',
            'duration': 213.0,
            'availability': 'public',
            'live_status': 'not_live'
        }
    }, {
        'url': 'https://rokfin.com/post/223/Julian-Assange-Arrested-Streaming-In-Real-Time',
        'info_dict': {
            'id': 'post/223',
            'ext': 'mp4',
            'title': 'Julian Assange Arrested: Streaming In Real Time',
            'thumbnail': 're:https://img.production.rokfin.com/.+',
            'upload_date': '20190412',
            'timestamp': 1555052644,
            'creator': 'Ron Placone',
            'channel': 'Ron Placone',
            'channel_id': 10,
            'channel_url': 'https://rokfin.com/RonPlacone',
            'availability': 'public',
            'live_status': 'not_live'
        }
    }]

    def _real_extract(self, url_from_user):
        video_id = self._match_id(url_from_user)
        metadata = self._authorized_download_json(self._SINGLE_VIDEO_META_DATA_BASE_URL + video_id, video_id)
        video_formats_url = url_or_none(traverse_obj(metadata, ('content', 'contentUrl')))
        availability = self._availability(
            is_private=False,
            needs_premium=True if metadata.get('premiumPlan') == 1 else False if metadata.get('premiumPlan') == 0 else None,
            # premiumPlan = 0 - no-premium content
            # premiumPlan = 1 - premium-only content
            needs_subscription=False, needs_auth=False, is_unlisted=False)

        if metadata.get('premiumPlan') not in (0, 1, None):
            self.report_warning(f'unknown availability code: {metadata.get("premiumPlan")}. Rokfin extractor should be updated')

        if video_formats_url:
            if try_get(video_formats_url, lambda x: urllib.parse.urlparse(x).path.endswith('.m3u8')):
                frmts, subs = self._extract_m3u8_formats_and_subtitles(m3u8_url=video_formats_url, video_id=video_id, fatal=False)
            else:
                frmts = [{'url': video_formats_url}]
                subs = None
        else:
            frmts = None
            subs = None

        if not frmts:
            if availability == 'premium_only':
                self.raise_login_required('premium content', True, method='password')
            elif video_formats_url:
                self.raise_no_formats(msg='missing video data', video_id=video_id, expected=True)
            else:
                self.raise_no_formats(msg='missing/bad link to video data', video_id=video_id, expected=True)

        self._sort_formats(frmts)
        return {
            'id': video_id,
            'title': str_or_none(traverse_obj(metadata, ('content', 'contentTitle'))),
            'webpage_url': self._SINGLE_VIDEO_BASE_WEB_URL + video_id,
            # webpage_url = url_from_user minus the final part. The final part exists solely for human consumption and is otherwise irrelevant.
            'live_status': 'not_live',
            'duration': float_or_none(traverse_obj(metadata, ('content', 'duration'))),
            'thumbnail': url_or_none(traverse_obj(metadata, ('content', 'thumbnailUrl1'))),
            'description': str_or_none(traverse_obj(metadata, ('content', 'contentDescription'))),
            'like_count': int_or_none(metadata.get('likeCount')),
            'dislike_count': int_or_none(metadata.get('dislikeCount')),
            # 'comment_count': metadata.get('numComments'), # Uncomment when Rf corrects 'numComments' field.
            'availability': availability,
            'creator': str_or_none(traverse_obj(metadata, ('createdBy', 'name'))),
            'channel_id': traverse_obj(metadata, ('createdBy', 'id')),
            'channel': str_or_none(traverse_obj(metadata, ('createdBy', 'name'))),
            'channel_url': try_get(metadata, lambda x: url_or_none(self._SINGLE_VIDEO_BASE_WEB_URL + x['createdBy']['username'])),
            'timestamp': unified_timestamp(metadata.get('creationDateTime')),
            'tags': metadata.get('tags', []),
            'formats': frmts or [],
            'subtitles': subs or {},
            '__post_extractor': self.extract_comments(video_id=video_id)
        }

    def _get_comments(self, video_id):
        _COMMENTS_BASE_URL = 'https://prod-api-v2.production.rokfin.com/api/v2/public/comment'
        _COMMENTS_PER_REQUEST = 50  # 50 is the maximum Rokfin permits per request.
        pages_total = None

        for page_n in itertools.count(0):
            raw_comments = self._download_json(
                f'{_COMMENTS_BASE_URL}?postId={video_id[5:]}&page={page_n}&size={_COMMENTS_PER_REQUEST}',
                video_id, note=f'Downloading viewer comments (page {page_n + 1}' + (f' of {pages_total}' if pages_total else '') + ')',
                fatal=False) or {}
            pages_total = int_or_none(raw_comments.get('totalPages'))
            is_last_page = bool_or_none(raw_comments.get('last'))
            max_page_count_reached = None if pages_total is None else (page_n + 1 >= pages_total)

            for comment in raw_comments.get('content', []):
                comment_text = str_or_none(comment.get('comment'))

                if comment_text is None:
                    continue

                yield {
                    'text': comment_text,
                    'author': str_or_none(comment.get('name')),
                    'id': comment.get('commentId'),
                    'author_id': comment.get('userId'),
                    'parent': 'root',
                    'like_count': int_or_none(comment.get('numLikes')),
                    'dislike_count': int_or_none(comment.get('numDislikes')),
                    'timestamp': unified_timestamp(comment.get('postedAt'))
                }

            if is_last_page or max_page_count_reached or ((is_last_page is None) and (max_page_count_reached is None)):
                return


class RokfinStreamIE(RokfinIE):
    IE_NAME = 'rokfin:stream'
    _VALID_URL = r'https?://(?:www\.)?rokfin\.com/(?P<id>stream/[^/]+)'
    _TESTS = [{
        'url': 'https://www.rokfin.com/stream/10543/Its-A-Crazy-Mess-Regional-Director-Blows-Whistle-On-Pfizers-Vaccine-Trial-Data',
        'info_dict': {
            'id': 'stream/10543',
            'ext': 'mp4',
            'title': '"It\'s A Crazy Mess" Regional Director Blows Whistle On Pfizer\'s Vaccine Trial Data',
            'thumbnail': 'https://img.production.rokfin.com/eyJidWNrZXQiOiJya2ZuLXByb2R1Y3Rpb24tbWVkaWEiLCJrZXkiOiIvdXNlci81Mzg1Ni9wb3N0L2Y0ZWY4YzQyLTdiMmYtNGZhYy05MDIzLTg4YmI5ZTNjY2ZiNi90aHVtYm5haWwvMDU4NjE1MTktNjE5NS00NTY4LWI4ZDAtNTdhZGUxMmZiZDcyIiwiZWRpdHMiOnsicmVzaXplIjp7IndpZHRoIjo2MDAsImhlaWdodCI6MzM3LCJmaXQiOiJjb3ZlciJ9fX0=',
            'uploader_id': 53856,
            'description': 'md5:324ce2d3e3b62e659506409e458b9d8e',
            'creator': 'Ryan Cristián',
            'channel': 'Ryan Cristián',
            'channel_id': 53856,
            'channel_url': 'https://rokfin.com/TLAVagabond',
            'availability': 'public',
            'is_live': False,
            'was_live': True,
            'live_status': 'was_live',
            'timestamp': 1635874720,
            'release_timestamp': 1635874720,
            'release_date': '20211102',
            'upload_date': '20211102'
        }
    }]

    def _real_extract(self, url_from_user):
        if self.get_param('live_from_start'):
            self.report_warning('--live-from-start is unsupported')

        video_id = self._match_id(url_from_user)
        metadata = self._authorized_download_json(self._SINGLE_VIDEO_META_DATA_BASE_URL + video_id, video_id)
        availability = self._availability(
            needs_premium=bool(metadata.get('premium')) if metadata.get('premium') in (True, False, 0, 1) else None,
            is_private=False, needs_subscription=False, needs_auth=False, is_unlisted=False)
        m3u8_url = url_or_none(metadata.get('url'))
        stream_scheduled_for = try_get(metadata, lambda x: datetime.datetime.strptime(x.get('scheduledAt'), '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc))
        # 'scheduledAt' gets set to None after the stream becomes live.
        stream_ended_at = try_get(
            metadata,
            lambda x: datetime.datetime.strptime(x.get('stoppedAt'), '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc))
        # 'stoppedAt' is null unless the stream is finished. 'stoppedAt' likely contains an incorrect value,
        # so what matters to us is whether or not this field is *present*.

        if m3u8_url:
            frmts, subs = self._extract_m3u8_formats_and_subtitles(m3u8_url=m3u8_url, video_id=video_id, fatal=False, live=(stream_scheduled_for is None and stream_ended_at is None))
        else:
            frmts = None
            subs = None

        if not frmts:
            if stream_scheduled_for:
                # The stream is pending.
                def error_message(stream_scheduled_for, availability):
                    time_diff = (stream_scheduled_for - datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)) if stream_scheduled_for >= datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc) else (datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc) - stream_scheduled_for)
                    main_part = (f'{time_diff.days}D+' if time_diff.days else '') + f'{(time_diff.seconds // 3600):02}:{((time_diff.seconds % 3600) // 60):02}:{((time_diff.seconds % 3600) % 60):02}'

                    if stream_scheduled_for >= datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc):
                        return 'live in ' + main_part + (' (premium-only)' if availability == 'premium_only' else '') + '. Try --wait-for-video'
                    else:
                        return 'not live; ' + main_part + ' behind schedule' + (' (premium-only)' if availability == 'premium_only' else '') + '. Try --wait-for-video'
                self.raise_no_formats(error_message(stream_scheduled_for, availability), video_id=video_id, expected=True)
            elif availability == 'premium_only':
                self.raise_login_required('premium content', True, method='password')
            elif m3u8_url:
                self.raise_no_formats(msg='missing video data', video_id=video_id, expected=True)
            else:
                self.raise_no_formats(msg='missing/bad link to video data', video_id=video_id, expected=True)

            # --wait-for-video causes raise_no_formats(... expected=True ...) to print a warning message
            # and exit without raising ExtractorError.

        # 'postedAtMilli' shows when the stream (live or pending) appeared on Rokfin. As soon as the pending stream goes live,
        # the value of 'postedAtMilli' changes to reflect the stream's starting time.
        stream_started_at_timestamp = try_get(metadata, lambda x: x.get('postedAtMilli') / 1000) if stream_scheduled_for is None else None
        stream_started_at = try_get(stream_started_at_timestamp, lambda x: datetime.datetime.utcfromtimestamp(x).replace(tzinfo=datetime.timezone.utc))
        # The stream's actual (if live or finished) or announced (if pending) starting time:
        release_timestamp = try_get(stream_scheduled_for, lambda x: unified_timestamp(datetime.datetime.strftime(x, '%Y-%m-%dT%H:%M:%S'))) or stream_started_at_timestamp

        self._sort_formats(frmts)
        return {
            'id': video_id,
            'title': str_or_none(metadata.get('title')),
            'webpage_url': self._SINGLE_VIDEO_BASE_WEB_URL + video_id,
            # webpage_url = url_from_user minus the final part. The final part exists solely for human consumption and is otherwise irrelevant.
            'manifest_url': m3u8_url,
            'thumbnail': url_or_none(metadata.get('thumbnail')),
            'description': str_or_none(metadata.get('description')),
            'like_count': int_or_none(metadata.get('likeCount')),
            'dislike_count': int_or_none(metadata.get('dislikeCount')),
            'creator': str_or_none(traverse_obj(metadata, ('creator', 'name'))),
            'channel': str_or_none(traverse_obj(metadata, ('creator', 'name'))),
            'channel_id': traverse_obj(metadata, ('creator', 'id')),
            'uploader_id': traverse_obj(metadata, ('creator', 'id')),
            'channel_url': try_get(metadata, lambda x: url_or_none(self._SINGLE_VIDEO_BASE_WEB_URL + traverse_obj(x, ('creator', 'username')))),
            'availability': availability,
            'tags': metadata.get('tags', []),
            'live_status': 'was_live' if (stream_scheduled_for is None) and (stream_ended_at is not None) else
                           'is_live' if stream_scheduled_for is None else  # stream_scheduled_for=stream_ended_at=None
                           'is_upcoming' if stream_ended_at is None else   # stream_scheduled_for is not None
                           None,  # Both stream_scheduled_for and stream_ended_at are not None: inconsistent meta data.
            # Remove the 'False and' part when Rokfin corrects the 'stoppedAt' field:
            'duration': (stream_ended_at - stream_started_at).total_seconds() if False and stream_started_at and stream_ended_at else None,
            'timestamp': release_timestamp,
            'release_timestamp': release_timestamp,
            'formats': frmts or [],
            'subtitles': subs or {},
            '__post_extractor': self.extract_comments(video_id=video_id)
        }

    def _get_comments(self, video_id):
        raise ExtractorError(msg='downloading stream chat is unsupported', expected=True)


class RokfinPlaylistIE(RokfinIE):
    def _get_video_data(self, json_data, video_base_url):
        def real_get_video_data(content):
            media_type = content.get('mediaType')
            fn = try_get(media_type, lambda y: {
                'video': lambda x: {'id': x['id'], 'url': f'{video_base_url}post/{x["id"]}'},
                'audio': lambda x: {'id': x['id'], 'url': f'{video_base_url}post/{x["id"]}'},
                'stream': lambda x: {'id': x['mediaId'], 'url': f'{video_base_url}stream/{x["mediaId"]}'},
                'dead_stream': lambda x: {'id': x['mediaId'], 'url': f'{video_base_url}stream/{x["mediaId"]}'},
                'stack': lambda x: {'id': x['mediaId'], 'url': f'{video_base_url}stack/{x["mediaId"]}'},
                'article': lambda x: {'id': x['mediaId'], 'url': f'{video_base_url}article/{x["mediaId"]}'},
                'ranking': lambda x: {'id': x['mediaId'], 'url': f'{video_base_url}ranking/{x["mediaId"]}'}
            }[y])

            if fn is None:
                self.to_screen('non-downloadable content skipped' + ('' if self.get_param('verbose') else '. Use --verbose for details'))
                self.write_debug(f'unprocessed entry: {content}')
                return

            video_data = try_get(content, fn)
            if video_data is None:
                self.write_debug(f'{media_type}: could not process content entry: {content}')
                return

            video_data['url'] = url_or_none(video_data.get('url'))

            if video_data.get('url') is None:
                self.to_screen('entry with missing or malformed URL skipped' + ('' if self.get_param('verbose') else '. Use --verbose for details'))
                self.write_debug(f'{media_type}: could not process content entry: {content}')
                return

            video_data['title'] = str_or_none(traverse_obj(content, ('content', 'contentTitle')))
            return video_data

        for content in json_data.get('content', []):
            video_data = real_get_video_data(content)

            if not video_data:
                continue

            yield self.url_result(url=video_data.get('url'), video_id=video_data.get('id'), video_title=str_or_none(video_data.get('title')))


# Stack is an aggregation of content. On the website, stacks are shown as a collection of videos
# or other materials stacked over each other.
class RokfinStackIE(RokfinPlaylistIE):
    IE_NAME = 'rokfin:stack'
    _VALID_URL = r'https?://(?:www\.)?rokfin\.com/stack/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://www.rokfin.com/stack/271/Tulsi-Gabbard-Portsmouth-Townhall-FULL--Feb-9-2020',
        'info_dict': {
            'id': 271,
            'ext': 'mp4'
        }
    }]

    def _real_extract(self, url_from_user):
        _META_VIDEO_DATA_BASE_URL = 'https://prod-api-v2.production.rokfin.com/api/v2/public/stack/'
        _VIDEO_BASE_URL = 'https://rokfin.com/'
        _RECOMMENDED_STACK_BASE_URL = 'https://rokfin.com/stack/'
        list_id = self._match_id(url_from_user)
        return self.playlist_result(
            entries=self._get_video_data(
                json_data=self._authorized_download_json(_META_VIDEO_DATA_BASE_URL + list_id, list_id), video_base_url=_VIDEO_BASE_URL),
            playlist_id=list_id, webpage_url=_RECOMMENDED_STACK_BASE_URL + list_id, original_url=url_from_user, multi_video=True)
        # webpage_url = url_from_user minus the final part. The final part exists solely for human consumption and is otherwise irrelevant.


class RokfinChannelIE(RokfinPlaylistIE):
    IE_NAME = 'rokfin:channel'
    _VALID_URL = r'https?://(?:www\.)?rokfin\.com/(?!((feed/?)|(discover/?)|(channels/?))$)(?P<id>[^/]+)/?$'
    _TESTS = [{
        'url': 'https://rokfin.com/TheConvoCouch',
        'info_dict': {
            'id': 12071,
            'description': 'Independent media providing news and commentary in our studio but also on the ground. We stand by our principles regardless of party lines & are willing to sit down and have convos with most anybody.',
            'ext': 'mp4'
        }
    }]

    def _real_extract(self, url_from_user):
        _CHANNEL_BASE_URL = 'https://prod-api-v2.production.rokfin.com/api/v2/public/user/'
        _RECOMMENDED_CHANNEL_BASE_URL = 'https://rokfin.com/'

        def dnl_video_meta_data_incrementally(channel_id, tab, channel_username, channel_base_url):
            _VIDEO_BASE_URL = 'https://rokfin.com/'
            _METADATA_BASE_URL = 'https://prod-api-v2.production.rokfin.com/api/v2/public/post/search/'
            _ENTRIES_PER_REQUEST = 50  # 50 is the maximum Rokfin permits per request.
            pages_total = None

            for page_n in itertools.count(0):
                if tab in ('posts', 'top'):
                    data_url = f'{channel_base_url}{channel_username}/{tab}?page={page_n}&size={_ENTRIES_PER_REQUEST}'
                else:
                    data_url = f'{_METADATA_BASE_URL}{tab}?page={page_n}&size={_ENTRIES_PER_REQUEST}&creator={channel_id}'

                metadata = self._download_json(data_url, channel_username, note=f'Downloading video metadata (page {page_n + 1}' + (f' of {pages_total}' if pages_total else '') + ')', fatal=False, headers=try_get(RokfinIE.access_mgmt_tokens, lambda tokens: {'authorization': tokens['token_type'] + ' ' + tokens['access_token']}) or {}) or {}

                yield from self._get_video_data(json_data=metadata, video_base_url=_VIDEO_BASE_URL)

                pages_total = metadata.get('totalPages')
                is_last_page = try_get(metadata, lambda x: x['last'] is True)
                max_page_count_reached = try_get(pages_total, lambda x: page_n + 1 >= x)

                if is_last_page or max_page_count_reached or ((is_last_page is None) and (max_page_count_reached is None)):
                    return []
                # The final and-condition is a mere safety check.

        tabs = self._configuration_arg('content')
        tab_dic = {'new': 'posts', 'top': 'top', 'videos': 'video', 'podcasts': 'audio', 'streams': 'stream', 'articles': 'article', 'rankings': 'ranking', 'stacks': 'stack'}

        if len(tabs) > 1 or (len(tabs) == 1 and tabs[0] not in tab_dic.keys()):
            raise ExtractorError(msg='usage: --extractor-args "rokfinchannel:content=[new|top|videos|podcasts|streams|articles|rankings|stacks]"', expected=True)

        channel_username = self._match_id(url_from_user)
        channel_info = self._download_json(_CHANNEL_BASE_URL + channel_username, channel_username, fatal=False, headers=try_get(RokfinIE.access_mgmt_tokens, lambda tokens: {'authorization': tokens['token_type'] + ' ' + tokens['access_token']}) or {}) or {}
        channel_id = channel_info.get('id')

        if channel_id:
            return self.playlist_result(
                entries=dnl_video_meta_data_incrementally(tab=tab_dic[tabs[0] if tabs else "new"], channel_id=channel_id, channel_username=channel_username, channel_base_url=_CHANNEL_BASE_URL),
                playlist_id=channel_id, playlist_title=channel_username, playlist_description=str_or_none(channel_info.get('description')),
                webpage_url=_RECOMMENDED_CHANNEL_BASE_URL + channel_username, original_url=url_from_user)
            # webpage_url = url_from_user minus the final part. The final part exists solely for human consumption and is otherwise irrelevant.
        else:
            raise ExtractorError(msg='unknown channel', expected=True)


# E.g.: rkfnsearch5:"zelenko" or rkfnsearch5:"\"dr mollie james\""
class RokfinSearchIE(SearchInfoExtractor):
    IE_NAME = 'rokfin:search'
    _SEARCH_KEY = 'rkfnsearch'

    service_url = None
    service_access_key = None

    def _get_n_results(self, query, n_results):
        def dnl_video_meta_data_incrementally(query, n_results):
            ENTRIES_PER_PAGE = 100
            max_pages_to_download = None if n_results == float('inf') else math.ceil(n_results / ENTRIES_PER_PAGE)
            pages_total = None  # The # of pages containing search results, as reported by Rokfin.
            pages_total_printed = False  # Makes sure pages_total is not printed more than once.
            results_total_printed = False  # Makes sure the total number of search results is not printed more than once.
            yielded_result_counter = 0  # How many search results have been yielded?
            POST_DATA = {'query': query, 'page': {'size': ENTRIES_PER_PAGE}, 'facets': {'content_type': {'type': 'value', 'size': ENTRIES_PER_PAGE}, 'creator_name': {'type': 'value', 'size': ENTRIES_PER_PAGE}, 'premium_plan': {'type': 'value', 'size': ENTRIES_PER_PAGE}}, 'result_fields': {'creator_twitter': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'content_id': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'creator_username': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'creator_instagram': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'post_comments': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'post_text': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'content_description': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'content_title': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'post_updated_at': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'creator_youtube': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'content_type': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'creator_name': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'creator_facebook': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'id': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'premium_plan': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}}}

            for page_n in itertools.count(1) if n_results == float('inf') else range(1, max_pages_to_download + 1):
                POST_DATA['page']['current'] = page_n

                if RokfinSearchIE.service_url and RokfinSearchIE.service_access_key:
                    # Access has already been established.
                    srch_res = self._download_json(
                        RokfinSearchIE.service_url, self._SEARCH_KEY, headers={'authorization': RokfinSearchIE.service_access_key},
                        data=json.dumps(POST_DATA).encode('utf-8'), encoding='utf-8',
                        note=f'Downloading search results (page {page_n}' + (f' of {min(pages_total, max_pages_to_download)}' if pages_total is not None and max_pages_to_download is not None else '') + ')',
                        fatal=True)
                else:
                    self.write_debug(msg='gaining access')

                    # Try all possible combinations between service_urls and service_access_keys and see which one works.
                    # This should succeed on the first attempt, but no one knows for sure.
                    for service_url, service_access_key in (lambda p: itertools.product(p[0], p[1]))(self._get_access_credentials()):
                        self.write_debug(msg=f'attempting to download 1st batch of search results from "{service_url}" using access key "{service_access_key}"')
                        srch_res = self._download_json(
                            service_url, self._SEARCH_KEY, headers={'authorization': service_access_key}, data=json.dumps(POST_DATA).encode('utf-8'),
                            encoding='utf-8', note='Downloading search results (page 1)', fatal=False) or {}

                        if srch_res:
                            RokfinSearchIE.service_url = service_url
                            RokfinSearchIE.service_access_key = service_access_key
                            self.write_debug(msg='download succeeded, access gained')
                            break
                        else:
                            self.write_debug(msg='download failed: access denied. Still trying...')
                    else:
                        raise ExtractorError(msg='couldn\'t gain access', expected=False)

                def get_video_data(content):
                    BASE_URL = 'https://rokfin.com/'
                    content_type = try_get(content, lambda x: x['content_type']['raw'])
                    fn = try_get(content_type, lambda y: {
                        'video': lambda x: {'id': int(x['id']['raw']), 'url': f'{BASE_URL}post/{int(x["id"]["raw"])}'},
                        'audio': lambda x: {'id': int(x['id']['raw']), 'url': f'{BASE_URL}post/{int(x["id"]["raw"])}'},
                        'stream': lambda x: {'id': int(x['content_id']['raw']), 'url': f'{BASE_URL}stream/{int(x["content_id"]["raw"])}'},
                        'dead_stream': lambda x: {'id': int(x['content_id']['raw']), 'url': f'{BASE_URL}stream/{int(x["content_id"]["raw"])}'},
                        'stack': lambda x: {'id': int(x['content_id']['raw']), 'url': f'{BASE_URL}stack/{int(x["content_id"]["raw"])}'},
                        'article': lambda x: {'id': int(x['content_id']['raw']), 'url': f'{BASE_URL}article/{int(x["content_id"]["raw"])}'},
                        'ranking': lambda x: {'id': int(x['content_id']['raw']), 'url': f'{BASE_URL}ranking/{int(x["content_id"]["raw"])}'}
                    }[y])

                    if fn is None:
                        self.to_screen('non-downloadable content ignored' + ('' if self.get_param('verbose') else '. Use --verbose for details'))
                        self.write_debug(f'unprocessed entry: {content}')
                        return

                    video_data = try_get(content, fn)
                    if video_data is None:
                        self.write_debug(f'{content_type}: could not process content entry: {content}')
                        return

                    video_data['url'] = url_or_none(video_data.get('url'))

                    if video_data.get('url') is None:
                        self.to_screen('entry with missing or malformed URL ignored' + ('' if self.get_param('verbose') else '. Use --verbose for details'))
                        self.write_debug(f'{content_type}: could not process content entry: {content}')
                        return

                    video_data['title'] = str_or_none(traverse_obj(content, ('content_title', 'raw')))
                    return video_data

                pages_total = int_or_none(traverse_obj(srch_res, ('meta', 'page', 'total_pages')))
                if pages_total <= 0 or not query:
                    return []
                if pages_total is None:
                    self.report_warning(msg='unknown total # of pages of search results. This may be a bug', only_once=True)
                elif (pages_total_printed is False) and max_pages_to_download is not None:
                    self.to_screen(msg=f'Pages to download: {min(pages_total, max_pages_to_download)}')
                    pages_total_printed = True

                results_total = int_or_none(traverse_obj(srch_res, ('meta', 'page', 'total_results')))
                if results_total is None:
                    self.report_warning(msg='unknown total # of search results. This may be a bug', only_once=True)
                elif results_total_printed is False:
                    self.to_screen(msg=f'Search results available: {results_total}')
                    results_total_printed = True

                for content in srch_res.get('results', []):
                    video_data = get_video_data(content)

                    if not video_data:
                        continue

                    yield self.url_result(url=video_data.get('url'), video_id=video_data.get('id'), video_title=video_data.get('title'))
                    yielded_result_counter += 1

                    if yielded_result_counter >= min(n_results, results_total or float('inf')) or (n_results == float('inf') and results_total is None):
                        # If Rokfin (unexpectedly) does not report the total # of search results,
                        # and n_results == inf, then the downloading loop has no definitive stopping point
                        # and could, theoritically, execute indefinitely. To prevent this, we proactively
                        # quit the loop.
                        #
                        # The good news is: this is an unlikely scenario and should not occur routinely.
                        if n_results == float('inf') and results_total is None:
                            self.report_warning(msg='please specify a finite number of search results, e.g. 100, and re-run. Stopping the downloading process prematurely to avoid an infinite loop')

                        return

                if page_n >= min(pages_total or float('inf'), max_pages_to_download or float('inf')) or (pages_total is None and max_pages_to_download is None):
                    return

        return self.playlist_result(entries=dnl_video_meta_data_incrementally(query, n_results), playlist_id=query)

    def _get_access_credentials(self):
        if RokfinSearchIE.service_url and RokfinSearchIE.service_access_key:
            return

        STARTING_WP_URL = 'https://rokfin.com/discover'
        SERVICE_URL_PATH = '/api/as/v1/engines/rokfin-search/search.json'
        BASE_URL = 'https://rokfin.com'

        # 'Not Found' is the expected outcome here.
        notfound_err_page = self._download_webpage(STARTING_WP_URL, self._SEARCH_KEY, expected_status=404, fatal=False)

        js = ''
        # <script src="/static/js/<filename>">
        for m in try_get(notfound_err_page, lambda x: re.finditer(r'<script\s+[^>]*?src\s*=\s*"(?P<path>/static/js/[^">]*)"[^>]*>', x)) or []:
            try:
                js = js + try_get(m, lambda x: self._download_webpage(BASE_URL + x.group('path'), self._SEARCH_KEY, note='Downloading JavaScript file', fatal=False))
            except TypeError:  # Happens when try_get returns a non-string.
                pass

        service_urls = []
        services_access_keys = []
        for m in re.finditer(r'(REACT_APP_SEARCH_KEY\s*:\s*"(?P<key>[^"]*)")|(REACT_APP_ENDPOINT_BASE\s*:\s*"(?P<url>[^"]*)")', js):
            if m.group('url'):
                service_urls.append(m.group('url') + SERVICE_URL_PATH)
            elif m.group('key'):
                services_access_keys.append('Bearer ' + m.group('key'))

        return (service_urls, services_access_keys)
