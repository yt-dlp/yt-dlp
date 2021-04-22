# coding: utf-8

from __future__ import unicode_literals

import calendar
import hashlib
import itertools
import json
import os.path
import random
import re
import time
import traceback

from .common import InfoExtractor, SearchInfoExtractor
from ..compat import (
    compat_chr,
    compat_HTTPError,
    compat_parse_qs,
    compat_str,
    compat_urllib_parse_unquote_plus,
    compat_urllib_parse_urlencode,
    compat_urllib_parse_urlparse,
    compat_urlparse,
)
from ..jsinterp import JSInterpreter
from ..utils import (
    bool_or_none,
    clean_html,
    dict_get,
    datetime_from_str,
    error_to_compat_str,
    ExtractorError,
    format_field,
    float_or_none,
    int_or_none,
    mimetype2ext,
    parse_codecs,
    parse_duration,
    qualities,
    remove_start,
    smuggle_url,
    str_or_none,
    str_to_int,
    try_get,
    unescapeHTML,
    unified_strdate,
    unsmuggle_url,
    update_url_query,
    url_or_none,
    urlencode_postdata,
    urljoin
)


def parse_qs(url):
    return compat_urlparse.parse_qs(compat_urlparse.urlparse(url).query)


class YoutubeBaseInfoExtractor(InfoExtractor):
    """Provide base functions for Youtube extractors"""
    _LOGIN_URL = 'https://accounts.google.com/ServiceLogin'
    _TWOFACTOR_URL = 'https://accounts.google.com/signin/challenge'

    _LOOKUP_URL = 'https://accounts.google.com/_/signin/sl/lookup'
    _CHALLENGE_URL = 'https://accounts.google.com/_/signin/sl/challenge'
    _TFA_URL = 'https://accounts.google.com/_/signin/challenge?hl=en&TL={0}'

    _RESERVED_NAMES = (
        r'channel|c|user|playlist|watch|w|v|embed|e|watch_popup|'
        r'movies|results|shared|hashtag|trending|feed|feeds|'
        r'storefront|oops|index|account|reporthistory|t/terms|about|upload|signin|logout')

    _NETRC_MACHINE = 'youtube'
    # If True it will raise an error if no login info is provided
    _LOGIN_REQUIRED = False

    _PLAYLIST_ID_RE = r'(?:(?:PL|LL|EC|UU|FL|RD|UL|TL|PU|OLAK5uy_)[0-9A-Za-z-_]{10,}|RDMM|WL|LL|LM)'

    def _login(self):
        """
        Attempt to log in to YouTube.
        True is returned if successful or skipped.
        False is returned if login failed.

        If _LOGIN_REQUIRED is set and no authentication was provided, an error is raised.
        """
        username, password = self._get_login_info()
        # No authentication to be performed
        if username is None:
            if self._LOGIN_REQUIRED and self._downloader.params.get('cookiefile') is None:
                raise ExtractorError('No login info available, needed for using %s.' % self.IE_NAME, expected=True)
            # if self._downloader.params.get('cookiefile'):  # TODO remove 'and False' later - too many people using outdated cookies and open issues, remind them.
            #     self.to_screen('[Cookies] Reminder - Make sure to always use up to date cookies!')
            return True

        login_page = self._download_webpage(
            self._LOGIN_URL, None,
            note='Downloading login page',
            errnote='unable to fetch login page', fatal=False)
        if login_page is False:
            return

        login_form = self._hidden_inputs(login_page)

        def req(url, f_req, note, errnote):
            data = login_form.copy()
            data.update({
                'pstMsg': 1,
                'checkConnection': 'youtube',
                'checkedDomains': 'youtube',
                'hl': 'en',
                'deviceinfo': '[null,null,null,[],null,"US",null,null,[],"GlifWebSignIn",null,[null,null,[]]]',
                'f.req': json.dumps(f_req),
                'flowName': 'GlifWebSignIn',
                'flowEntry': 'ServiceLogin',
                # TODO: reverse actual botguard identifier generation algo
                'bgRequest': '["identifier",""]',
            })
            return self._download_json(
                url, None, note=note, errnote=errnote,
                transform_source=lambda s: re.sub(r'^[^[]*', '', s),
                fatal=False,
                data=urlencode_postdata(data), headers={
                    'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
                    'Google-Accounts-XSRF': 1,
                })

        def warn(message):
            self.report_warning(message)

        lookup_req = [
            username,
            None, [], None, 'US', None, None, 2, False, True,
            [
                None, None,
                [2, 1, None, 1,
                 'https://accounts.google.com/ServiceLogin?passive=true&continue=https%3A%2F%2Fwww.youtube.com%2Fsignin%3Fnext%3D%252F%26action_handle_signin%3Dtrue%26hl%3Den%26app%3Ddesktop%26feature%3Dsign_in_button&hl=en&service=youtube&uilel=3&requestPath=%2FServiceLogin&Page=PasswordSeparationSignIn',
                 None, [], 4],
                1, [None, None, []], None, None, None, True
            ],
            username,
        ]

        lookup_results = req(
            self._LOOKUP_URL, lookup_req,
            'Looking up account info', 'Unable to look up account info')

        if lookup_results is False:
            return False

        user_hash = try_get(lookup_results, lambda x: x[0][2], compat_str)
        if not user_hash:
            warn('Unable to extract user hash')
            return False

        challenge_req = [
            user_hash,
            None, 1, None, [1, None, None, None, [password, None, True]],
            [
                None, None, [2, 1, None, 1, 'https://accounts.google.com/ServiceLogin?passive=true&continue=https%3A%2F%2Fwww.youtube.com%2Fsignin%3Fnext%3D%252F%26action_handle_signin%3Dtrue%26hl%3Den%26app%3Ddesktop%26feature%3Dsign_in_button&hl=en&service=youtube&uilel=3&requestPath=%2FServiceLogin&Page=PasswordSeparationSignIn', None, [], 4],
                1, [None, None, []], None, None, None, True
            ]]

        challenge_results = req(
            self._CHALLENGE_URL, challenge_req,
            'Logging in', 'Unable to log in')

        if challenge_results is False:
            return

        login_res = try_get(challenge_results, lambda x: x[0][5], list)
        if login_res:
            login_msg = try_get(login_res, lambda x: x[5], compat_str)
            warn(
                'Unable to login: %s' % 'Invalid password'
                if login_msg == 'INCORRECT_ANSWER_ENTERED' else login_msg)
            return False

        res = try_get(challenge_results, lambda x: x[0][-1], list)
        if not res:
            warn('Unable to extract result entry')
            return False

        login_challenge = try_get(res, lambda x: x[0][0], list)
        if login_challenge:
            challenge_str = try_get(login_challenge, lambda x: x[2], compat_str)
            if challenge_str == 'TWO_STEP_VERIFICATION':
                # SEND_SUCCESS - TFA code has been successfully sent to phone
                # QUOTA_EXCEEDED - reached the limit of TFA codes
                status = try_get(login_challenge, lambda x: x[5], compat_str)
                if status == 'QUOTA_EXCEEDED':
                    warn('Exceeded the limit of TFA codes, try later')
                    return False

                tl = try_get(challenge_results, lambda x: x[1][2], compat_str)
                if not tl:
                    warn('Unable to extract TL')
                    return False

                tfa_code = self._get_tfa_info('2-step verification code')

                if not tfa_code:
                    warn(
                        'Two-factor authentication required. Provide it either interactively or with --twofactor <code>'
                        '(Note that only TOTP (Google Authenticator App) codes work at this time.)')
                    return False

                tfa_code = remove_start(tfa_code, 'G-')

                tfa_req = [
                    user_hash, None, 2, None,
                    [
                        9, None, None, None, None, None, None, None,
                        [None, tfa_code, True, 2]
                    ]]

                tfa_results = req(
                    self._TFA_URL.format(tl), tfa_req,
                    'Submitting TFA code', 'Unable to submit TFA code')

                if tfa_results is False:
                    return False

                tfa_res = try_get(tfa_results, lambda x: x[0][5], list)
                if tfa_res:
                    tfa_msg = try_get(tfa_res, lambda x: x[5], compat_str)
                    warn(
                        'Unable to finish TFA: %s' % 'Invalid TFA code'
                        if tfa_msg == 'INCORRECT_ANSWER_ENTERED' else tfa_msg)
                    return False

                check_cookie_url = try_get(
                    tfa_results, lambda x: x[0][-1][2], compat_str)
            else:
                CHALLENGES = {
                    'LOGIN_CHALLENGE': "This device isn't recognized. For your security, Google wants to make sure it's really you.",
                    'USERNAME_RECOVERY': 'Please provide additional information to aid in the recovery process.',
                    'REAUTH': "There is something unusual about your activity. For your security, Google wants to make sure it's really you.",
                }
                challenge = CHALLENGES.get(
                    challenge_str,
                    '%s returned error %s.' % (self.IE_NAME, challenge_str))
                warn('%s\nGo to https://accounts.google.com/, login and solve a challenge.' % challenge)
                return False
        else:
            check_cookie_url = try_get(res, lambda x: x[2], compat_str)

        if not check_cookie_url:
            warn('Unable to extract CheckCookie URL')
            return False

        check_cookie_results = self._download_webpage(
            check_cookie_url, None, 'Checking cookie', fatal=False)

        if check_cookie_results is False:
            return False

        if 'https://myaccount.google.com/' not in check_cookie_results:
            warn('Unable to log in')
            return False

        return True

    def _initialize_consent(self):
        cookies = self._get_cookies('https://www.youtube.com/')
        if cookies.get('__Secure-3PSID'):
            return
        consent_id = None
        consent = cookies.get('CONSENT')
        if consent:
            if 'YES' in consent.value:
                return
            consent_id = self._search_regex(
                r'PENDING\+(\d+)', consent.value, 'consent', default=None)
        if not consent_id:
            consent_id = random.randint(100, 999)
        self._set_cookie('.youtube.com', 'CONSENT', 'YES+cb.20210328-17-p0.en+FX+%s' % consent_id)

    def _real_initialize(self):
        self._initialize_consent()
        if self._downloader is None:
            return
        if not self._login():
            return

    _YT_WEB_CLIENT_VERSION = '2.20210407.08.00'
    _YT_INNERTUBE_API_KEY = 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8'
    _YT_INITIAL_DATA_RE = r'(?:window\s*\[\s*["\']ytInitialData["\']\s*\]|ytInitialData)\s*=\s*({.+?})\s*;'
    _YT_INITIAL_PLAYER_RESPONSE_RE = r'ytInitialPlayerResponse\s*=\s*({.+?})\s*;'
    _YT_INITIAL_BOUNDARY_RE = r'(?:var\s+meta|</script|\n)'

    def _generate_sapisidhash_header(self):
        sapisid_cookie = self._get_cookies('https://www.youtube.com').get('SAPISID')
        if sapisid_cookie is None:
            return
        time_now = round(time.time())
        sapisidhash = hashlib.sha1((str(time_now) + " " + sapisid_cookie.value + " " + "https://www.youtube.com").encode("utf-8")).hexdigest()
        return "SAPISIDHASH %s_%s" % (time_now, sapisidhash)

    def _call_api(self, ep, query, video_id, fatal=True, headers=None,
                  note='Downloading API JSON', errnote='Unable to download API page',
                  context=None, api_key=None):

        data = {'context': context} if context else {'context': self._extract_context()}
        data.update(query)
        real_headers = self._generate_api_headers()
        real_headers.update({'content-type': 'application/json'})
        if headers:
            real_headers.update(headers)
        return self._download_json(
            'https://www.youtube.com/youtubei/v1/%s' % ep,
            video_id=video_id, fatal=fatal, note=note, errnote=errnote,
            data=json.dumps(data).encode('utf8'), headers=real_headers,
            query={'key': api_key or self._extract_api_key()})

    def _extract_api_key(self, ytcfg=None):
        return try_get(ytcfg, lambda x: x['INNERTUBE_API_KEY'], compat_str) or self._YT_INNERTUBE_API_KEY

    def _extract_yt_initial_data(self, video_id, webpage):
        return self._parse_json(
            self._search_regex(
                (r'%s\s*%s' % (self._YT_INITIAL_DATA_RE, self._YT_INITIAL_BOUNDARY_RE),
                 self._YT_INITIAL_DATA_RE), webpage, 'yt initial data'),
            video_id)

    def _extract_identity_token(self, webpage, item_id):
        ytcfg = self._extract_ytcfg(item_id, webpage)
        if ytcfg:
            token = try_get(ytcfg, lambda x: x['ID_TOKEN'], compat_str)
            if token:
                return token
        return self._search_regex(
            r'\bID_TOKEN["\']\s*:\s*["\'](.+?)["\']', webpage,
            'identity token', default=None)

    @staticmethod
    def _extract_account_syncid(data):
        """
        Extract syncId required to download private playlists of secondary channels
        @param data Either response or ytcfg
        """
        sync_ids = (try_get(
            data, (lambda x: x['responseContext']['mainAppWebResponseContext']['datasyncId'],
                   lambda x: x['DATASYNC_ID']), compat_str) or '').split("||")
        if len(sync_ids) >= 2 and sync_ids[1]:
            # datasyncid is of the form "channel_syncid||user_syncid" for secondary channel
            # and just "user_syncid||" for primary channel. We only want the channel_syncid
            return sync_ids[0]
        # ytcfg includes channel_syncid if on secondary channel
        return data.get('DELEGATED_SESSION_ID')

    def _extract_ytcfg(self, video_id, webpage):
        if not webpage:
            return {}
        return self._parse_json(
            self._search_regex(
                r'ytcfg\.set\s*\(\s*({.+?})\s*\)\s*;', webpage, 'ytcfg',
                default='{}'), video_id, fatal=False) or {}

    def __extract_client_version(self, ytcfg):
        return try_get(ytcfg, lambda x: x['INNERTUBE_CLIENT_VERSION'], compat_str) or self._YT_WEB_CLIENT_VERSION

    def _extract_context(self, ytcfg=None):
        context = try_get(ytcfg, lambda x: x['INNERTUBE_CONTEXT'], dict)
        if context:
            return context

        # Recreate the client context (required)
        client_version = self.__extract_client_version(ytcfg)
        client_name = try_get(ytcfg, lambda x: x['INNERTUBE_CLIENT_NAME'], compat_str) or 'WEB'
        context = {
            'client': {
                'clientName': client_name,
                'clientVersion': client_version,
            }
        }
        visitor_data = try_get(ytcfg, lambda x: x['VISITOR_DATA'], compat_str)
        if visitor_data:
            context['client']['visitorData'] = visitor_data
        return context

    def _generate_api_headers(self, ytcfg=None, identity_token=None, account_syncid=None, visitor_data=None):
        headers = {
            'X-YouTube-Client-Name': '1',
            'X-YouTube-Client-Version': self.__extract_client_version(ytcfg),
        }
        if identity_token:
            headers['x-youtube-identity-token'] = identity_token
        if account_syncid:
            headers['X-Goog-PageId'] = account_syncid
            headers['X-Goog-AuthUser'] = 0
        if visitor_data:
            headers['x-goog-visitor-id'] = visitor_data
        auth = self._generate_sapisidhash_header()
        if auth is not None:
            headers['Authorization'] = auth
            headers['X-Origin'] = 'https://www.youtube.com'
        return headers

    def _extract_video(self, renderer):
        video_id = renderer.get('videoId')
        title = try_get(
            renderer,
            (lambda x: x['title']['runs'][0]['text'],
             lambda x: x['title']['simpleText']), compat_str)
        description = try_get(
            renderer, lambda x: x['descriptionSnippet']['runs'][0]['text'],
            compat_str)
        duration = parse_duration(try_get(
            renderer, lambda x: x['lengthText']['simpleText'], compat_str))
        view_count_text = try_get(
            renderer, lambda x: x['viewCountText']['simpleText'], compat_str) or ''
        view_count = str_to_int(self._search_regex(
            r'^([\d,]+)', re.sub(r'\s', '', view_count_text),
            'view count', default=None))
        uploader = try_get(
            renderer,
            (lambda x: x['ownerText']['runs'][0]['text'],
             lambda x: x['shortBylineText']['runs'][0]['text']), compat_str)
        return {
            '_type': 'url',
            'ie_key': YoutubeIE.ie_key(),
            'id': video_id,
            'url': video_id,
            'title': title,
            'description': description,
            'duration': duration,
            'view_count': view_count,
            'uploader': uploader,
        }


class YoutubeIE(YoutubeBaseInfoExtractor):
    IE_DESC = 'YouTube.com'
    _INVIDIOUS_SITES = (
        # invidious-redirect websites
        r'(?:www\.)?redirect\.invidious\.io',
        r'(?:(?:www|dev)\.)?invidio\.us',
        # Invidious instances taken from https://github.com/iv-org/documentation/blob/master/Invidious-Instances.md
        r'(?:www\.)?invidious\.pussthecat\.org',
        r'(?:www\.)?invidious\.zee\.li',
        r'(?:(?:www|au)\.)?ytprivate\.com',
        r'(?:www\.)?invidious\.namazso\.eu',
        r'(?:www\.)?invidious\.ethibox\.fr',
        r'(?:www\.)?w6ijuptxiku4xpnnaetxvnkc5vqcdu7mgns2u77qefoixi63vbvnpnqd\.onion',
        r'(?:www\.)?kbjggqkzv65ivcqj6bumvp337z6264huv5kpkwuv6gu5yjiskvan7fad\.onion',
        r'(?:www\.)?invidious\.3o7z6yfxhbw7n3za4rss6l434kmv55cgw2vuziwuigpwegswvwzqipyd\.onion',
        r'(?:www\.)?grwp24hodrefzvjjuccrkw3mjq4tzhaaq32amf33dzpmuxe7ilepcmad\.onion',
        # youtube-dl invidious instances list
        r'(?:(?:www|no)\.)?invidiou\.sh',
        r'(?:(?:www|fi)\.)?invidious\.snopyta\.org',
        r'(?:www\.)?invidious\.kabi\.tk',
        r'(?:www\.)?invidious\.mastodon\.host',
        r'(?:www\.)?invidious\.zapashcanon\.fr',
        r'(?:www\.)?invidious\.kavin\.rocks',
        r'(?:www\.)?invidious\.tinfoil-hat\.net',
        r'(?:www\.)?invidious\.himiko\.cloud',
        r'(?:www\.)?invidious\.reallyancient\.tech',
        r'(?:www\.)?invidious\.tube',
        r'(?:www\.)?invidiou\.site',
        r'(?:www\.)?invidious\.site',
        r'(?:www\.)?invidious\.xyz',
        r'(?:www\.)?invidious\.nixnet\.xyz',
        r'(?:www\.)?invidious\.048596\.xyz',
        r'(?:www\.)?invidious\.drycat\.fr',
        r'(?:www\.)?inv\.skyn3t\.in',
        r'(?:www\.)?tube\.poal\.co',
        r'(?:www\.)?tube\.connect\.cafe',
        r'(?:www\.)?vid\.wxzm\.sx',
        r'(?:www\.)?vid\.mint\.lgbt',
        r'(?:www\.)?vid\.puffyan\.us',
        r'(?:www\.)?yewtu\.be',
        r'(?:www\.)?yt\.elukerio\.org',
        r'(?:www\.)?yt\.lelux\.fi',
        r'(?:www\.)?invidious\.ggc-project\.de',
        r'(?:www\.)?yt\.maisputain\.ovh',
        r'(?:www\.)?ytprivate\.com',
        r'(?:www\.)?invidious\.13ad\.de',
        r'(?:www\.)?invidious\.toot\.koeln',
        r'(?:www\.)?invidious\.fdn\.fr',
        r'(?:www\.)?watch\.nettohikari\.com',
        r'(?:www\.)?kgg2m7yk5aybusll\.onion',
        r'(?:www\.)?qklhadlycap4cnod\.onion',
        r'(?:www\.)?axqzx4s6s54s32yentfqojs3x5i7faxza6xo3ehd4bzzsg2ii4fv2iid\.onion',
        r'(?:www\.)?c7hqkpkpemu6e7emz5b4vyz7idjgdvgaaa3dyimmeojqbgpea3xqjoid\.onion',
        r'(?:www\.)?fz253lmuao3strwbfbmx46yu7acac2jz27iwtorgmbqlkurlclmancad\.onion',
        r'(?:www\.)?invidious\.l4qlywnpwqsluw65ts7md3khrivpirse744un3x7mlskqauz5pyuzgqd\.onion',
        r'(?:www\.)?owxfohz4kjyv25fvlqilyxast7inivgiktls3th44jhk3ej3i7ya\.b32\.i2p',
        r'(?:www\.)?4l2dgddgsrkf2ous66i6seeyi6etzfgrue332grh2n7madpwopotugyd\.onion',
    )
    _VALID_URL = r"""(?x)^
                     (
                         (?:https?://|//)                                    # http(s):// or protocol-independent URL
                         (?:(?:(?:(?:\w+\.)?[yY][oO][uU][tT][uU][bB][eE](?:-nocookie|kids)?\.com|
                            (?:www\.)?deturl\.com/www\.youtube\.com|
                            (?:www\.)?pwnyoutube\.com|
                            (?:www\.)?hooktube\.com|
                            (?:www\.)?yourepeat\.com|
                            tube\.majestyc\.net|
                            %(invidious)s|
                            youtube\.googleapis\.com)/                        # the various hostnames, with wildcard subdomains
                         (?:.*?\#/)?                                          # handle anchor (#/) redirect urls
                         (?:                                                  # the various things that can precede the ID:
                             (?:(?:v|embed|e)/(?!videoseries))                # v/ or embed/ or e/
                             |(?:                                             # or the v= param in all its forms
                                 (?:(?:watch|movie)(?:_popup)?(?:\.php)?/?)?  # preceding watch(_popup|.php) or nothing (like /?v=xxxx)
                                 (?:\?|\#!?)                                  # the params delimiter ? or # or #!
                                 (?:.*?[&;])??                                # any other preceding param (like /?s=tuff&v=xxxx or ?s=tuff&amp;v=V36LpHqtcDY)
                                 v=
                             )
                         ))
                         |(?:
                            youtu\.be|                                        # just youtu.be/xxxx
                            vid\.plus|                                        # or vid.plus/xxxx
                            zwearz\.com/watch|                                # or zwearz.com/watch/xxxx
                            %(invidious)s
                         )/
                         |(?:www\.)?cleanvideosearch\.com/media/action/yt/watch\?videoId=
                         )
                     )?                                                       # all until now is optional -> you can pass the naked ID
                     (?P<id>[0-9A-Za-z_-]{11})                                # here is it! the YouTube video ID
                     (?(1).+)?                                                # if we found the ID, everything can follow
                     $""" % {
        'invidious': '|'.join(_INVIDIOUS_SITES),
    }
    _PLAYER_INFO_RE = (
        r'/s/player/(?P<id>[a-zA-Z0-9_-]{8,})/player',
        r'/(?P<id>[a-zA-Z0-9_-]{8,})/player(?:_ias\.vflset(?:/[a-zA-Z]{2,3}_[a-zA-Z]{2,3})?|-plasma-ias-(?:phone|tablet)-[a-z]{2}_[A-Z]{2}\.vflset)/base\.js$',
        r'\b(?P<id>vfl[a-zA-Z0-9_-]+)\b.*?\.js$',
    )
    _formats = {
        '5': {'ext': 'flv', 'width': 400, 'height': 240, 'acodec': 'mp3', 'abr': 64, 'vcodec': 'h263'},
        '6': {'ext': 'flv', 'width': 450, 'height': 270, 'acodec': 'mp3', 'abr': 64, 'vcodec': 'h263'},
        '13': {'ext': '3gp', 'acodec': 'aac', 'vcodec': 'mp4v'},
        '17': {'ext': '3gp', 'width': 176, 'height': 144, 'acodec': 'aac', 'abr': 24, 'vcodec': 'mp4v'},
        '18': {'ext': 'mp4', 'width': 640, 'height': 360, 'acodec': 'aac', 'abr': 96, 'vcodec': 'h264'},
        '22': {'ext': 'mp4', 'width': 1280, 'height': 720, 'acodec': 'aac', 'abr': 192, 'vcodec': 'h264'},
        '34': {'ext': 'flv', 'width': 640, 'height': 360, 'acodec': 'aac', 'abr': 128, 'vcodec': 'h264'},
        '35': {'ext': 'flv', 'width': 854, 'height': 480, 'acodec': 'aac', 'abr': 128, 'vcodec': 'h264'},
        # itag 36 videos are either 320x180 (BaW_jenozKc) or 320x240 (__2ABJjxzNo), abr varies as well
        '36': {'ext': '3gp', 'width': 320, 'acodec': 'aac', 'vcodec': 'mp4v'},
        '37': {'ext': 'mp4', 'width': 1920, 'height': 1080, 'acodec': 'aac', 'abr': 192, 'vcodec': 'h264'},
        '38': {'ext': 'mp4', 'width': 4096, 'height': 3072, 'acodec': 'aac', 'abr': 192, 'vcodec': 'h264'},
        '43': {'ext': 'webm', 'width': 640, 'height': 360, 'acodec': 'vorbis', 'abr': 128, 'vcodec': 'vp8'},
        '44': {'ext': 'webm', 'width': 854, 'height': 480, 'acodec': 'vorbis', 'abr': 128, 'vcodec': 'vp8'},
        '45': {'ext': 'webm', 'width': 1280, 'height': 720, 'acodec': 'vorbis', 'abr': 192, 'vcodec': 'vp8'},
        '46': {'ext': 'webm', 'width': 1920, 'height': 1080, 'acodec': 'vorbis', 'abr': 192, 'vcodec': 'vp8'},
        '59': {'ext': 'mp4', 'width': 854, 'height': 480, 'acodec': 'aac', 'abr': 128, 'vcodec': 'h264'},
        '78': {'ext': 'mp4', 'width': 854, 'height': 480, 'acodec': 'aac', 'abr': 128, 'vcodec': 'h264'},


        # 3D videos
        '82': {'ext': 'mp4', 'height': 360, 'format_note': '3D', 'acodec': 'aac', 'abr': 128, 'vcodec': 'h264', 'preference': -20},
        '83': {'ext': 'mp4', 'height': 480, 'format_note': '3D', 'acodec': 'aac', 'abr': 128, 'vcodec': 'h264', 'preference': -20},
        '84': {'ext': 'mp4', 'height': 720, 'format_note': '3D', 'acodec': 'aac', 'abr': 192, 'vcodec': 'h264', 'preference': -20},
        '85': {'ext': 'mp4', 'height': 1080, 'format_note': '3D', 'acodec': 'aac', 'abr': 192, 'vcodec': 'h264', 'preference': -20},
        '100': {'ext': 'webm', 'height': 360, 'format_note': '3D', 'acodec': 'vorbis', 'abr': 128, 'vcodec': 'vp8', 'preference': -20},
        '101': {'ext': 'webm', 'height': 480, 'format_note': '3D', 'acodec': 'vorbis', 'abr': 192, 'vcodec': 'vp8', 'preference': -20},
        '102': {'ext': 'webm', 'height': 720, 'format_note': '3D', 'acodec': 'vorbis', 'abr': 192, 'vcodec': 'vp8', 'preference': -20},

        # Apple HTTP Live Streaming
        '91': {'ext': 'mp4', 'height': 144, 'format_note': 'HLS', 'acodec': 'aac', 'abr': 48, 'vcodec': 'h264', 'preference': -10},
        '92': {'ext': 'mp4', 'height': 240, 'format_note': 'HLS', 'acodec': 'aac', 'abr': 48, 'vcodec': 'h264', 'preference': -10},
        '93': {'ext': 'mp4', 'height': 360, 'format_note': 'HLS', 'acodec': 'aac', 'abr': 128, 'vcodec': 'h264', 'preference': -10},
        '94': {'ext': 'mp4', 'height': 480, 'format_note': 'HLS', 'acodec': 'aac', 'abr': 128, 'vcodec': 'h264', 'preference': -10},
        '95': {'ext': 'mp4', 'height': 720, 'format_note': 'HLS', 'acodec': 'aac', 'abr': 256, 'vcodec': 'h264', 'preference': -10},
        '96': {'ext': 'mp4', 'height': 1080, 'format_note': 'HLS', 'acodec': 'aac', 'abr': 256, 'vcodec': 'h264', 'preference': -10},
        '132': {'ext': 'mp4', 'height': 240, 'format_note': 'HLS', 'acodec': 'aac', 'abr': 48, 'vcodec': 'h264', 'preference': -10},
        '151': {'ext': 'mp4', 'height': 72, 'format_note': 'HLS', 'acodec': 'aac', 'abr': 24, 'vcodec': 'h264', 'preference': -10},

        # DASH mp4 video
        '133': {'ext': 'mp4', 'height': 240, 'format_note': 'DASH video', 'vcodec': 'h264'},
        '134': {'ext': 'mp4', 'height': 360, 'format_note': 'DASH video', 'vcodec': 'h264'},
        '135': {'ext': 'mp4', 'height': 480, 'format_note': 'DASH video', 'vcodec': 'h264'},
        '136': {'ext': 'mp4', 'height': 720, 'format_note': 'DASH video', 'vcodec': 'h264'},
        '137': {'ext': 'mp4', 'height': 1080, 'format_note': 'DASH video', 'vcodec': 'h264'},
        '138': {'ext': 'mp4', 'format_note': 'DASH video', 'vcodec': 'h264'},  # Height can vary (https://github.com/ytdl-org/youtube-dl/issues/4559)
        '160': {'ext': 'mp4', 'height': 144, 'format_note': 'DASH video', 'vcodec': 'h264'},
        '212': {'ext': 'mp4', 'height': 480, 'format_note': 'DASH video', 'vcodec': 'h264'},
        '264': {'ext': 'mp4', 'height': 1440, 'format_note': 'DASH video', 'vcodec': 'h264'},
        '298': {'ext': 'mp4', 'height': 720, 'format_note': 'DASH video', 'vcodec': 'h264', 'fps': 60},
        '299': {'ext': 'mp4', 'height': 1080, 'format_note': 'DASH video', 'vcodec': 'h264', 'fps': 60},
        '266': {'ext': 'mp4', 'height': 2160, 'format_note': 'DASH video', 'vcodec': 'h264'},

        # Dash mp4 audio
        '139': {'ext': 'm4a', 'format_note': 'DASH audio', 'acodec': 'aac', 'abr': 48, 'container': 'm4a_dash'},
        '140': {'ext': 'm4a', 'format_note': 'DASH audio', 'acodec': 'aac', 'abr': 128, 'container': 'm4a_dash'},
        '141': {'ext': 'm4a', 'format_note': 'DASH audio', 'acodec': 'aac', 'abr': 256, 'container': 'm4a_dash'},
        '256': {'ext': 'm4a', 'format_note': 'DASH audio', 'acodec': 'aac', 'container': 'm4a_dash'},
        '258': {'ext': 'm4a', 'format_note': 'DASH audio', 'acodec': 'aac', 'container': 'm4a_dash'},
        '325': {'ext': 'm4a', 'format_note': 'DASH audio', 'acodec': 'dtse', 'container': 'm4a_dash'},
        '328': {'ext': 'm4a', 'format_note': 'DASH audio', 'acodec': 'ec-3', 'container': 'm4a_dash'},

        # Dash webm
        '167': {'ext': 'webm', 'height': 360, 'width': 640, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'vp8'},
        '168': {'ext': 'webm', 'height': 480, 'width': 854, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'vp8'},
        '169': {'ext': 'webm', 'height': 720, 'width': 1280, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'vp8'},
        '170': {'ext': 'webm', 'height': 1080, 'width': 1920, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'vp8'},
        '218': {'ext': 'webm', 'height': 480, 'width': 854, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'vp8'},
        '219': {'ext': 'webm', 'height': 480, 'width': 854, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'vp8'},
        '278': {'ext': 'webm', 'height': 144, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'vp9'},
        '242': {'ext': 'webm', 'height': 240, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '243': {'ext': 'webm', 'height': 360, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '244': {'ext': 'webm', 'height': 480, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '245': {'ext': 'webm', 'height': 480, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '246': {'ext': 'webm', 'height': 480, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '247': {'ext': 'webm', 'height': 720, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '248': {'ext': 'webm', 'height': 1080, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '271': {'ext': 'webm', 'height': 1440, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        # itag 272 videos are either 3840x2160 (e.g. RtoitU2A-3E) or 7680x4320 (sLprVF6d7Ug)
        '272': {'ext': 'webm', 'height': 2160, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '302': {'ext': 'webm', 'height': 720, 'format_note': 'DASH video', 'vcodec': 'vp9', 'fps': 60},
        '303': {'ext': 'webm', 'height': 1080, 'format_note': 'DASH video', 'vcodec': 'vp9', 'fps': 60},
        '308': {'ext': 'webm', 'height': 1440, 'format_note': 'DASH video', 'vcodec': 'vp9', 'fps': 60},
        '313': {'ext': 'webm', 'height': 2160, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '315': {'ext': 'webm', 'height': 2160, 'format_note': 'DASH video', 'vcodec': 'vp9', 'fps': 60},

        # Dash webm audio
        '171': {'ext': 'webm', 'acodec': 'vorbis', 'format_note': 'DASH audio', 'abr': 128},
        '172': {'ext': 'webm', 'acodec': 'vorbis', 'format_note': 'DASH audio', 'abr': 256},

        # Dash webm audio with opus inside
        '249': {'ext': 'webm', 'format_note': 'DASH audio', 'acodec': 'opus', 'abr': 50},
        '250': {'ext': 'webm', 'format_note': 'DASH audio', 'acodec': 'opus', 'abr': 70},
        '251': {'ext': 'webm', 'format_note': 'DASH audio', 'acodec': 'opus', 'abr': 160},

        # RTMP (unnamed)
        '_rtmp': {'protocol': 'rtmp'},

        # av01 video only formats sometimes served with "unknown" codecs
        '394': {'acodec': 'none', 'vcodec': 'av01.0.05M.08'},
        '395': {'acodec': 'none', 'vcodec': 'av01.0.05M.08'},
        '396': {'acodec': 'none', 'vcodec': 'av01.0.05M.08'},
        '397': {'acodec': 'none', 'vcodec': 'av01.0.05M.08'},
    }
    _SUBTITLE_FORMATS = ('json3', 'srv1', 'srv2', 'srv3', 'ttml', 'vtt')

    _GEO_BYPASS = False

    IE_NAME = 'youtube'
    _TESTS = [
        {
            'url': 'https://www.youtube.com/watch?v=BaW_jenozKc&t=1s&end=9',
            'info_dict': {
                'id': 'BaW_jenozKc',
                'ext': 'mp4',
                'title': 'youtube-dl test video "\'/\\ä↭𝕐',
                'uploader': 'Philipp Hagemeister',
                'uploader_id': 'phihag',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/phihag',
                'channel_id': 'UCLqxVugv74EIW3VWh2NOa3Q',
                'channel_url': r're:https?://(?:www\.)?youtube\.com/channel/UCLqxVugv74EIW3VWh2NOa3Q',
                'upload_date': '20121002',
                'description': 'test chars:  "\'/\\ä↭𝕐\ntest URL: https://github.com/rg3/youtube-dl/issues/1892\n\nThis is a test video for youtube-dl.\n\nFor more information, contact phihag@phihag.de .',
                'categories': ['Science & Technology'],
                'tags': ['youtube-dl'],
                'duration': 10,
                'view_count': int,
                'like_count': int,
                'dislike_count': int,
                'start_time': 1,
                'end_time': 9,
            }
        },
        {
            'url': '//www.YouTube.com/watch?v=yZIXLfi8CZQ',
            'note': 'Embed-only video (#1746)',
            'info_dict': {
                'id': 'yZIXLfi8CZQ',
                'ext': 'mp4',
                'upload_date': '20120608',
                'title': 'Principal Sexually Assaults A Teacher - Episode 117 - 8th June 2012',
                'description': 'md5:09b78bd971f1e3e289601dfba15ca4f7',
                'uploader': 'SET India',
                'uploader_id': 'setindia',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/setindia',
                'age_limit': 18,
            },
            'skip': 'Private video',
        },
        {
            'url': 'https://www.youtube.com/watch?v=BaW_jenozKc&v=yZIXLfi8CZQ',
            'note': 'Use the first video ID in the URL',
            'info_dict': {
                'id': 'BaW_jenozKc',
                'ext': 'mp4',
                'title': 'youtube-dl test video "\'/\\ä↭𝕐',
                'uploader': 'Philipp Hagemeister',
                'uploader_id': 'phihag',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/phihag',
                'upload_date': '20121002',
                'description': 'test chars:  "\'/\\ä↭𝕐\ntest URL: https://github.com/rg3/youtube-dl/issues/1892\n\nThis is a test video for youtube-dl.\n\nFor more information, contact phihag@phihag.de .',
                'categories': ['Science & Technology'],
                'tags': ['youtube-dl'],
                'duration': 10,
                'view_count': int,
                'like_count': int,
                'dislike_count': int,
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'https://www.youtube.com/watch?v=a9LDPn-MO4I',
            'note': '256k DASH audio (format 141) via DASH manifest',
            'info_dict': {
                'id': 'a9LDPn-MO4I',
                'ext': 'm4a',
                'upload_date': '20121002',
                'uploader_id': '8KVIDEO',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/8KVIDEO',
                'description': '',
                'uploader': '8KVIDEO',
                'title': 'UHDTV TEST 8K VIDEO.mp4'
            },
            'params': {
                'youtube_include_dash_manifest': True,
                'format': '141',
            },
            'skip': 'format 141 not served anymore',
        },
        # DASH manifest with encrypted signature
        {
            'url': 'https://www.youtube.com/watch?v=IB3lcPjvWLA',
            'info_dict': {
                'id': 'IB3lcPjvWLA',
                'ext': 'm4a',
                'title': 'Afrojack, Spree Wilson - The Spark (Official Music Video) ft. Spree Wilson',
                'description': 'md5:8f5e2b82460520b619ccac1f509d43bf',
                'duration': 244,
                'uploader': 'AfrojackVEVO',
                'uploader_id': 'AfrojackVEVO',
                'upload_date': '20131011',
                'abr': 129.495,
            },
            'params': {
                'youtube_include_dash_manifest': True,
                'format': '141/bestaudio[ext=m4a]',
            },
        },
        # Controversy video
        {
            'url': 'https://www.youtube.com/watch?v=T4XJQO3qol8',
            'info_dict': {
                'id': 'T4XJQO3qol8',
                'ext': 'mp4',
                'duration': 219,
                'upload_date': '20100909',
                'uploader': 'Amazing Atheist',
                'uploader_id': 'TheAmazingAtheist',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/TheAmazingAtheist',
                'title': 'Burning Everyone\'s Koran',
                'description': 'SUBSCRIBE: http://www.youtube.com/saturninefilms \r\n\r\nEven Obama has taken a stand against freedom on this issue: http://www.huffingtonpost.com/2010/09/09/obama-gma-interview-quran_n_710282.html',
            }
        },
        # Normal age-gate video (embed allowed)
        {
            'url': 'https://youtube.com/watch?v=HtVdAasjOgU',
            'info_dict': {
                'id': 'HtVdAasjOgU',
                'ext': 'mp4',
                'title': 'The Witcher 3: Wild Hunt - The Sword Of Destiny Trailer',
                'description': r're:(?s).{100,}About the Game\n.*?The Witcher 3: Wild Hunt.{100,}',
                'duration': 142,
                'uploader': 'The Witcher',
                'uploader_id': 'WitcherGame',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/WitcherGame',
                'upload_date': '20140605',
                'age_limit': 18,
            },
        },
        # video_info is None (https://github.com/ytdl-org/youtube-dl/issues/4421)
        # YouTube Red ad is not captured for creator
        {
            'url': '__2ABJjxzNo',
            'info_dict': {
                'id': '__2ABJjxzNo',
                'ext': 'mp4',
                'duration': 266,
                'upload_date': '20100430',
                'uploader_id': 'deadmau5',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/deadmau5',
                'creator': 'deadmau5',
                'description': 'md5:6cbcd3a92ce1bc676fc4d6ab4ace2336',
                'uploader': 'deadmau5',
                'title': 'Deadmau5 - Some Chords (HD)',
                'alt_title': 'Some Chords',
            },
            'expected_warnings': [
                'DASH manifest missing',
            ]
        },
        # Olympics (https://github.com/ytdl-org/youtube-dl/issues/4431)
        {
            'url': 'lqQg6PlCWgI',
            'info_dict': {
                'id': 'lqQg6PlCWgI',
                'ext': 'mp4',
                'duration': 6085,
                'upload_date': '20150827',
                'uploader_id': 'olympic',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/olympic',
                'description': 'HO09  - Women -  GER-AUS - Hockey - 31 July 2012 - London 2012 Olympic Games',
                'uploader': 'Olympic',
                'title': 'Hockey - Women -  GER-AUS - London 2012 Olympic Games',
            },
            'params': {
                'skip_download': 'requires avconv',
            }
        },
        # Non-square pixels
        {
            'url': 'https://www.youtube.com/watch?v=_b-2C3KPAM0',
            'info_dict': {
                'id': '_b-2C3KPAM0',
                'ext': 'mp4',
                'stretched_ratio': 16 / 9.,
                'duration': 85,
                'upload_date': '20110310',
                'uploader_id': 'AllenMeow',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/AllenMeow',
                'description': 'made by Wacom from Korea | 字幕&加油添醋 by TY\'s Allen | 感謝heylisa00cavey1001同學熱情提供梗及翻譯',
                'uploader': '孫ᄋᄅ',
                'title': '[A-made] 變態妍字幕版 太妍 我就是這樣的人',
            },
        },
        # url_encoded_fmt_stream_map is empty string
        {
            'url': 'qEJwOuvDf7I',
            'info_dict': {
                'id': 'qEJwOuvDf7I',
                'ext': 'webm',
                'title': 'Обсуждение судебной практики по выборам 14 сентября 2014 года в Санкт-Петербурге',
                'description': '',
                'upload_date': '20150404',
                'uploader_id': 'spbelect',
                'uploader': 'Наблюдатели Петербурга',
            },
            'params': {
                'skip_download': 'requires avconv',
            },
            'skip': 'This live event has ended.',
        },
        # Extraction from multiple DASH manifests (https://github.com/ytdl-org/youtube-dl/pull/6097)
        {
            'url': 'https://www.youtube.com/watch?v=FIl7x6_3R5Y',
            'info_dict': {
                'id': 'FIl7x6_3R5Y',
                'ext': 'webm',
                'title': 'md5:7b81415841e02ecd4313668cde88737a',
                'description': 'md5:116377fd2963b81ec4ce64b542173306',
                'duration': 220,
                'upload_date': '20150625',
                'uploader_id': 'dorappi2000',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/dorappi2000',
                'uploader': 'dorappi2000',
                'formats': 'mincount:31',
            },
            'skip': 'not actual anymore',
        },
        # DASH manifest with segment_list
        {
            'url': 'https://www.youtube.com/embed/CsmdDsKjzN8',
            'md5': '8ce563a1d667b599d21064e982ab9e31',
            'info_dict': {
                'id': 'CsmdDsKjzN8',
                'ext': 'mp4',
                'upload_date': '20150501',  # According to '<meta itemprop="datePublished"', but in other places it's 20150510
                'uploader': 'Airtek',
                'description': 'Retransmisión en directo de la XVIII media maratón de Zaragoza.',
                'uploader_id': 'UCzTzUmjXxxacNnL8I3m4LnQ',
                'title': 'Retransmisión XVIII Media maratón Zaragoza 2015',
            },
            'params': {
                'youtube_include_dash_manifest': True,
                'format': '135',  # bestvideo
            },
            'skip': 'This live event has ended.',
        },
        {
            # Multifeed videos (multiple cameras), URL is for Main Camera
            'url': 'https://www.youtube.com/watch?v=jvGDaLqkpTg',
            'info_dict': {
                'id': 'jvGDaLqkpTg',
                'title': 'Tom Clancy Free Weekend Rainbow Whatever',
                'description': 'md5:e03b909557865076822aa169218d6a5d',
            },
            'playlist': [{
                'info_dict': {
                    'id': 'jvGDaLqkpTg',
                    'ext': 'mp4',
                    'title': 'Tom Clancy Free Weekend Rainbow Whatever (Main Camera)',
                    'description': 'md5:e03b909557865076822aa169218d6a5d',
                    'duration': 10643,
                    'upload_date': '20161111',
                    'uploader': 'Team PGP',
                    'uploader_id': 'UChORY56LMMETTuGjXaJXvLg',
                    'uploader_url': r're:https?://(?:www\.)?youtube\.com/channel/UChORY56LMMETTuGjXaJXvLg',
                },
            }, {
                'info_dict': {
                    'id': '3AKt1R1aDnw',
                    'ext': 'mp4',
                    'title': 'Tom Clancy Free Weekend Rainbow Whatever (Camera 2)',
                    'description': 'md5:e03b909557865076822aa169218d6a5d',
                    'duration': 10991,
                    'upload_date': '20161111',
                    'uploader': 'Team PGP',
                    'uploader_id': 'UChORY56LMMETTuGjXaJXvLg',
                    'uploader_url': r're:https?://(?:www\.)?youtube\.com/channel/UChORY56LMMETTuGjXaJXvLg',
                },
            }, {
                'info_dict': {
                    'id': 'RtAMM00gpVc',
                    'ext': 'mp4',
                    'title': 'Tom Clancy Free Weekend Rainbow Whatever (Camera 3)',
                    'description': 'md5:e03b909557865076822aa169218d6a5d',
                    'duration': 10995,
                    'upload_date': '20161111',
                    'uploader': 'Team PGP',
                    'uploader_id': 'UChORY56LMMETTuGjXaJXvLg',
                    'uploader_url': r're:https?://(?:www\.)?youtube\.com/channel/UChORY56LMMETTuGjXaJXvLg',
                },
            }, {
                'info_dict': {
                    'id': '6N2fdlP3C5U',
                    'ext': 'mp4',
                    'title': 'Tom Clancy Free Weekend Rainbow Whatever (Camera 4)',
                    'description': 'md5:e03b909557865076822aa169218d6a5d',
                    'duration': 10990,
                    'upload_date': '20161111',
                    'uploader': 'Team PGP',
                    'uploader_id': 'UChORY56LMMETTuGjXaJXvLg',
                    'uploader_url': r're:https?://(?:www\.)?youtube\.com/channel/UChORY56LMMETTuGjXaJXvLg',
                },
            }],
            'params': {
                'skip_download': True,
            },
        },
        {
            # Multifeed video with comma in title (see https://github.com/ytdl-org/youtube-dl/issues/8536)
            'url': 'https://www.youtube.com/watch?v=gVfLd0zydlo',
            'info_dict': {
                'id': 'gVfLd0zydlo',
                'title': 'DevConf.cz 2016 Day 2 Workshops 1 14:00 - 15:30',
            },
            'playlist_count': 2,
            'skip': 'Not multifeed anymore',
        },
        {
            'url': 'https://vid.plus/FlRa-iH7PGw',
            'only_matching': True,
        },
        {
            'url': 'https://zwearz.com/watch/9lWxNJF-ufM/electra-woman-dyna-girl-official-trailer-grace-helbig.html',
            'only_matching': True,
        },
        {
            # Title with JS-like syntax "};" (see https://github.com/ytdl-org/youtube-dl/issues/7468)
            # Also tests cut-off URL expansion in video description (see
            # https://github.com/ytdl-org/youtube-dl/issues/1892,
            # https://github.com/ytdl-org/youtube-dl/issues/8164)
            'url': 'https://www.youtube.com/watch?v=lsguqyKfVQg',
            'info_dict': {
                'id': 'lsguqyKfVQg',
                'ext': 'mp4',
                'title': '{dark walk}; Loki/AC/Dishonored; collab w/Elflover21',
                'alt_title': 'Dark Walk - Position Music',
                'description': 'md5:8085699c11dc3f597ce0410b0dcbb34a',
                'duration': 133,
                'upload_date': '20151119',
                'uploader_id': 'IronSoulElf',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/IronSoulElf',
                'uploader': 'IronSoulElf',
                'creator': 'Todd Haberman,  Daniel Law Heath and Aaron Kaplan',
                'track': 'Dark Walk - Position Music',
                'artist': 'Todd Haberman,  Daniel Law Heath and Aaron Kaplan',
                'album': 'Position Music - Production Music Vol. 143 - Dark Walk',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # Tags with '};' (see https://github.com/ytdl-org/youtube-dl/issues/7468)
            'url': 'https://www.youtube.com/watch?v=Ms7iBXnlUO8',
            'only_matching': True,
        },
        {
            # Video with yt:stretch=17:0
            'url': 'https://www.youtube.com/watch?v=Q39EVAstoRM',
            'info_dict': {
                'id': 'Q39EVAstoRM',
                'ext': 'mp4',
                'title': 'Clash Of Clans#14 Dicas De Ataque Para CV 4',
                'description': 'md5:ee18a25c350637c8faff806845bddee9',
                'upload_date': '20151107',
                'uploader_id': 'UCCr7TALkRbo3EtFzETQF1LA',
                'uploader': 'CH GAMER DROID',
            },
            'params': {
                'skip_download': True,
            },
            'skip': 'This video does not exist.',
        },
        {
            # Video with incomplete 'yt:stretch=16:'
            'url': 'https://www.youtube.com/watch?v=FRhJzUSJbGI',
            'only_matching': True,
        },
        {
            # Video licensed under Creative Commons
            'url': 'https://www.youtube.com/watch?v=M4gD1WSo5mA',
            'info_dict': {
                'id': 'M4gD1WSo5mA',
                'ext': 'mp4',
                'title': 'md5:e41008789470fc2533a3252216f1c1d1',
                'description': 'md5:a677553cf0840649b731a3024aeff4cc',
                'duration': 721,
                'upload_date': '20150127',
                'uploader_id': 'BerkmanCenter',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/BerkmanCenter',
                'uploader': 'The Berkman Klein Center for Internet & Society',
                'license': 'Creative Commons Attribution license (reuse allowed)',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # Channel-like uploader_url
            'url': 'https://www.youtube.com/watch?v=eQcmzGIKrzg',
            'info_dict': {
                'id': 'eQcmzGIKrzg',
                'ext': 'mp4',
                'title': 'Democratic Socialism and Foreign Policy | Bernie Sanders',
                'description': 'md5:13a2503d7b5904ef4b223aa101628f39',
                'duration': 4060,
                'upload_date': '20151119',
                'uploader': 'Bernie Sanders',
                'uploader_id': 'UCH1dpzjCEiGAt8CXkryhkZg',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/channel/UCH1dpzjCEiGAt8CXkryhkZg',
                'license': 'Creative Commons Attribution license (reuse allowed)',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'https://www.youtube.com/watch?feature=player_embedded&amp;amp;v=V36LpHqtcDY',
            'only_matching': True,
        },
        {
            # YouTube Red paid video (https://github.com/ytdl-org/youtube-dl/issues/10059)
            'url': 'https://www.youtube.com/watch?v=i1Ko8UG-Tdo',
            'only_matching': True,
        },
        {
            # Rental video preview
            'url': 'https://www.youtube.com/watch?v=yYr8q0y5Jfg',
            'info_dict': {
                'id': 'uGpuVWrhIzE',
                'ext': 'mp4',
                'title': 'Piku - Trailer',
                'description': 'md5:c36bd60c3fd6f1954086c083c72092eb',
                'upload_date': '20150811',
                'uploader': 'FlixMatrix',
                'uploader_id': 'FlixMatrixKaravan',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/FlixMatrixKaravan',
                'license': 'Standard YouTube License',
            },
            'params': {
                'skip_download': True,
            },
            'skip': 'This video is not available.',
        },
        {
            # YouTube Red video with episode data
            'url': 'https://www.youtube.com/watch?v=iqKdEhx-dD4',
            'info_dict': {
                'id': 'iqKdEhx-dD4',
                'ext': 'mp4',
                'title': 'Isolation - Mind Field (Ep 1)',
                'description': 'md5:f540112edec5d09fc8cc752d3d4ba3cd',
                'duration': 2085,
                'upload_date': '20170118',
                'uploader': 'Vsauce',
                'uploader_id': 'Vsauce',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/Vsauce',
                'series': 'Mind Field',
                'season_number': 1,
                'episode_number': 1,
            },
            'params': {
                'skip_download': True,
            },
            'expected_warnings': [
                'Skipping DASH manifest',
            ],
        },
        {
            # The following content has been identified by the YouTube community
            # as inappropriate or offensive to some audiences.
            'url': 'https://www.youtube.com/watch?v=6SJNVb0GnPI',
            'info_dict': {
                'id': '6SJNVb0GnPI',
                'ext': 'mp4',
                'title': 'Race Differences in Intelligence',
                'description': 'md5:5d161533167390427a1f8ee89a1fc6f1',
                'duration': 965,
                'upload_date': '20140124',
                'uploader': 'New Century Foundation',
                'uploader_id': 'UCEJYpZGqgUob0zVVEaLhvVg',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/channel/UCEJYpZGqgUob0zVVEaLhvVg',
            },
            'params': {
                'skip_download': True,
            },
            'skip': 'This video has been removed for violating YouTube\'s policy on hate speech.',
        },
        {
            # itag 212
            'url': '1t24XAntNCY',
            'only_matching': True,
        },
        {
            # geo restricted to JP
            'url': 'sJL6WA-aGkQ',
            'only_matching': True,
        },
        {
            'url': 'https://invidio.us/watch?v=BaW_jenozKc',
            'only_matching': True,
        },
        {
            'url': 'https://redirect.invidious.io/watch?v=BaW_jenozKc',
            'only_matching': True,
        },
        {
            # from https://nitter.pussthecat.org/YouTube/status/1360363141947944964#m
            'url': 'https://redirect.invidious.io/Yh0AhrY9GjA',
            'only_matching': True,
        },
        {
            # DRM protected
            'url': 'https://www.youtube.com/watch?v=s7_qI6_mIXc',
            'only_matching': True,
        },
        {
            # Video with unsupported adaptive stream type formats
            'url': 'https://www.youtube.com/watch?v=Z4Vy8R84T1U',
            'info_dict': {
                'id': 'Z4Vy8R84T1U',
                'ext': 'mp4',
                'title': 'saman SMAN 53 Jakarta(Sancety) opening COFFEE4th at SMAN 53 Jakarta',
                'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
                'duration': 433,
                'upload_date': '20130923',
                'uploader': 'Amelia Putri Harwita',
                'uploader_id': 'UCpOxM49HJxmC1qCalXyB3_Q',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/channel/UCpOxM49HJxmC1qCalXyB3_Q',
                'formats': 'maxcount:10',
            },
            'params': {
                'skip_download': True,
                'youtube_include_dash_manifest': False,
            },
            'skip': 'not actual anymore',
        },
        {
            # Youtube Music Auto-generated description
            'url': 'https://music.youtube.com/watch?v=MgNrAu2pzNs',
            'info_dict': {
                'id': 'MgNrAu2pzNs',
                'ext': 'mp4',
                'title': 'Voyeur Girl',
                'description': 'md5:7ae382a65843d6df2685993e90a8628f',
                'upload_date': '20190312',
                'uploader': 'Stephen - Topic',
                'uploader_id': 'UC-pWHpBjdGG69N9mM2auIAA',
                'artist': 'Stephen',
                'track': 'Voyeur Girl',
                'album': 'it\'s too much love to know my dear',
                'release_date': '20190313',
                'release_year': 2019,
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'https://www.youtubekids.com/watch?v=3b8nCWDgZ6Q',
            'only_matching': True,
        },
        {
            # invalid -> valid video id redirection
            'url': 'DJztXj2GPfl',
            'info_dict': {
                'id': 'DJztXj2GPfk',
                'ext': 'mp4',
                'title': 'Panjabi MC - Mundian To Bach Ke (The Dictator Soundtrack)',
                'description': 'md5:bf577a41da97918e94fa9798d9228825',
                'upload_date': '20090125',
                'uploader': 'Prochorowka',
                'uploader_id': 'Prochorowka',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/Prochorowka',
                'artist': 'Panjabi MC',
                'track': 'Beware of the Boys (Mundian to Bach Ke) - Motivo Hi-Lectro Remix',
                'album': 'Beware of the Boys (Mundian To Bach Ke)',
            },
            'params': {
                'skip_download': True,
            },
            'skip': 'Video unavailable',
        },
        {
            # empty description results in an empty string
            'url': 'https://www.youtube.com/watch?v=x41yOUIvK2k',
            'info_dict': {
                'id': 'x41yOUIvK2k',
                'ext': 'mp4',
                'title': 'IMG 3456',
                'description': '',
                'upload_date': '20170613',
                'uploader_id': 'ElevageOrVert',
                'uploader': 'ElevageOrVert',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # with '};' inside yt initial data (see [1])
            # see [2] for an example with '};' inside ytInitialPlayerResponse
            # 1. https://github.com/ytdl-org/youtube-dl/issues/27093
            # 2. https://github.com/ytdl-org/youtube-dl/issues/27216
            'url': 'https://www.youtube.com/watch?v=CHqg6qOn4no',
            'info_dict': {
                'id': 'CHqg6qOn4no',
                'ext': 'mp4',
                'title': 'Part 77   Sort a list of simple types in c#',
                'description': 'md5:b8746fa52e10cdbf47997903f13b20dc',
                'upload_date': '20130831',
                'uploader_id': 'kudvenkat',
                'uploader': 'kudvenkat',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # another example of '};' in ytInitialData
            'url': 'https://www.youtube.com/watch?v=gVfgbahppCY',
            'only_matching': True,
        },
        {
            'url': 'https://www.youtube.com/watch_popup?v=63RmMXCd_bQ',
            'only_matching': True,
        },
        {
            # https://github.com/ytdl-org/youtube-dl/pull/28094
            'url': 'OtqTfy26tG0',
            'info_dict': {
                'id': 'OtqTfy26tG0',
                'ext': 'mp4',
                'title': 'Burn Out',
                'description': 'md5:8d07b84dcbcbfb34bc12a56d968b6131',
                'upload_date': '20141120',
                'uploader': 'The Cinematic Orchestra - Topic',
                'uploader_id': 'UCIzsJBIyo8hhpFm1NK0uLgw',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/channel/UCIzsJBIyo8hhpFm1NK0uLgw',
                'artist': 'The Cinematic Orchestra',
                'track': 'Burn Out',
                'album': 'Every Day',
                'release_data': None,
                'release_year': None,
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # controversial video, only works with bpctr when authenticated with cookies
            'url': 'https://www.youtube.com/watch?v=nGC3D_FkCmg',
            'only_matching': True,
        },
        {
            # restricted location, https://github.com/ytdl-org/youtube-dl/issues/28685
            'url': 'cBvYw8_A0vQ',
            'info_dict': {
                'id': 'cBvYw8_A0vQ',
                'ext': 'mp4',
                'title': '4K Ueno Okachimachi  Street  Scenes  上野御徒町歩き',
                'description': 'md5:ea770e474b7cd6722b4c95b833c03630',
                'upload_date': '20201120',
                'uploader': 'Walk around Japan',
                'uploader_id': 'UC3o_t8PzBmXf5S9b7GLx1Mw',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/channel/UC3o_t8PzBmXf5S9b7GLx1Mw',
            },
            'params': {
                'skip_download': True,
            },
        },
    ]

    @classmethod
    def suitable(cls, url):
        # Hack for lazy extractors until more generic solution is implemented
        # (see #28780)
        from .youtube import parse_qs
        qs = parse_qs(url)
        if qs.get('list', [None])[0]:
            return False
        return super(YoutubeIE, cls).suitable(url)

    def __init__(self, *args, **kwargs):
        super(YoutubeIE, self).__init__(*args, **kwargs)
        self._code_cache = {}
        self._player_cache = {}

    def _signature_cache_id(self, example_sig):
        """ Return a string representation of a signature """
        return '.'.join(compat_str(len(part)) for part in example_sig.split('.'))

    @classmethod
    def _extract_player_info(cls, player_url):
        for player_re in cls._PLAYER_INFO_RE:
            id_m = re.search(player_re, player_url)
            if id_m:
                break
        else:
            raise ExtractorError('Cannot identify player %r' % player_url)
        return id_m.group('id')

    def _extract_signature_function(self, video_id, player_url, example_sig):
        player_id = self._extract_player_info(player_url)

        # Read from filesystem cache
        func_id = 'js_%s_%s' % (
            player_id, self._signature_cache_id(example_sig))
        assert os.path.basename(func_id) == func_id

        cache_spec = self._downloader.cache.load('youtube-sigfuncs', func_id)
        if cache_spec is not None:
            return lambda s: ''.join(s[i] for i in cache_spec)

        if player_id not in self._code_cache:
            self._code_cache[player_id] = self._download_webpage(
                player_url, video_id,
                note='Downloading player ' + player_id,
                errnote='Download of %s failed' % player_url)
        code = self._code_cache[player_id]
        res = self._parse_sig_js(code)

        test_string = ''.join(map(compat_chr, range(len(example_sig))))
        cache_res = res(test_string)
        cache_spec = [ord(c) for c in cache_res]

        self._downloader.cache.store('youtube-sigfuncs', func_id, cache_spec)
        return res

    def _print_sig_code(self, func, example_sig):
        def gen_sig_code(idxs):
            def _genslice(start, end, step):
                starts = '' if start == 0 else str(start)
                ends = (':%d' % (end + step)) if end + step >= 0 else ':'
                steps = '' if step == 1 else (':%d' % step)
                return 's[%s%s%s]' % (starts, ends, steps)

            step = None
            # Quelch pyflakes warnings - start will be set when step is set
            start = '(Never used)'
            for i, prev in zip(idxs[1:], idxs[:-1]):
                if step is not None:
                    if i - prev == step:
                        continue
                    yield _genslice(start, prev, step)
                    step = None
                    continue
                if i - prev in [-1, 1]:
                    step = i - prev
                    start = prev
                    continue
                else:
                    yield 's[%d]' % prev
            if step is None:
                yield 's[%d]' % i
            else:
                yield _genslice(start, i, step)

        test_string = ''.join(map(compat_chr, range(len(example_sig))))
        cache_res = func(test_string)
        cache_spec = [ord(c) for c in cache_res]
        expr_code = ' + '.join(gen_sig_code(cache_spec))
        signature_id_tuple = '(%s)' % (
            ', '.join(compat_str(len(p)) for p in example_sig.split('.')))
        code = ('if tuple(len(p) for p in s.split(\'.\')) == %s:\n'
                '    return %s\n') % (signature_id_tuple, expr_code)
        self.to_screen('Extracted signature function:\n' + code)

    def _parse_sig_js(self, jscode):
        funcname = self._search_regex(
            (r'\b[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*encodeURIComponent\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\b[a-zA-Z0-9]+\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*encodeURIComponent\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\bm=(?P<sig>[a-zA-Z0-9$]{2})\(decodeURIComponent\(h\.s\)\)',
             r'\bc&&\(c=(?P<sig>[a-zA-Z0-9$]{2})\(decodeURIComponent\(c\)\)',
             r'(?:\b|[^a-zA-Z0-9$])(?P<sig>[a-zA-Z0-9$]{2})\s*=\s*function\(\s*a\s*\)\s*{\s*a\s*=\s*a\.split\(\s*""\s*\);[a-zA-Z0-9$]{2}\.[a-zA-Z0-9$]{2}\(a,\d+\)',
             r'(?:\b|[^a-zA-Z0-9$])(?P<sig>[a-zA-Z0-9$]{2})\s*=\s*function\(\s*a\s*\)\s*{\s*a\s*=\s*a\.split\(\s*""\s*\)',
             r'(?P<sig>[a-zA-Z0-9$]+)\s*=\s*function\(\s*a\s*\)\s*{\s*a\s*=\s*a\.split\(\s*""\s*\)',
             # Obsolete patterns
             r'(["\'])signature\1\s*,\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\.sig\|\|(?P<sig>[a-zA-Z0-9$]+)\(',
             r'yt\.akamaized\.net/\)\s*\|\|\s*.*?\s*[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*(?:encodeURIComponent\s*\()?\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\b[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\b[a-zA-Z0-9]+\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\bc\s*&&\s*a\.set\([^,]+\s*,\s*\([^)]*\)\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\bc\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*\([^)]*\)\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\bc\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*\([^)]*\)\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\('),
            jscode, 'Initial JS player signature function name', group='sig')

        jsi = JSInterpreter(jscode)
        initial_function = jsi.extract_function(funcname)
        return lambda s: initial_function([s])

    def _decrypt_signature(self, s, video_id, player_url):
        """Turn the encrypted s field into a working signature"""

        if player_url is None:
            raise ExtractorError('Cannot decrypt signature without player_url')

        if player_url.startswith('//'):
            player_url = 'https:' + player_url
        elif not re.match(r'https?://', player_url):
            player_url = compat_urlparse.urljoin(
                'https://www.youtube.com', player_url)
        try:
            player_id = (player_url, self._signature_cache_id(s))
            if player_id not in self._player_cache:
                func = self._extract_signature_function(
                    video_id, player_url, s
                )
                self._player_cache[player_id] = func
            func = self._player_cache[player_id]
            if self._downloader.params.get('youtube_print_sig_code'):
                self._print_sig_code(func, s)
            return func(s)
        except Exception as e:
            tb = traceback.format_exc()
            raise ExtractorError(
                'Signature extraction failed: ' + tb, cause=e)

    def _mark_watched(self, video_id, player_response):
        playback_url = url_or_none(try_get(
            player_response,
            lambda x: x['playbackTracking']['videostatsPlaybackUrl']['baseUrl']))
        if not playback_url:
            return
        parsed_playback_url = compat_urlparse.urlparse(playback_url)
        qs = compat_urlparse.parse_qs(parsed_playback_url.query)

        # cpn generation algorithm is reverse engineered from base.js.
        # In fact it works even with dummy cpn.
        CPN_ALPHABET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
        cpn = ''.join((CPN_ALPHABET[random.randint(0, 256) & 63] for _ in range(0, 16)))

        qs.update({
            'ver': ['2'],
            'cpn': [cpn],
        })
        playback_url = compat_urlparse.urlunparse(
            parsed_playback_url._replace(query=compat_urllib_parse_urlencode(qs, True)))

        self._download_webpage(
            playback_url, video_id, 'Marking watched',
            'Unable to mark watched', fatal=False)

    @staticmethod
    def _extract_urls(webpage):
        # Embedded YouTube player
        entries = [
            unescapeHTML(mobj.group('url'))
            for mobj in re.finditer(r'''(?x)
            (?:
                <iframe[^>]+?src=|
                data-video-url=|
                <embed[^>]+?src=|
                embedSWF\(?:\s*|
                <object[^>]+data=|
                new\s+SWFObject\(
            )
            (["\'])
                (?P<url>(?:https?:)?//(?:www\.)?youtube(?:-nocookie)?\.com/
                (?:embed|v|p)/[0-9A-Za-z_-]{11}.*?)
            \1''', webpage)]

        # lazyYT YouTube embed
        entries.extend(list(map(
            unescapeHTML,
            re.findall(r'class="lazyYT" data-youtube-id="([^"]+)"', webpage))))

        # Wordpress "YouTube Video Importer" plugin
        matches = re.findall(r'''(?x)<div[^>]+
            class=(?P<q1>[\'"])[^\'"]*\byvii_single_video_player\b[^\'"]*(?P=q1)[^>]+
            data-video_id=(?P<q2>[\'"])([^\'"]+)(?P=q2)''', webpage)
        entries.extend(m[-1] for m in matches)

        return entries

    @staticmethod
    def _extract_url(webpage):
        urls = YoutubeIE._extract_urls(webpage)
        return urls[0] if urls else None

    @classmethod
    def extract_id(cls, url):
        mobj = re.match(cls._VALID_URL, url, re.VERBOSE)
        if mobj is None:
            raise ExtractorError('Invalid URL: %s' % url)
        video_id = mobj.group(2)
        return video_id

    def _extract_chapters_from_json(self, data, video_id, duration):
        chapters_list = try_get(
            data,
            lambda x: x['playerOverlays']
                       ['playerOverlayRenderer']
                       ['decoratedPlayerBarRenderer']
                       ['decoratedPlayerBarRenderer']
                       ['playerBar']
                       ['chapteredPlayerBarRenderer']
                       ['chapters'],
            list)
        if not chapters_list:
            return

        def chapter_time(chapter):
            return float_or_none(
                try_get(
                    chapter,
                    lambda x: x['chapterRenderer']['timeRangeStartMillis'],
                    int),
                scale=1000)
        chapters = []
        for next_num, chapter in enumerate(chapters_list, start=1):
            start_time = chapter_time(chapter)
            if start_time is None:
                continue
            end_time = (chapter_time(chapters_list[next_num])
                        if next_num < len(chapters_list) else duration)
            if end_time is None:
                continue
            title = try_get(
                chapter, lambda x: x['chapterRenderer']['title']['simpleText'],
                compat_str)
            chapters.append({
                'start_time': start_time,
                'end_time': end_time,
                'title': title,
            })
        return chapters

    def _extract_yt_initial_variable(self, webpage, regex, video_id, name):
        return self._parse_json(self._search_regex(
            (r'%s\s*%s' % (regex, self._YT_INITIAL_BOUNDARY_RE),
             regex), webpage, name, default='{}'), video_id, fatal=False)

    @staticmethod
    def parse_time_text(time_text):
        """
        Parse the comment time text
        time_text is in the format 'X units ago (edited)'
        """
        time_text_split = time_text.split(' ')
        if len(time_text_split) >= 3:
            return datetime_from_str('now-%s%s' % (time_text_split[0], time_text_split[1]), precision='auto')

    @staticmethod
    def _join_text_entries(runs):
        text = None
        for run in runs:
            if not isinstance(run, dict):
                continue
            sub_text = try_get(run, lambda x: x['text'], compat_str)
            if sub_text:
                if not text:
                    text = sub_text
                    continue
                text += sub_text
        return text

    def _extract_comment(self, comment_renderer, parent=None):
        comment_id = comment_renderer.get('commentId')
        if not comment_id:
            return
        comment_text_runs = try_get(comment_renderer, lambda x: x['contentText']['runs']) or []
        text = self._join_text_entries(comment_text_runs) or ''
        comment_time_text = try_get(comment_renderer, lambda x: x['publishedTimeText']['runs']) or []
        time_text = self._join_text_entries(comment_time_text)
        timestamp = calendar.timegm(self.parse_time_text(time_text).timetuple())
        author = try_get(comment_renderer, lambda x: x['authorText']['simpleText'], compat_str)
        author_id = try_get(comment_renderer,
                            lambda x: x['authorEndpoint']['browseEndpoint']['browseId'], compat_str)
        votes = str_to_int(try_get(comment_renderer, (lambda x: x['voteCount']['simpleText'],
                                                      lambda x: x['likeCount']), compat_str)) or 0
        author_thumbnail = try_get(comment_renderer,
                                   lambda x: x['authorThumbnail']['thumbnails'][-1]['url'], compat_str)

        author_is_uploader = try_get(comment_renderer, lambda x: x['authorIsChannelOwner'], bool)
        is_liked = try_get(comment_renderer, lambda x: x['isLiked'], bool)
        return {
            'id': comment_id,
            'text': text,
            'timestamp': timestamp,
            'time_text': time_text,
            'like_count': votes,
            'is_favorited': is_liked,
            'author': author,
            'author_id': author_id,
            'author_thumbnail': author_thumbnail,
            'author_is_uploader': author_is_uploader,
            'parent': parent or 'root'
        }

    def _comment_entries(self, root_continuation_data, identity_token, account_syncid,
                         ytcfg, session_token_list, parent=None, comment_counts=None):

        def extract_thread(parent_renderer):
            contents = try_get(parent_renderer, lambda x: x['contents'], list) or []
            if not parent:
                comment_counts[2] = 0
            for content in contents:
                comment_thread_renderer = try_get(content, lambda x: x['commentThreadRenderer'])
                comment_renderer = try_get(
                    comment_thread_renderer, (lambda x: x['comment']['commentRenderer'], dict)) or try_get(
                    content, (lambda x: x['commentRenderer'], dict))

                if not comment_renderer:
                    continue
                comment = self._extract_comment(comment_renderer, parent)
                if not comment:
                    continue
                comment_counts[0] += 1
                yield comment
                # Attempt to get the replies
                comment_replies_renderer = try_get(
                    comment_thread_renderer, lambda x: x['replies']['commentRepliesRenderer'], dict)

                if comment_replies_renderer:
                    comment_counts[2] += 1
                    comment_entries_iter = self._comment_entries(
                        comment_replies_renderer, identity_token, account_syncid, ytcfg,
                        parent=comment.get('id'), session_token_list=session_token_list,
                        comment_counts=comment_counts)

                    for reply_comment in comment_entries_iter:
                        yield reply_comment

        if not comment_counts:
            # comment so far, est. total comments, current comment thread #
            comment_counts = [0, 0, 0]

        # TODO: Generalize the download code with TabIE
        context = self._extract_context(ytcfg)
        visitor_data = try_get(context, lambda x: x['client']['visitorData'], compat_str)
        continuation = YoutubeTabIE._extract_continuation(root_continuation_data)  # TODO
        first_continuation = False
        if parent is None:
            first_continuation = True

        for page_num in itertools.count(0):
            if not continuation:
                break
            headers = self._generate_api_headers(ytcfg, identity_token, account_syncid, visitor_data)
            retries = self._downloader.params.get('extractor_retries', 3)
            count = -1
            last_error = None

            while count < retries:
                count += 1
                if last_error:
                    self.report_warning('%s. Retrying ...' % last_error)
                try:
                    query = {
                        'ctoken': continuation['ctoken'],
                        'pbj': 1,
                        'type': 'next',
                    }
                    if parent:
                        query['action_get_comment_replies'] = 1
                    else:
                        query['action_get_comments'] = 1

                    comment_prog_str = '(%d/%d)' % (comment_counts[0], comment_counts[1])
                    if page_num == 0:
                        if first_continuation:
                            note_prefix = 'Downloading initial comment continuation page'
                        else:
                            note_prefix = '    Downloading comment reply thread %d %s' % (comment_counts[2], comment_prog_str)
                    else:
                        note_prefix = '%sDownloading comment%s page %d %s' % (
                            '       ' if parent else '',
                            ' replies' if parent else '',
                            page_num,
                            comment_prog_str)

                    browse = self._download_json(
                        'https://www.youtube.com/comment_service_ajax', None,
                        '%s %s' % (note_prefix, '(retry #%d)' % count if count else ''),
                        headers=headers, query=query,
                        data=urlencode_postdata({
                            'session_token': session_token_list[0]
                        }))
                except ExtractorError as e:
                    if isinstance(e.cause, compat_HTTPError) and e.cause.code in (500, 503, 404, 413):
                        if e.cause.code == 413:
                            self.report_warning('Assumed end of comments (received HTTP Error 413)')
                            return
                        # Downloading page may result in intermittent 5xx HTTP error
                        # Sometimes a 404 is also recieved. See: https://github.com/ytdl-org/youtube-dl/issues/28289
                        last_error = 'HTTP Error %s' % e.cause.code
                        if e.cause.code == 404:
                            last_error = last_error + ' (this API is probably deprecated)'
                        if count < retries:
                            continue
                    raise
                else:
                    session_token = try_get(browse, lambda x: x['xsrf_token'], compat_str)
                    if session_token:
                        session_token_list[0] = session_token

                    response = try_get(browse,
                                       (lambda x: x['response'],
                                        lambda x: x[1]['response'])) or {}

                    if response.get('continuationContents'):
                        break

                    # YouTube sometimes gives reload: now json if something went wrong (e.g. bad auth)
                    if browse.get('reload'):
                        raise ExtractorError('Invalid or missing params in continuation request', expected=False)

                    # TODO: not tested, merged from old extractor
                    err_msg = browse.get('externalErrorMessage')
                    if err_msg:
                        raise ExtractorError('YouTube said: %s' % err_msg, expected=False)

                    # Youtube sometimes sends incomplete data
                    # See: https://github.com/ytdl-org/youtube-dl/issues/28194
                    last_error = 'Incomplete data received'
                    if count >= retries:
                        raise ExtractorError(last_error)

            if not response:
                break
            visitor_data = try_get(
                response,
                lambda x: x['responseContext']['webResponseContextExtensionData']['ytConfigData']['visitorData'],
                compat_str) or visitor_data

            known_continuation_renderers = {
                'itemSectionContinuation': extract_thread,
                'commentRepliesContinuation': extract_thread
            }

            # extract next root continuation from the results
            continuation_contents = try_get(
                response, lambda x: x['continuationContents'], dict) or {}

            for key, value in continuation_contents.items():
                if key not in known_continuation_renderers:
                    continue
                continuation_renderer = value

                if first_continuation:
                    first_continuation = False
                    expected_comment_count = try_get(
                        continuation_renderer,
                        (lambda x: x['header']['commentsHeaderRenderer']['countText']['runs'][0]['text'],
                         lambda x: x['header']['commentsHeaderRenderer']['commentsCount']['runs'][0]['text']),
                        compat_str)

                    if expected_comment_count:
                        comment_counts[1] = str_to_int(expected_comment_count)
                        self.to_screen('Downloading ~%d comments' % str_to_int(expected_comment_count))
                        yield comment_counts[1]

                    # TODO: cli arg.
                    # 1/True for newest, 0/False for popular (default)
                    comment_sort_index = int(True)
                    sort_continuation_renderer = try_get(
                        continuation_renderer,
                        lambda x: x['header']['commentsHeaderRenderer']['sortMenu']['sortFilterSubMenuRenderer']['subMenuItems']
                        [comment_sort_index]['continuation']['reloadContinuationData'], dict)
                    # If this fails, the initial continuation page
                    # starts off with popular anyways.
                    if sort_continuation_renderer:
                        continuation = YoutubeTabIE._build_continuation_query(
                            continuation=sort_continuation_renderer.get('continuation'),
                            ctp=sort_continuation_renderer.get('clickTrackingParams'))
                        self.to_screen('Sorting comments by %s' % ('popular' if comment_sort_index == 0 else 'newest'))
                        break

                for entry in known_continuation_renderers[key](continuation_renderer):
                    yield entry

                continuation = YoutubeTabIE._extract_continuation(continuation_renderer)  # TODO
                break

    def _extract_comments(self, ytcfg, video_id, contents, webpage, xsrf_token):
        """Entry for comment extraction"""
        comments = []
        known_entry_comment_renderers = (
            'itemSectionRenderer',
        )
        estimated_total = 0
        for entry in contents:
            for key, renderer in entry.items():
                if key not in known_entry_comment_renderers:
                    continue

                comment_iter = self._comment_entries(
                    renderer,
                    identity_token=self._extract_identity_token(webpage, item_id=video_id),
                    account_syncid=self._extract_account_syncid(ytcfg),
                    ytcfg=ytcfg,
                    session_token_list=[xsrf_token])

                for comment in comment_iter:
                    if isinstance(comment, int):
                        estimated_total = comment
                        continue
                    comments.append(comment)
                break
        self.to_screen('Downloaded %d/%d comments' % (len(comments), estimated_total))
        return {
            'comments': comments,
            'comment_count': len(comments),
        }

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        video_id = self._match_id(url)
        base_url = self.http_scheme() + '//www.youtube.com/'
        webpage_url = base_url + 'watch?v=' + video_id
        webpage = self._download_webpage(
            webpage_url + '&bpctr=9999999999&has_verified=1', video_id, fatal=False)

        player_response = None
        if webpage:
            player_response = self._extract_yt_initial_variable(
                webpage, self._YT_INITIAL_PLAYER_RESPONSE_RE,
                video_id, 'initial player response')

        ytcfg = self._extract_ytcfg(video_id, webpage)
        if not player_response:
            player_response = self._call_api(
                'player', {'videoId': video_id}, video_id, api_key=self._extract_api_key(ytcfg))

        playability_status = player_response.get('playabilityStatus') or {}
        if playability_status.get('reason') == 'Sign in to confirm your age':
            pr = self._parse_json(try_get(compat_parse_qs(
                self._download_webpage(
                    base_url + 'get_video_info', video_id,
                    'Refetching age-gated info webpage',
                    'unable to download video info webpage', query={
                        'video_id': video_id,
                        'eurl': 'https://youtube.googleapis.com/v/' + video_id,
                    }, fatal=False)),
                lambda x: x['player_response'][0],
                compat_str) or '{}', video_id)
            if pr:
                player_response = pr

        trailer_video_id = try_get(
            playability_status,
            lambda x: x['errorScreen']['playerLegacyDesktopYpcTrailerRenderer']['trailerVideoId'],
            compat_str)
        if trailer_video_id:
            return self.url_result(
                trailer_video_id, self.ie_key(), trailer_video_id)

        def get_text(x):
            if not x:
                return
            text = x.get('simpleText')
            if text and isinstance(text, compat_str):
                return text
            runs = x.get('runs')
            if not isinstance(runs, list):
                return
            return ''.join([r['text'] for r in runs if isinstance(r.get('text'), compat_str)])

        search_meta = (
            lambda x: self._html_search_meta(x, webpage, default=None)) \
            if webpage else lambda x: None

        video_details = player_response.get('videoDetails') or {}
        microformat = try_get(
            player_response,
            lambda x: x['microformat']['playerMicroformatRenderer'],
            dict) or {}
        video_title = video_details.get('title') \
            or get_text(microformat.get('title')) \
            or search_meta(['og:title', 'twitter:title', 'title'])
        video_description = video_details.get('shortDescription')

        if not smuggled_data.get('force_singlefeed', False):
            if not self._downloader.params.get('noplaylist'):
                multifeed_metadata_list = try_get(
                    player_response,
                    lambda x: x['multicamera']['playerLegacyMulticameraRenderer']['metadataList'],
                    compat_str)
                if multifeed_metadata_list:
                    entries = []
                    feed_ids = []
                    for feed in multifeed_metadata_list.split(','):
                        # Unquote should take place before split on comma (,) since textual
                        # fields may contain comma as well (see
                        # https://github.com/ytdl-org/youtube-dl/issues/8536)
                        feed_data = compat_parse_qs(
                            compat_urllib_parse_unquote_plus(feed))

                        def feed_entry(name):
                            return try_get(
                                feed_data, lambda x: x[name][0], compat_str)

                        feed_id = feed_entry('id')
                        if not feed_id:
                            continue
                        feed_title = feed_entry('title')
                        title = video_title
                        if feed_title:
                            title += ' (%s)' % feed_title
                        entries.append({
                            '_type': 'url_transparent',
                            'ie_key': 'Youtube',
                            'url': smuggle_url(
                                base_url + 'watch?v=' + feed_data['id'][0],
                                {'force_singlefeed': True}),
                            'title': title,
                        })
                        feed_ids.append(feed_id)
                    self.to_screen(
                        'Downloading multifeed video (%s) - add --no-playlist to just download video %s'
                        % (', '.join(feed_ids), video_id))
                    return self.playlist_result(
                        entries, video_id, video_title, video_description)
            else:
                self.to_screen('Downloading just video %s because of --no-playlist' % video_id)

        formats = []
        itags = []
        itag_qualities = {}
        player_url = None
        q = qualities(['tiny', 'small', 'medium', 'large', 'hd720', 'hd1080', 'hd1440', 'hd2160', 'hd2880', 'highres'])
        streaming_data = player_response.get('streamingData') or {}
        streaming_formats = streaming_data.get('formats') or []
        streaming_formats.extend(streaming_data.get('adaptiveFormats') or [])
        for fmt in streaming_formats:
            if fmt.get('targetDurationSec') or fmt.get('drmFamilies'):
                continue

            itag = str_or_none(fmt.get('itag'))
            quality = fmt.get('quality')
            if itag and quality:
                itag_qualities[itag] = quality
            # FORMAT_STREAM_TYPE_OTF(otf=1) requires downloading the init fragment
            # (adding `&sq=0` to the URL) and parsing emsg box to determine the
            # number of fragment that would subsequently requested with (`&sq=N`)
            if fmt.get('type') == 'FORMAT_STREAM_TYPE_OTF':
                continue

            fmt_url = fmt.get('url')
            if not fmt_url:
                sc = compat_parse_qs(fmt.get('signatureCipher'))
                fmt_url = url_or_none(try_get(sc, lambda x: x['url'][0]))
                encrypted_sig = try_get(sc, lambda x: x['s'][0])
                if not (sc and fmt_url and encrypted_sig):
                    continue
                if not player_url:
                    if not webpage:
                        continue
                    player_url = self._search_regex(
                        r'"(?:PLAYER_JS_URL|jsUrl)"\s*:\s*"([^"]+)"',
                        webpage, 'player URL', fatal=False)
                if not player_url:
                    continue
                signature = self._decrypt_signature(sc['s'][0], video_id, player_url)
                sp = try_get(sc, lambda x: x['sp'][0]) or 'signature'
                fmt_url += '&' + sp + '=' + signature

            if itag:
                itags.append(itag)
            tbr = float_or_none(
                fmt.get('averageBitrate') or fmt.get('bitrate'), 1000)
            dct = {
                'asr': int_or_none(fmt.get('audioSampleRate')),
                'filesize': int_or_none(fmt.get('contentLength')),
                'format_id': itag,
                'format_note': fmt.get('qualityLabel') or quality,
                'fps': int_or_none(fmt.get('fps')),
                'height': int_or_none(fmt.get('height')),
                'quality': q(quality),
                'tbr': tbr,
                'url': fmt_url,
                'width': fmt.get('width'),
            }
            mimetype = fmt.get('mimeType')
            if mimetype:
                mobj = re.match(
                    r'((?:[^/]+)/(?:[^;]+))(?:;\s*codecs="([^"]+)")?', mimetype)
                if mobj:
                    dct['ext'] = mimetype2ext(mobj.group(1))
                    dct.update(parse_codecs(mobj.group(2)))
            no_audio = dct.get('acodec') == 'none'
            no_video = dct.get('vcodec') == 'none'
            if no_audio:
                dct['vbr'] = tbr
            if no_video:
                dct['abr'] = tbr
            if no_audio or no_video:
                dct['downloader_options'] = {
                    # Youtube throttles chunks >~10M
                    'http_chunk_size': 10485760,
                }
                if dct.get('ext'):
                    dct['container'] = dct['ext'] + '_dash'
            formats.append(dct)

        hls_manifest_url = streaming_data.get('hlsManifestUrl')
        if hls_manifest_url:
            for f in self._extract_m3u8_formats(
                    hls_manifest_url, video_id, 'mp4', fatal=False):
                itag = self._search_regex(
                    r'/itag/(\d+)', f['url'], 'itag', default=None)
                if itag:
                    f['format_id'] = itag
                formats.append(f)

        if self._downloader.params.get('youtube_include_dash_manifest', True):
            dash_manifest_url = streaming_data.get('dashManifestUrl')
            if dash_manifest_url:
                for f in self._extract_mpd_formats(
                        dash_manifest_url, video_id, fatal=False):
                    itag = f['format_id']
                    if itag in itags:
                        continue
                    if itag in itag_qualities:
                        # Not actually usefull since the sorting is already done with "quality,res,fps,codec"
                        # but kept to maintain feature parity (and code similarity) with youtube-dl
                        # Remove if this causes any issues with sorting in future
                        f['quality'] = q(itag_qualities[itag])
                    filesize = int_or_none(self._search_regex(
                        r'/clen/(\d+)', f.get('fragment_base_url')
                        or f['url'], 'file size', default=None))
                    if filesize:
                        f['filesize'] = filesize
                    formats.append(f)

        if not formats:
            if not self._downloader.params.get('allow_unplayable_formats') and streaming_data.get('licenseInfos'):
                self.raise_no_formats(
                    'This video is DRM protected.', expected=True)
            pemr = try_get(
                playability_status,
                lambda x: x['errorScreen']['playerErrorMessageRenderer'],
                dict) or {}
            reason = get_text(pemr.get('reason')) or playability_status.get('reason')
            subreason = pemr.get('subreason')
            if subreason:
                subreason = clean_html(get_text(subreason))
                if subreason == 'The uploader has not made this video available in your country.':
                    countries = microformat.get('availableCountries')
                    if not countries:
                        regions_allowed = search_meta('regionsAllowed')
                        countries = regions_allowed.split(',') if regions_allowed else None
                    self.raise_geo_restricted(subreason, countries, metadata_available=True)
                reason += '\n' + subreason
            if reason:
                self.raise_no_formats(reason, expected=True)

        self._sort_formats(formats)

        keywords = video_details.get('keywords') or []
        if not keywords and webpage:
            keywords = [
                unescapeHTML(m.group('content'))
                for m in re.finditer(self._meta_regex('og:video:tag'), webpage)]
        for keyword in keywords:
            if keyword.startswith('yt:stretch='):
                mobj = re.search(r'(\d+)\s*:\s*(\d+)', keyword)
                if mobj:
                    # NB: float is intentional for forcing float division
                    w, h = (float(v) for v in mobj.groups())
                    if w > 0 and h > 0:
                        ratio = w / h
                        for f in formats:
                            if f.get('vcodec') != 'none':
                                f['stretched_ratio'] = ratio
                        break

        thumbnails = []
        for container in (video_details, microformat):
            for thumbnail in (try_get(
                    container,
                    lambda x: x['thumbnail']['thumbnails'], list) or []):
                thumbnail_url = thumbnail.get('url')
                if not thumbnail_url:
                    continue
                # Sometimes youtube gives a wrong thumbnail URL. See:
                # https://github.com/yt-dlp/yt-dlp/issues/233
                # https://github.com/ytdl-org/youtube-dl/issues/28023
                if 'maxresdefault' in thumbnail_url:
                    thumbnail_url = thumbnail_url.split('?')[0]
                thumbnails.append({
                    'height': int_or_none(thumbnail.get('height')),
                    'url': thumbnail_url,
                    'width': int_or_none(thumbnail.get('width')),
                })
            if thumbnails:
                break
        else:
            thumbnail = search_meta(['og:image', 'twitter:image'])
            if thumbnail:
                thumbnails = [{'url': thumbnail}]

        category = microformat.get('category') or search_meta('genre')
        channel_id = video_details.get('channelId') \
            or microformat.get('externalChannelId') \
            or search_meta('channelId')
        duration = int_or_none(
            video_details.get('lengthSeconds')
            or microformat.get('lengthSeconds')) \
            or parse_duration(search_meta('duration'))
        is_live = video_details.get('isLive')
        owner_profile_url = microformat.get('ownerProfileUrl')

        info = {
            'id': video_id,
            'title': self._live_title(video_title) if is_live else video_title,
            'formats': formats,
            'thumbnails': thumbnails,
            'description': video_description,
            'upload_date': unified_strdate(
                microformat.get('uploadDate')
                or search_meta('uploadDate')),
            'uploader': video_details['author'],
            'uploader_id': self._search_regex(r'/(?:channel|user)/([^/?&#]+)', owner_profile_url, 'uploader id') if owner_profile_url else None,
            'uploader_url': owner_profile_url,
            'channel_id': channel_id,
            'channel_url': 'https://www.youtube.com/channel/' + channel_id if channel_id else None,
            'duration': duration,
            'view_count': int_or_none(
                video_details.get('viewCount')
                or microformat.get('viewCount')
                or search_meta('interactionCount')),
            'average_rating': float_or_none(video_details.get('averageRating')),
            'age_limit': 18 if (
                microformat.get('isFamilySafe') is False
                or search_meta('isFamilyFriendly') == 'false'
                or search_meta('og:restrictions:age') == '18+') else 0,
            'webpage_url': webpage_url,
            'categories': [category] if category else None,
            'tags': keywords,
            'is_live': is_live,
            'playable_in_embed': playability_status.get('playableInEmbed'),
            'was_live': video_details.get('isLiveContent'),
        }

        pctr = try_get(
            player_response,
            lambda x: x['captions']['playerCaptionsTracklistRenderer'], dict)
        subtitles = {}
        if pctr:
            def process_language(container, base_url, lang_code, query):
                lang_subs = []
                for fmt in self._SUBTITLE_FORMATS:
                    query.update({
                        'fmt': fmt,
                    })
                    lang_subs.append({
                        'ext': fmt,
                        'url': update_url_query(base_url, query),
                    })
                container[lang_code] = lang_subs

            for caption_track in (pctr.get('captionTracks') or []):
                base_url = caption_track.get('baseUrl')
                if not base_url:
                    continue
                if caption_track.get('kind') != 'asr':
                    lang_code = caption_track.get('languageCode')
                    if not lang_code:
                        continue
                    process_language(
                        subtitles, base_url, lang_code, {})
                    continue
                automatic_captions = {}
                for translation_language in (pctr.get('translationLanguages') or []):
                    translation_language_code = translation_language.get('languageCode')
                    if not translation_language_code:
                        continue
                    process_language(
                        automatic_captions, base_url, translation_language_code,
                        {'tlang': translation_language_code})
                info['automatic_captions'] = automatic_captions
        info['subtitles'] = subtitles

        parsed_url = compat_urllib_parse_urlparse(url)
        for component in [parsed_url.fragment, parsed_url.query]:
            query = compat_parse_qs(component)
            for k, v in query.items():
                for d_k, s_ks in [('start', ('start', 't')), ('end', ('end',))]:
                    d_k += '_time'
                    if d_k not in info and k in s_ks:
                        info[d_k] = parse_duration(query[k][0])

        # Youtube Music Auto-generated description
        if video_description:
            mobj = re.search(r'(?s)(?P<track>[^·\n]+)·(?P<artist>[^\n]+)\n+(?P<album>[^\n]+)(?:.+?℗\s*(?P<release_year>\d{4})(?!\d))?(?:.+?Released on\s*:\s*(?P<release_date>\d{4}-\d{2}-\d{2}))?(.+?\nArtist\s*:\s*(?P<clean_artist>[^\n]+))?.+\nAuto-generated by YouTube\.\s*$', video_description)
            if mobj:
                release_year = mobj.group('release_year')
                release_date = mobj.group('release_date')
                if release_date:
                    release_date = release_date.replace('-', '')
                    if not release_year:
                        release_year = release_date[:4]
                info.update({
                    'album': mobj.group('album'.strip()),
                    'artist': mobj.group('clean_artist') or ', '.join(a.strip() for a in mobj.group('artist').split('·')),
                    'track': mobj.group('track').strip(),
                    'release_date': release_date,
                    'release_year': int_or_none(release_year),
                })

        initial_data = None
        if webpage:
            initial_data = self._extract_yt_initial_variable(
                webpage, self._YT_INITIAL_DATA_RE, video_id,
                'yt initial data')
        if not initial_data:
            initial_data = self._call_api(
                'next', {'videoId': video_id}, video_id, fatal=False, api_key=self._extract_api_key(ytcfg))

        if not is_live:
            try:
                # This will error if there is no livechat
                initial_data['contents']['twoColumnWatchNextResults']['conversationBar']['liveChatRenderer']['continuations'][0]['reloadContinuationData']['continuation']
                info['subtitles']['live_chat'] = [{
                    'url': 'https://www.youtube.com/watch?v=%s' % video_id,  # url is needed to set cookies
                    'video_id': video_id,
                    'ext': 'json',
                    'protocol': 'youtube_live_chat_replay',
                }]
            except (KeyError, IndexError, TypeError):
                pass

        if initial_data:
            chapters = self._extract_chapters_from_json(
                initial_data, video_id, duration)
            if not chapters:
                for engagment_pannel in (initial_data.get('engagementPanels') or []):
                    contents = try_get(
                        engagment_pannel, lambda x: x['engagementPanelSectionListRenderer']['content']['macroMarkersListRenderer']['contents'],
                        list)
                    if not contents:
                        continue

                    def chapter_time(mmlir):
                        return parse_duration(
                            get_text(mmlir.get('timeDescription')))

                    chapters = []
                    for next_num, content in enumerate(contents, start=1):
                        mmlir = content.get('macroMarkersListItemRenderer') or {}
                        start_time = chapter_time(mmlir)
                        end_time = chapter_time(try_get(
                            contents, lambda x: x[next_num]['macroMarkersListItemRenderer'])) \
                            if next_num < len(contents) else duration
                        if start_time is None or end_time is None:
                            continue
                        chapters.append({
                            'start_time': start_time,
                            'end_time': end_time,
                            'title': get_text(mmlir.get('title')),
                        })
                    if chapters:
                        break
            if chapters:
                info['chapters'] = chapters

            contents = try_get(
                initial_data,
                lambda x: x['contents']['twoColumnWatchNextResults']['results']['results']['contents'],
                list) or []
            for content in contents:
                vpir = content.get('videoPrimaryInfoRenderer')
                if vpir:
                    stl = vpir.get('superTitleLink')
                    if stl:
                        stl = get_text(stl)
                        if try_get(
                                vpir,
                                lambda x: x['superTitleIcon']['iconType']) == 'LOCATION_PIN':
                            info['location'] = stl
                        else:
                            mobj = re.search(r'(.+?)\s*S(\d+)\s*•\s*E(\d+)', stl)
                            if mobj:
                                info.update({
                                    'series': mobj.group(1),
                                    'season_number': int(mobj.group(2)),
                                    'episode_number': int(mobj.group(3)),
                                })
                    for tlb in (try_get(
                            vpir,
                            lambda x: x['videoActions']['menuRenderer']['topLevelButtons'],
                            list) or []):
                        tbr = tlb.get('toggleButtonRenderer') or {}
                        for getter, regex in [(
                                lambda x: x['defaultText']['accessibility']['accessibilityData'],
                                r'(?P<count>[\d,]+)\s*(?P<type>(?:dis)?like)'), ([
                                    lambda x: x['accessibility'],
                                    lambda x: x['accessibilityData']['accessibilityData'],
                                ], r'(?P<type>(?:dis)?like) this video along with (?P<count>[\d,]+) other people')]:
                            label = (try_get(tbr, getter, dict) or {}).get('label')
                            if label:
                                mobj = re.match(regex, label)
                                if mobj:
                                    info[mobj.group('type') + '_count'] = str_to_int(mobj.group('count'))
                                    break
                    sbr_tooltip = try_get(
                        vpir, lambda x: x['sentimentBar']['sentimentBarRenderer']['tooltip'])
                    if sbr_tooltip:
                        like_count, dislike_count = sbr_tooltip.split(' / ')
                        info.update({
                            'like_count': str_to_int(like_count),
                            'dislike_count': str_to_int(dislike_count),
                        })
                vsir = content.get('videoSecondaryInfoRenderer')
                if vsir:
                    info['channel'] = get_text(try_get(
                        vsir,
                        lambda x: x['owner']['videoOwnerRenderer']['title'],
                        dict))
                    rows = try_get(
                        vsir,
                        lambda x: x['metadataRowContainer']['metadataRowContainerRenderer']['rows'],
                        list) or []
                    multiple_songs = False
                    for row in rows:
                        if try_get(row, lambda x: x['metadataRowRenderer']['hasDividerLine']) is True:
                            multiple_songs = True
                            break
                    for row in rows:
                        mrr = row.get('metadataRowRenderer') or {}
                        mrr_title = mrr.get('title')
                        if not mrr_title:
                            continue
                        mrr_title = get_text(mrr['title'])
                        mrr_contents_text = get_text(mrr['contents'][0])
                        if mrr_title == 'License':
                            info['license'] = mrr_contents_text
                        elif not multiple_songs:
                            if mrr_title == 'Album':
                                info['album'] = mrr_contents_text
                            elif mrr_title == 'Artist':
                                info['artist'] = mrr_contents_text
                            elif mrr_title == 'Song':
                                info['track'] = mrr_contents_text

        fallbacks = {
            'channel': 'uploader',
            'channel_id': 'uploader_id',
            'channel_url': 'uploader_url',
        }
        for to, frm in fallbacks.items():
            if not info.get(to):
                info[to] = info.get(frm)

        for s_k, d_k in [('artist', 'creator'), ('track', 'alt_title')]:
            v = info.get(s_k)
            if v:
                info[d_k] = v

        is_private = bool_or_none(video_details.get('isPrivate'))
        is_unlisted = bool_or_none(microformat.get('isUnlisted'))
        is_membersonly = None
        is_premium = None
        if initial_data and is_private is not None:
            is_membersonly = False
            is_premium = False
            contents = try_get(initial_data, lambda x: x['contents']['twoColumnWatchNextResults']['results']['results']['contents'], list)
            for content in contents or []:
                badges = try_get(content, lambda x: x['videoPrimaryInfoRenderer']['badges'], list)
                for badge in badges or []:
                    label = try_get(badge, lambda x: x['metadataBadgeRenderer']['label']) or ''
                    if label.lower() == 'members only':
                        is_membersonly = True
                        break
                    elif label.lower() == 'premium':
                        is_premium = True
                        break
                if is_membersonly or is_premium:
                    break

        # TODO: Add this for playlists
        info['availability'] = self._availability(
            is_private=is_private,
            needs_premium=is_premium,
            needs_subscription=is_membersonly,
            needs_auth=info['age_limit'] >= 18,
            is_unlisted=None if is_private is None else is_unlisted)

        # get xsrf for annotations or comments
        get_annotations = self._downloader.params.get('writeannotations', False)
        get_comments = self._downloader.params.get('getcomments', False)
        if get_annotations or get_comments:
            xsrf_token = None
            ytcfg = self._extract_ytcfg(video_id, webpage)
            if ytcfg:
                xsrf_token = try_get(ytcfg, lambda x: x['XSRF_TOKEN'], compat_str)
            if not xsrf_token:
                xsrf_token = self._search_regex(
                    r'([\'"])XSRF_TOKEN\1\s*:\s*([\'"])(?P<xsrf_token>(?:(?!\2).)+)\2',
                    webpage, 'xsrf token', group='xsrf_token', fatal=False)

        # annotations
        if get_annotations:
            invideo_url = try_get(
                player_response, lambda x: x['annotations'][0]['playerAnnotationsUrlsRenderer']['invideoUrl'], compat_str)
            if xsrf_token and invideo_url:
                xsrf_field_name = None
                if ytcfg:
                    xsrf_field_name = try_get(ytcfg, lambda x: x['XSRF_FIELD_NAME'], compat_str)
                if not xsrf_field_name:
                    xsrf_field_name = self._search_regex(
                        r'([\'"])XSRF_FIELD_NAME\1\s*:\s*([\'"])(?P<xsrf_field_name>\w+)\2',
                        webpage, 'xsrf field name',
                        group='xsrf_field_name', default='session_token')
                info['annotations'] = self._download_webpage(
                    self._proto_relative_url(invideo_url),
                    video_id, note='Downloading annotations',
                    errnote='Unable to download video annotations', fatal=False,
                    data=urlencode_postdata({xsrf_field_name: xsrf_token}))

        if get_comments:
            info['__post_extractor'] = lambda: self._extract_comments(ytcfg, video_id, contents, webpage, xsrf_token)

        self.mark_watched(video_id, player_response)

        return info


class YoutubeTabIE(YoutubeBaseInfoExtractor):
    IE_DESC = 'YouTube.com tab'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:\w+\.)?
                        (?:
                            youtube(?:kids)?\.com|
                            invidio\.us
                        )/
                        (?:
                            (?:channel|c|user)/|
                            (?P<not_channel>
                                feed/|hashtag/|
                                (?:playlist|watch)\?.*?\blist=
                            )|
                            (?!(?:%s)\b)  # Direct URLs
                        )
                        (?P<id>[^/?\#&]+)
                    ''' % YoutubeBaseInfoExtractor._RESERVED_NAMES
    IE_NAME = 'youtube:tab'

    _TESTS = [{
        # playlists, multipage
        'url': 'https://www.youtube.com/c/ИгорьКлейнер/playlists?view=1&flow=grid',
        'playlist_mincount': 94,
        'info_dict': {
            'id': 'UCqj7Cz7revf5maW9g5pgNcg',
            'title': 'Игорь Клейнер - Playlists',
            'description': 'md5:be97ee0f14ee314f1f002cf187166ee2',
            'uploader': 'Игорь Клейнер',
            'uploader_id': 'UCqj7Cz7revf5maW9g5pgNcg',
        },
    }, {
        # playlists, multipage, different order
        'url': 'https://www.youtube.com/user/igorkle1/playlists?view=1&sort=dd',
        'playlist_mincount': 94,
        'info_dict': {
            'id': 'UCqj7Cz7revf5maW9g5pgNcg',
            'title': 'Игорь Клейнер - Playlists',
            'description': 'md5:be97ee0f14ee314f1f002cf187166ee2',
            'uploader_id': 'UCqj7Cz7revf5maW9g5pgNcg',
            'uploader': 'Игорь Клейнер',
        },
    }, {
        # playlists, series
        'url': 'https://www.youtube.com/c/3blue1brown/playlists?view=50&sort=dd&shelf_id=3',
        'playlist_mincount': 5,
        'info_dict': {
            'id': 'UCYO_jab_esuFRV4b17AJtAw',
            'title': '3Blue1Brown - Playlists',
            'description': 'md5:e1384e8a133307dd10edee76e875d62f',
        },
    }, {
        # playlists, singlepage
        'url': 'https://www.youtube.com/user/ThirstForScience/playlists',
        'playlist_mincount': 4,
        'info_dict': {
            'id': 'UCAEtajcuhQ6an9WEzY9LEMQ',
            'title': 'ThirstForScience - Playlists',
            'description': 'md5:609399d937ea957b0f53cbffb747a14c',
            'uploader': 'ThirstForScience',
            'uploader_id': 'UCAEtajcuhQ6an9WEzY9LEMQ',
        }
    }, {
        'url': 'https://www.youtube.com/c/ChristophLaimer/playlists',
        'only_matching': True,
    }, {
        # basic, single video playlist
        'url': 'https://www.youtube.com/playlist?list=PL4lCao7KL_QFVb7Iudeipvc2BCavECqzc',
        'info_dict': {
            'uploader_id': 'UCmlqkdCBesrv2Lak1mF_MxA',
            'uploader': 'Sergey M.',
            'id': 'PL4lCao7KL_QFVb7Iudeipvc2BCavECqzc',
            'title': 'youtube-dl public playlist',
        },
        'playlist_count': 1,
    }, {
        # empty playlist
        'url': 'https://www.youtube.com/playlist?list=PL4lCao7KL_QFodcLWhDpGCYnngnHtQ-Xf',
        'info_dict': {
            'uploader_id': 'UCmlqkdCBesrv2Lak1mF_MxA',
            'uploader': 'Sergey M.',
            'id': 'PL4lCao7KL_QFodcLWhDpGCYnngnHtQ-Xf',
            'title': 'youtube-dl empty playlist',
        },
        'playlist_count': 0,
    }, {
        # Home tab
        'url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w/featured',
        'info_dict': {
            'id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'title': 'lex will - Home',
            'description': 'md5:2163c5d0ff54ed5f598d6a7e6211e488',
            'uploader': 'lex will',
            'uploader_id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
        },
        'playlist_mincount': 2,
    }, {
        # Videos tab
        'url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w/videos',
        'info_dict': {
            'id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'title': 'lex will - Videos',
            'description': 'md5:2163c5d0ff54ed5f598d6a7e6211e488',
            'uploader': 'lex will',
            'uploader_id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
        },
        'playlist_mincount': 975,
    }, {
        # Videos tab, sorted by popular
        'url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w/videos?view=0&sort=p&flow=grid',
        'info_dict': {
            'id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'title': 'lex will - Videos',
            'description': 'md5:2163c5d0ff54ed5f598d6a7e6211e488',
            'uploader': 'lex will',
            'uploader_id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
        },
        'playlist_mincount': 199,
    }, {
        # Playlists tab
        'url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w/playlists',
        'info_dict': {
            'id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'title': 'lex will - Playlists',
            'description': 'md5:2163c5d0ff54ed5f598d6a7e6211e488',
            'uploader': 'lex will',
            'uploader_id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
        },
        'playlist_mincount': 17,
    }, {
        # Community tab
        'url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w/community',
        'info_dict': {
            'id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'title': 'lex will - Community',
            'description': 'md5:2163c5d0ff54ed5f598d6a7e6211e488',
            'uploader': 'lex will',
            'uploader_id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
        },
        'playlist_mincount': 18,
    }, {
        # Channels tab
        'url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w/channels',
        'info_dict': {
            'id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'title': 'lex will - Channels',
            'description': 'md5:2163c5d0ff54ed5f598d6a7e6211e488',
            'uploader': 'lex will',
            'uploader_id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
        },
        'playlist_mincount': 12,
    }, {
        'url': 'https://invidio.us/channel/UCmlqkdCBesrv2Lak1mF_MxA',
        'only_matching': True,
    }, {
        'url': 'https://www.youtubekids.com/channel/UCmlqkdCBesrv2Lak1mF_MxA',
        'only_matching': True,
    }, {
        'url': 'https://music.youtube.com/channel/UCmlqkdCBesrv2Lak1mF_MxA',
        'only_matching': True,
    }, {
        'note': 'Playlist with deleted videos (#651). As a bonus, the video #51 is also twice in this list.',
        'url': 'https://www.youtube.com/playlist?list=PLwP_SiAcdui0KVebT0mU9Apz359a4ubsC',
        'info_dict': {
            'title': '29C3: Not my department',
            'id': 'PLwP_SiAcdui0KVebT0mU9Apz359a4ubsC',
            'uploader': 'Christiaan008',
            'uploader_id': 'UCEPzS1rYsrkqzSLNp76nrcg',
            'description': 'md5:a14dc1a8ef8307a9807fe136a0660268',
        },
        'playlist_count': 96,
    }, {
        'note': 'Large playlist',
        'url': 'https://www.youtube.com/playlist?list=UUBABnxM4Ar9ten8Mdjj1j0Q',
        'info_dict': {
            'title': 'Uploads from Cauchemar',
            'id': 'UUBABnxM4Ar9ten8Mdjj1j0Q',
            'uploader': 'Cauchemar',
            'uploader_id': 'UCBABnxM4Ar9ten8Mdjj1j0Q',
        },
        'playlist_mincount': 1123,
    }, {
        # even larger playlist, 8832 videos
        'url': 'http://www.youtube.com/user/NASAgovVideo/videos',
        'only_matching': True,
    }, {
        'note': 'Buggy playlist: the webpage has a "Load more" button but it doesn\'t have more videos',
        'url': 'https://www.youtube.com/playlist?list=UUXw-G3eDE9trcvY2sBMM_aA',
        'info_dict': {
            'title': 'Uploads from Interstellar Movie',
            'id': 'UUXw-G3eDE9trcvY2sBMM_aA',
            'uploader': 'Interstellar Movie',
            'uploader_id': 'UCXw-G3eDE9trcvY2sBMM_aA',
        },
        'playlist_mincount': 21,
    }, {
        'note': 'Playlist with "show unavailable videos" button',
        'url': 'https://www.youtube.com/playlist?list=UUTYLiWFZy8xtPwxFwX9rV7Q',
        'info_dict': {
            'title': 'Uploads from Phim Siêu Nhân Nhật Bản',
            'id': 'UUTYLiWFZy8xtPwxFwX9rV7Q',
            'uploader': 'Phim Siêu Nhân Nhật Bản',
            'uploader_id': 'UCTYLiWFZy8xtPwxFwX9rV7Q',
        },
        'playlist_mincount': 1400,
        'expected_warnings': [
            'YouTube said: INFO - Unavailable videos are hidden',
        ]
    }, {
        'note': 'Playlist with unavailable videos in a later page',
        'url': 'https://www.youtube.com/playlist?list=UU8l9frL61Yl5KFOl87nIm2w',
        'info_dict': {
            'title': 'Uploads from BlankTV',
            'id': 'UU8l9frL61Yl5KFOl87nIm2w',
            'uploader': 'BlankTV',
            'uploader_id': 'UC8l9frL61Yl5KFOl87nIm2w',
        },
        'playlist_mincount': 20000,
    }, {
        # https://github.com/ytdl-org/youtube-dl/issues/21844
        'url': 'https://www.youtube.com/playlist?list=PLzH6n4zXuckpfMu_4Ff8E7Z1behQks5ba',
        'info_dict': {
            'title': 'Data Analysis with Dr Mike Pound',
            'id': 'PLzH6n4zXuckpfMu_4Ff8E7Z1behQks5ba',
            'uploader_id': 'UC9-y-6csu5WGm29I7JiwpnA',
            'uploader': 'Computerphile',
            'description': 'md5:7f567c574d13d3f8c0954d9ffee4e487',
        },
        'playlist_mincount': 11,
    }, {
        'url': 'https://invidio.us/playlist?list=PL4lCao7KL_QFVb7Iudeipvc2BCavECqzc',
        'only_matching': True,
    }, {
        # Playlist URL that does not actually serve a playlist
        'url': 'https://www.youtube.com/watch?v=FqZTN594JQw&list=PLMYEtVRpaqY00V9W81Cwmzp6N6vZqfUKD4',
        'info_dict': {
            'id': 'FqZTN594JQw',
            'ext': 'webm',
            'title': "Smiley's People 01 detective, Adventure Series, Action",
            'uploader': 'STREEM',
            'uploader_id': 'UCyPhqAZgwYWZfxElWVbVJng',
            'uploader_url': r're:https?://(?:www\.)?youtube\.com/channel/UCyPhqAZgwYWZfxElWVbVJng',
            'upload_date': '20150526',
            'license': 'Standard YouTube License',
            'description': 'md5:507cdcb5a49ac0da37a920ece610be80',
            'categories': ['People & Blogs'],
            'tags': list,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'This video is not available.',
        'add_ie': [YoutubeIE.ie_key()],
    }, {
        'url': 'https://www.youtubekids.com/watch?v=Agk7R8I8o5U&list=PUZ6jURNr1WQZCNHF0ao-c0g',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/watch?v=MuAGGZNfUkU&list=RDMM',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/channel/UCoMdktPbSTixAyNGwb-UYkQ/live',
        'info_dict': {
            'id': '9Auq9mYxFEE',
            'ext': 'mp4',
            'title': compat_str,
            'uploader': 'Sky News',
            'uploader_id': 'skynews',
            'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/skynews',
            'upload_date': '20191102',
            'description': 'md5:85ddd75d888674631aaf9599a9a0b0ae',
            'categories': ['News & Politics'],
            'tags': list,
            'like_count': int,
            'dislike_count': int,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.youtube.com/user/TheYoungTurks/live',
        'info_dict': {
            'id': 'a48o2S1cPoo',
            'ext': 'mp4',
            'title': 'The Young Turks - Live Main Show',
            'uploader': 'The Young Turks',
            'uploader_id': 'TheYoungTurks',
            'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/TheYoungTurks',
            'upload_date': '20150715',
            'license': 'Standard YouTube License',
            'description': 'md5:438179573adcdff3c97ebb1ee632b891',
            'categories': ['News & Politics'],
            'tags': ['Cenk Uygur (TV Program Creator)', 'The Young Turks (Award-Winning Work)', 'Talk Show (TV Genre)'],
            'like_count': int,
            'dislike_count': int,
        },
        'params': {
            'skip_download': True,
        },
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/channel/UC1yBKRuGpC1tSM73A0ZjYjQ/live',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/c/CommanderVideoHq/live',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/feed/trending',
        'only_matching': True,
    }, {
        # needs auth
        'url': 'https://www.youtube.com/feed/library',
        'only_matching': True,
    }, {
        # needs auth
        'url': 'https://www.youtube.com/feed/history',
        'only_matching': True,
    }, {
        # needs auth
        'url': 'https://www.youtube.com/feed/subscriptions',
        'only_matching': True,
    }, {
        # needs auth
        'url': 'https://www.youtube.com/feed/watch_later',
        'only_matching': True,
    }, {
        # no longer available?
        'url': 'https://www.youtube.com/feed/recommended',
        'only_matching': True,
    }, {
        # inline playlist with not always working continuations
        'url': 'https://www.youtube.com/watch?v=UC6u0Tct-Fo&list=PL36D642111D65BE7C',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/course?list=ECUl4u3cNGP61MdtwGTqZA0MreSaDybji8',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/course',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/zsecurity',
        'only_matching': True,
    }, {
        'url': 'http://www.youtube.com/NASAgovVideo/videos',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/TheYoungTurks/live',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/hashtag/cctv9',
        'info_dict': {
            'id': 'cctv9',
            'title': '#cctv9',
        },
        'playlist_mincount': 350,
    }, {
        'url': 'https://www.youtube.com/watch?list=PLW4dVinRY435CBE_JD3t-0SRXKfnZHS1P&feature=youtu.be&v=M9cJMXmQ_ZU',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if YoutubeIE.suitable(url) else super(
            YoutubeTabIE, cls).suitable(url)

    def _extract_channel_id(self, webpage):
        channel_id = self._html_search_meta(
            'channelId', webpage, 'channel id', default=None)
        if channel_id:
            return channel_id
        channel_url = self._html_search_meta(
            ('og:url', 'al:ios:url', 'al:android:url', 'al:web:url',
             'twitter:url', 'twitter:app:url:iphone', 'twitter:app:url:ipad',
             'twitter:app:url:googleplay'), webpage, 'channel url')
        return self._search_regex(
            r'https?://(?:www\.)?youtube\.com/channel/([^/?#&])+',
            channel_url, 'channel id')

    @staticmethod
    def _extract_basic_item_renderer(item):
        # Modified from _extract_grid_item_renderer
        known_basic_renderers = (
            'playlistRenderer', 'videoRenderer', 'channelRenderer', 'showRenderer'
        )
        for key, renderer in item.items():
            if not isinstance(renderer, dict):
                continue
            elif key in known_basic_renderers:
                return renderer
            elif key.startswith('grid') and key.endswith('Renderer'):
                return renderer

    def _grid_entries(self, grid_renderer):
        for item in grid_renderer['items']:
            if not isinstance(item, dict):
                continue
            renderer = self._extract_basic_item_renderer(item)
            if not isinstance(renderer, dict):
                continue
            title = try_get(
                renderer, (lambda x: x['title']['runs'][0]['text'],
                           lambda x: x['title']['simpleText']), compat_str)
            # playlist
            playlist_id = renderer.get('playlistId')
            if playlist_id:
                yield self.url_result(
                    'https://www.youtube.com/playlist?list=%s' % playlist_id,
                    ie=YoutubeTabIE.ie_key(), video_id=playlist_id,
                    video_title=title)
                continue
            # video
            video_id = renderer.get('videoId')
            if video_id:
                yield self._extract_video(renderer)
                continue
            # channel
            channel_id = renderer.get('channelId')
            if channel_id:
                title = try_get(
                    renderer, lambda x: x['title']['simpleText'], compat_str)
                yield self.url_result(
                    'https://www.youtube.com/channel/%s' % channel_id,
                    ie=YoutubeTabIE.ie_key(), video_title=title)
                continue
            # generic endpoint URL support
            ep_url = urljoin('https://www.youtube.com/', try_get(
                renderer, lambda x: x['navigationEndpoint']['commandMetadata']['webCommandMetadata']['url'],
                compat_str))
            if ep_url:
                for ie in (YoutubeTabIE, YoutubePlaylistIE, YoutubeIE):
                    if ie.suitable(ep_url):
                        yield self.url_result(
                            ep_url, ie=ie.ie_key(), video_id=ie._match_id(ep_url), video_title=title)
                        break

    def _shelf_entries_from_content(self, shelf_renderer):
        content = shelf_renderer.get('content')
        if not isinstance(content, dict):
            return
        renderer = content.get('gridRenderer') or content.get('expandedShelfContentsRenderer')
        if renderer:
            # TODO: add support for nested playlists so each shelf is processed
            # as separate playlist
            # TODO: this includes only first N items
            for entry in self._grid_entries(renderer):
                yield entry
        renderer = content.get('horizontalListRenderer')
        if renderer:
            # TODO
            pass

    def _shelf_entries(self, shelf_renderer, skip_channels=False):
        ep = try_get(
            shelf_renderer, lambda x: x['endpoint']['commandMetadata']['webCommandMetadata']['url'],
            compat_str)
        shelf_url = urljoin('https://www.youtube.com', ep)
        if shelf_url:
            # Skipping links to another channels, note that checking for
            # endpoint.commandMetadata.webCommandMetadata.webPageTypwebPageType == WEB_PAGE_TYPE_CHANNEL
            # will not work
            if skip_channels and '/channels?' in shelf_url:
                return
            title = try_get(
                shelf_renderer, lambda x: x['title']['runs'][0]['text'], compat_str)
            yield self.url_result(shelf_url, video_title=title)
        # Shelf may not contain shelf URL, fallback to extraction from content
        for entry in self._shelf_entries_from_content(shelf_renderer):
            yield entry

    def _playlist_entries(self, video_list_renderer):
        for content in video_list_renderer['contents']:
            if not isinstance(content, dict):
                continue
            renderer = content.get('playlistVideoRenderer') or content.get('playlistPanelVideoRenderer')
            if not isinstance(renderer, dict):
                continue
            video_id = renderer.get('videoId')
            if not video_id:
                continue
            yield self._extract_video(renderer)

    def _rich_entries(self, rich_grid_renderer):
        renderer = try_get(
            rich_grid_renderer, lambda x: x['content']['videoRenderer'], dict) or {}
        video_id = renderer.get('videoId')
        if not video_id:
            return
        yield self._extract_video(renderer)

    def _video_entry(self, video_renderer):
        video_id = video_renderer.get('videoId')
        if video_id:
            return self._extract_video(video_renderer)

    def _post_thread_entries(self, post_thread_renderer):
        post_renderer = try_get(
            post_thread_renderer, lambda x: x['post']['backstagePostRenderer'], dict)
        if not post_renderer:
            return
        # video attachment
        video_renderer = try_get(
            post_renderer, lambda x: x['backstageAttachment']['videoRenderer'], dict)
        video_id = None
        if video_renderer:
            entry = self._video_entry(video_renderer)
            if entry:
                yield entry
        # inline video links
        runs = try_get(post_renderer, lambda x: x['contentText']['runs'], list) or []
        for run in runs:
            if not isinstance(run, dict):
                continue
            ep_url = try_get(
                run, lambda x: x['navigationEndpoint']['urlEndpoint']['url'], compat_str)
            if not ep_url:
                continue
            if not YoutubeIE.suitable(ep_url):
                continue
            ep_video_id = YoutubeIE._match_id(ep_url)
            if video_id == ep_video_id:
                continue
            yield self.url_result(ep_url, ie=YoutubeIE.ie_key(), video_id=video_id)

    def _post_thread_continuation_entries(self, post_thread_continuation):
        contents = post_thread_continuation.get('contents')
        if not isinstance(contents, list):
            return
        for content in contents:
            renderer = content.get('backstagePostThreadRenderer')
            if not isinstance(renderer, dict):
                continue
            for entry in self._post_thread_entries(renderer):
                yield entry

    r''' # unused
    def _rich_grid_entries(self, contents):
        for content in contents:
            video_renderer = try_get(content, lambda x: x['richItemRenderer']['content']['videoRenderer'], dict)
            if video_renderer:
                entry = self._video_entry(video_renderer)
                if entry:
                    yield entry
    '''

    @staticmethod
    def _build_continuation_query(continuation, ctp=None):
        query = {
            'ctoken': continuation,
            'continuation': continuation,
        }
        if ctp:
            query['itct'] = ctp
        return query

    @staticmethod
    def _extract_next_continuation_data(renderer):
        next_continuation = try_get(
            renderer, lambda x: x['continuations'][0]['nextContinuationData'], dict)
        if not next_continuation:
            return
        continuation = next_continuation.get('continuation')
        if not continuation:
            return
        ctp = next_continuation.get('clickTrackingParams')
        return YoutubeTabIE._build_continuation_query(continuation, ctp)

    @classmethod
    def _extract_continuation(cls, renderer):
        next_continuation = cls._extract_next_continuation_data(renderer)
        if next_continuation:
            return next_continuation
        contents = []
        for key in ('contents', 'items'):
            contents.extend(try_get(renderer, lambda x: x[key], list) or [])
        for content in contents:
            if not isinstance(content, dict):
                continue
            continuation_ep = try_get(
                content, lambda x: x['continuationItemRenderer']['continuationEndpoint'],
                dict)
            if not continuation_ep:
                continue
            continuation = try_get(
                continuation_ep, lambda x: x['continuationCommand']['token'], compat_str)
            if not continuation:
                continue
            ctp = continuation_ep.get('clickTrackingParams')
            return YoutubeTabIE._build_continuation_query(continuation, ctp)

    def _entries(self, tab, item_id, identity_token, account_syncid, ytcfg):

        def extract_entries(parent_renderer):  # this needs to called again for continuation to work with feeds
            contents = try_get(parent_renderer, lambda x: x['contents'], list) or []
            for content in contents:
                if not isinstance(content, dict):
                    continue
                is_renderer = try_get(content, lambda x: x['itemSectionRenderer'], dict)
                if not is_renderer:
                    renderer = content.get('richItemRenderer')
                    if renderer:
                        for entry in self._rich_entries(renderer):
                            yield entry
                        continuation_list[0] = self._extract_continuation(parent_renderer)
                    continue
                isr_contents = try_get(is_renderer, lambda x: x['contents'], list) or []
                for isr_content in isr_contents:
                    if not isinstance(isr_content, dict):
                        continue

                    known_renderers = {
                        'playlistVideoListRenderer': self._playlist_entries,
                        'gridRenderer': self._grid_entries,
                        'shelfRenderer': lambda x: self._shelf_entries(x, tab.get('title') != 'Channels'),
                        'backstagePostThreadRenderer': self._post_thread_entries,
                        'videoRenderer': lambda x: [self._video_entry(x)],
                    }
                    for key, renderer in isr_content.items():
                        if key not in known_renderers:
                            continue
                        for entry in known_renderers[key](renderer):
                            if entry:
                                yield entry
                        continuation_list[0] = self._extract_continuation(renderer)
                        break

                if not continuation_list[0]:
                    continuation_list[0] = self._extract_continuation(is_renderer)

            if not continuation_list[0]:
                continuation_list[0] = self._extract_continuation(parent_renderer)

        continuation_list = [None]  # Python 2 doesnot support nonlocal
        tab_content = try_get(tab, lambda x: x['content'], dict)
        if not tab_content:
            return
        parent_renderer = (
            try_get(tab_content, lambda x: x['sectionListRenderer'], dict)
            or try_get(tab_content, lambda x: x['richGridRenderer'], dict) or {})
        for entry in extract_entries(parent_renderer):
            yield entry
        continuation = continuation_list[0]
        context = self._extract_context(ytcfg)
        visitor_data = try_get(context, lambda x: x['client']['visitorData'], compat_str)

        for page_num in itertools.count(1):
            if not continuation:
                break
            query = {
                'continuation': continuation['continuation'],
                'clickTracking': {'clickTrackingParams': continuation['itct']}
            }
            headers = self._generate_api_headers(ytcfg, identity_token, account_syncid, visitor_data)
            response = self._extract_response(
                item_id='%s page %s' % (item_id, page_num),
                query=query, headers=headers, ytcfg=ytcfg,
                check_get_keys=('continuationContents', 'onResponseReceivedActions', 'onResponseReceivedEndpoints'))

            if not response:
                break
            visitor_data = try_get(
                response, lambda x: x['responseContext']['visitorData'], compat_str) or visitor_data

            known_continuation_renderers = {
                'playlistVideoListContinuation': self._playlist_entries,
                'gridContinuation': self._grid_entries,
                'itemSectionContinuation': self._post_thread_continuation_entries,
                'sectionListContinuation': extract_entries,  # for feeds
            }
            continuation_contents = try_get(
                response, lambda x: x['continuationContents'], dict) or {}
            continuation_renderer = None
            for key, value in continuation_contents.items():
                if key not in known_continuation_renderers:
                    continue
                continuation_renderer = value
                continuation_list = [None]
                for entry in known_continuation_renderers[key](continuation_renderer):
                    yield entry
                continuation = continuation_list[0] or self._extract_continuation(continuation_renderer)
                break
            if continuation_renderer:
                continue

            known_renderers = {
                'gridPlaylistRenderer': (self._grid_entries, 'items'),
                'gridVideoRenderer': (self._grid_entries, 'items'),
                'playlistVideoRenderer': (self._playlist_entries, 'contents'),
                'itemSectionRenderer': (extract_entries, 'contents'),  # for feeds
                'richItemRenderer': (extract_entries, 'contents'),  # for hashtag
                'backstagePostThreadRenderer': (self._post_thread_continuation_entries, 'contents')
            }
            on_response_received = dict_get(response, ('onResponseReceivedActions', 'onResponseReceivedEndpoints'))
            continuation_items = try_get(
                on_response_received, lambda x: x[0]['appendContinuationItemsAction']['continuationItems'], list)
            continuation_item = try_get(continuation_items, lambda x: x[0], dict) or {}
            video_items_renderer = None
            for key, value in continuation_item.items():
                if key not in known_renderers:
                    continue
                video_items_renderer = {known_renderers[key][1]: continuation_items}
                continuation_list = [None]
                for entry in known_renderers[key][0](video_items_renderer):
                    yield entry
                continuation = continuation_list[0] or self._extract_continuation(video_items_renderer)
                break
            if video_items_renderer:
                continue
            break

    @staticmethod
    def _extract_selected_tab(tabs):
        for tab in tabs:
            if try_get(tab, lambda x: x['tabRenderer']['selected'], bool):
                return tab['tabRenderer']
        else:
            raise ExtractorError('Unable to find selected tab')

    @staticmethod
    def _extract_uploader(data):
        uploader = {}
        sidebar_renderer = try_get(
            data, lambda x: x['sidebar']['playlistSidebarRenderer']['items'], list)
        if sidebar_renderer:
            for item in sidebar_renderer:
                if not isinstance(item, dict):
                    continue
                renderer = item.get('playlistSidebarSecondaryInfoRenderer')
                if not isinstance(renderer, dict):
                    continue
                owner = try_get(
                    renderer, lambda x: x['videoOwner']['videoOwnerRenderer']['title']['runs'][0], dict)
                if owner:
                    uploader['uploader'] = owner.get('text')
                    uploader['uploader_id'] = try_get(
                        owner, lambda x: x['navigationEndpoint']['browseEndpoint']['browseId'], compat_str)
                    uploader['uploader_url'] = urljoin(
                        'https://www.youtube.com/',
                        try_get(owner, lambda x: x['navigationEndpoint']['browseEndpoint']['canonicalBaseUrl'], compat_str))
        return {k: v for k, v in uploader.items() if v is not None}

    def _extract_from_tabs(self, item_id, webpage, data, tabs):
        playlist_id = title = description = channel_url = channel_name = channel_id = None
        thumbnails_list = tags = []

        selected_tab = self._extract_selected_tab(tabs)
        renderer = try_get(
            data, lambda x: x['metadata']['channelMetadataRenderer'], dict)
        if renderer:
            channel_name = renderer.get('title')
            channel_url = renderer.get('channelUrl')
            channel_id = renderer.get('externalId')
        else:
            renderer = try_get(
                data, lambda x: x['metadata']['playlistMetadataRenderer'], dict)

        if renderer:
            title = renderer.get('title')
            description = renderer.get('description', '')
            playlist_id = channel_id
            tags = renderer.get('keywords', '').split()
            thumbnails_list = (
                try_get(renderer, lambda x: x['avatar']['thumbnails'], list)
                or try_get(
                    data,
                    lambda x: x['sidebar']['playlistSidebarRenderer']['items'][0]['playlistSidebarPrimaryInfoRenderer']['thumbnailRenderer']['playlistVideoThumbnailRenderer']['thumbnail']['thumbnails'],
                    list)
                or [])

        thumbnails = []
        for t in thumbnails_list:
            if not isinstance(t, dict):
                continue
            thumbnail_url = url_or_none(t.get('url'))
            if not thumbnail_url:
                continue
            thumbnails.append({
                'url': thumbnail_url,
                'width': int_or_none(t.get('width')),
                'height': int_or_none(t.get('height')),
            })
        if playlist_id is None:
            playlist_id = item_id
        if title is None:
            title = (
                try_get(data, lambda x: x['header']['hashtagHeaderRenderer']['hashtag']['simpleText'])
                or playlist_id)
        title += format_field(selected_tab, 'title', ' - %s')

        metadata = {
            'playlist_id': playlist_id,
            'playlist_title': title,
            'playlist_description': description,
            'uploader': channel_name,
            'uploader_id': channel_id,
            'uploader_url': channel_url,
            'thumbnails': thumbnails,
            'tags': tags,
        }
        if not channel_id:
            metadata.update(self._extract_uploader(data))
        metadata.update({
            'channel': metadata['uploader'],
            'channel_id': metadata['uploader_id'],
            'channel_url': metadata['uploader_url']})
        return self.playlist_result(
            self._entries(
                selected_tab, playlist_id,
                self._extract_identity_token(webpage, item_id),
                self._extract_account_syncid(data),
                self._extract_ytcfg(item_id, webpage)),
            **metadata)

    def _extract_mix_playlist(self, playlist, playlist_id, data, webpage):
        first_id = last_id = None
        ytcfg = self._extract_ytcfg(playlist_id, webpage)
        headers = self._generate_api_headers(
            ytcfg, account_syncid=self._extract_account_syncid(data),
            identity_token=self._extract_identity_token(webpage, item_id=playlist_id),
            visitor_data=try_get(self._extract_context(ytcfg), lambda x: x['client']['visitorData'], compat_str))
        for page_num in itertools.count(1):
            videos = list(self._playlist_entries(playlist))
            if not videos:
                return
            start = next((i for i, v in enumerate(videos) if v['id'] == last_id), -1) + 1
            if start >= len(videos):
                return
            for video in videos[start:]:
                if video['id'] == first_id:
                    self.to_screen('First video %s found again; Assuming end of Mix' % first_id)
                    return
                yield video
            first_id = first_id or videos[0]['id']
            last_id = videos[-1]['id']
            watch_endpoint = try_get(
                playlist, lambda x: x['contents'][-1]['playlistPanelVideoRenderer']['navigationEndpoint']['watchEndpoint'])
            query = {
                'playlistId': playlist_id,
                'videoId': watch_endpoint.get('videoId') or last_id,
                'index': watch_endpoint.get('index') or len(videos),
                'params': watch_endpoint.get('params') or 'OAE%3D'
            }
            response = self._extract_response(
                item_id='%s page %d' % (playlist_id, page_num),
                query=query,
                ep='next',
                headers=headers,
                check_get_keys='contents'
            )
            playlist = try_get(
                response, lambda x: x['contents']['twoColumnWatchNextResults']['playlist']['playlist'], dict)

    def _extract_from_playlist(self, item_id, url, data, playlist, webpage):
        title = playlist.get('title') or try_get(
            data, lambda x: x['titleText']['simpleText'], compat_str)
        playlist_id = playlist.get('playlistId') or item_id

        # Delegating everything except mix playlists to regular tab-based playlist URL
        playlist_url = urljoin(url, try_get(
            playlist, lambda x: x['endpoint']['commandMetadata']['webCommandMetadata']['url'],
            compat_str))
        if playlist_url and playlist_url != url:
            return self.url_result(
                playlist_url, ie=YoutubeTabIE.ie_key(), video_id=playlist_id,
                video_title=title)

        return self.playlist_result(
            self._extract_mix_playlist(playlist, playlist_id, data, webpage),
            playlist_id=playlist_id, playlist_title=title)

    def _extract_alerts(self, data, expected=False):

        def _real_extract_alerts():
            for alert_dict in try_get(data, lambda x: x['alerts'], list) or []:
                if not isinstance(alert_dict, dict):
                    continue
                for alert in alert_dict.values():
                    alert_type = alert.get('type')
                    if not alert_type:
                        continue
                    message = try_get(alert, lambda x: x['text']['simpleText'], compat_str) or ''
                    if message:
                        yield alert_type, message
                    for run in try_get(alert, lambda x: x['text']['runs'], list) or []:
                        message += try_get(run, lambda x: x['text'], compat_str)
                    if message:
                        yield alert_type, message

        errors = []
        warnings = []
        for alert_type, alert_message in _real_extract_alerts():
            if alert_type.lower() == 'error':
                errors.append([alert_type, alert_message])
            else:
                warnings.append([alert_type, alert_message])

        for alert_type, alert_message in (warnings + errors[:-1]):
            self.report_warning('YouTube said: %s - %s' % (alert_type, alert_message))
        if errors:
            raise ExtractorError('YouTube said: %s' % errors[-1][1], expected=expected)

    def _reload_with_unavailable_videos(self, item_id, data, webpage):
        """
        Get playlist with unavailable videos if the 'show unavailable videos' button exists.
        """
        sidebar_renderer = try_get(
            data, lambda x: x['sidebar']['playlistSidebarRenderer']['items'], list)
        if not sidebar_renderer:
            return
        browse_id = params = None
        for item in sidebar_renderer:
            if not isinstance(item, dict):
                continue
            renderer = item.get('playlistSidebarPrimaryInfoRenderer')
            menu_renderer = try_get(
                renderer, lambda x: x['menu']['menuRenderer']['items'], list) or []
            for menu_item in menu_renderer:
                if not isinstance(menu_item, dict):
                    continue
                nav_item_renderer = menu_item.get('menuNavigationItemRenderer')
                text = try_get(
                    nav_item_renderer, lambda x: x['text']['simpleText'], compat_str)
                if not text or text.lower() != 'show unavailable videos':
                    continue
                browse_endpoint = try_get(
                    nav_item_renderer, lambda x: x['navigationEndpoint']['browseEndpoint'], dict) or {}
                browse_id = browse_endpoint.get('browseId')
                params = browse_endpoint.get('params')
                break

            ytcfg = self._extract_ytcfg(item_id, webpage)
            headers = self._generate_api_headers(
                ytcfg, account_syncid=self._extract_account_syncid(ytcfg),
                identity_token=self._extract_identity_token(webpage, item_id=item_id),
                visitor_data=try_get(
                    self._extract_context(ytcfg), lambda x: x['client']['visitorData'], compat_str))
            query = {
                'params': params or 'wgYCCAA=',
                'browseId': browse_id or 'VL%s' % item_id
            }
            return self._extract_response(
                item_id=item_id, headers=headers, query=query,
                check_get_keys='contents', fatal=False,
                note='Downloading API JSON with unavailable videos')

    def _extract_response(self, item_id, query, note='Downloading API JSON', headers=None,
                          ytcfg=None, check_get_keys=None, ep='browse', fatal=True):
        response = None
        last_error = None
        count = -1
        retries = self._downloader.params.get('extractor_retries', 3)
        if check_get_keys is None:
            check_get_keys = []
        while count < retries:
            count += 1
            if last_error:
                self.report_warning('%s. Retrying ...' % last_error)
            try:
                response = self._call_api(
                    ep=ep, fatal=True, headers=headers,
                    video_id=item_id, query=query,
                    context=self._extract_context(ytcfg),
                    api_key=self._extract_api_key(ytcfg),
                    note='%s%s' % (note, ' (retry #%d)' % count if count else ''))
            except ExtractorError as e:
                if isinstance(e.cause, compat_HTTPError) and e.cause.code in (500, 503, 404):
                    # Downloading page may result in intermittent 5xx HTTP error
                    # Sometimes a 404 is also recieved. See: https://github.com/ytdl-org/youtube-dl/issues/28289
                    last_error = 'HTTP Error %s' % e.cause.code
                    if count < retries:
                        continue
                if fatal:
                    raise
                else:
                    self.report_warning(error_to_compat_str(e))
                    return

            else:
                # Youtube may send alerts if there was an issue with the continuation page
                self._extract_alerts(response, expected=False)
                if not check_get_keys or dict_get(response, check_get_keys):
                    break
                # Youtube sometimes sends incomplete data
                # See: https://github.com/ytdl-org/youtube-dl/issues/28194
                last_error = 'Incomplete data received'
                if count >= retries:
                    if fatal:
                        raise ExtractorError(last_error)
                    else:
                        self.report_warning(last_error)
                        return
        return response

    def _extract_webpage(self, url, item_id):
        retries = self._downloader.params.get('extractor_retries', 3)
        count = -1
        last_error = 'Incomplete yt initial data recieved'
        while count < retries:
            count += 1
            # Sometimes youtube returns a webpage with incomplete ytInitialData
            # See: https://github.com/yt-dlp/yt-dlp/issues/116
            if count:
                self.report_warning('%s. Retrying ...' % last_error)
            webpage = self._download_webpage(
                url, item_id,
                'Downloading webpage%s' % (' (retry #%d)' % count if count else ''))
            data = self._extract_yt_initial_data(item_id, webpage)
            self._extract_alerts(data, expected=True)
            if data.get('contents') or data.get('currentVideoEndpoint'):
                break
            if count >= retries:
                raise ExtractorError(last_error)
        return webpage, data

    def _real_extract(self, url):
        item_id = self._match_id(url)
        url = compat_urlparse.urlunparse(
            compat_urlparse.urlparse(url)._replace(netloc='www.youtube.com'))

        # This is not matched in a channel page with a tab selected
        mobj = re.match(r'(?P<pre>%s)(?P<post>/?(?![^#?]).*$)' % self._VALID_URL, url)
        mobj = mobj.groupdict() if mobj else {}
        if mobj and not mobj.get('not_channel'):
            self.report_warning(
                'A channel/user page was given. All the channel\'s videos will be downloaded. '
                'To download only the videos in the home page, add a "/featured" to the URL')
            url = '%s/videos%s' % (mobj.get('pre'), mobj.get('post') or '')

        # Handle both video/playlist URLs
        qs = parse_qs(url)
        video_id = qs.get('v', [None])[0]
        playlist_id = qs.get('list', [None])[0]

        if not video_id and (mobj.get('not_channel') or '').startswith('watch'):
            if not playlist_id:
                # If there is neither video or playlist ids,
                # youtube redirects to home page, which is undesirable
                raise ExtractorError('Unable to recognize tab page')
            self.report_warning('A video URL was given without video ID. Trying to download playlist %s' % playlist_id)
            url = 'https://www.youtube.com/playlist?list=%s' % playlist_id

        if video_id and playlist_id:
            if self._downloader.params.get('noplaylist'):
                self.to_screen('Downloading just video %s because of --no-playlist' % video_id)
                return self.url_result(video_id, ie=YoutubeIE.ie_key(), video_id=video_id)
            self.to_screen('Downloading playlist %s; add --no-playlist to just download video %s' % (playlist_id, video_id))

        webpage, data = self._extract_webpage(url, item_id)

        # YouTube sometimes provides a button to reload playlist with unavailable videos.
        data = self._reload_with_unavailable_videos(item_id, data, webpage) or data

        tabs = try_get(
            data, lambda x: x['contents']['twoColumnBrowseResultsRenderer']['tabs'], list)
        if tabs:
            return self._extract_from_tabs(item_id, webpage, data, tabs)

        playlist = try_get(
            data, lambda x: x['contents']['twoColumnWatchNextResults']['playlist']['playlist'], dict)
        if playlist:
            return self._extract_from_playlist(item_id, url, data, playlist, webpage)

        video_id = try_get(
            data, lambda x: x['currentVideoEndpoint']['watchEndpoint']['videoId'],
            compat_str) or video_id
        if video_id:
            self.report_warning('Unable to recognize playlist. Downloading just video %s' % video_id)
            return self.url_result(video_id, ie=YoutubeIE.ie_key(), video_id=video_id)

        raise ExtractorError('Unable to recognize tab page')


class YoutubePlaylistIE(InfoExtractor):
    IE_DESC = 'YouTube.com playlists'
    _VALID_URL = r'''(?x)(?:
                        (?:https?://)?
                        (?:\w+\.)?
                        (?:
                            (?:
                                youtube(?:kids)?\.com|
                                invidio\.us
                            )
                            /.*?\?.*?\blist=
                        )?
                        (?P<id>%(playlist_id)s)
                     )''' % {'playlist_id': YoutubeBaseInfoExtractor._PLAYLIST_ID_RE}
    IE_NAME = 'youtube:playlist'
    _TESTS = [{
        'note': 'issue #673',
        'url': 'PLBB231211A4F62143',
        'info_dict': {
            'title': '[OLD]Team Fortress 2 (Class-based LP)',
            'id': 'PLBB231211A4F62143',
            'uploader': 'Wickydoo',
            'uploader_id': 'UCKSpbfbl5kRQpTdL7kMc-1Q',
        },
        'playlist_mincount': 29,
    }, {
        'url': 'PLtPgu7CB4gbY9oDN3drwC3cMbJggS7dKl',
        'info_dict': {
            'title': 'YDL_safe_search',
            'id': 'PLtPgu7CB4gbY9oDN3drwC3cMbJggS7dKl',
        },
        'playlist_count': 2,
        'skip': 'This playlist is private',
    }, {
        'note': 'embedded',
        'url': 'https://www.youtube.com/embed/videoseries?list=PL6IaIsEjSbf96XFRuNccS_RuEXwNdsoEu',
        'playlist_count': 4,
        'info_dict': {
            'title': 'JODA15',
            'id': 'PL6IaIsEjSbf96XFRuNccS_RuEXwNdsoEu',
            'uploader': 'milan',
            'uploader_id': 'UCEI1-PVPcYXjB73Hfelbmaw',
        }
    }, {
        'url': 'http://www.youtube.com/embed/_xDOZElKyNU?list=PLsyOSbh5bs16vubvKePAQ1x3PhKavfBIl',
        'playlist_mincount': 982,
        'info_dict': {
            'title': '2018 Chinese New Singles (11/6 updated)',
            'id': 'PLsyOSbh5bs16vubvKePAQ1x3PhKavfBIl',
            'uploader': 'LBK',
            'uploader_id': 'UC21nz3_MesPLqtDqwdvnoxA',
        }
    }, {
        'url': 'TLGGrESM50VT6acwMjAyMjAxNw',
        'only_matching': True,
    }, {
        # music album playlist
        'url': 'OLAK5uy_m4xAFdmMC5rX3Ji3g93pQe3hqLZw_9LhM',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        if YoutubeTabIE.suitable(url):
            return False
        # Hack for lazy extractors until more generic solution is implemented
        # (see #28780)
        from .youtube import parse_qs
        qs = parse_qs(url)
        if qs.get('v', [None])[0]:
            return False
        return super(YoutubePlaylistIE, cls).suitable(url)

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        qs = parse_qs(url)
        if not qs:
            qs = {'list': playlist_id}
        return self.url_result(
            update_url_query('https://www.youtube.com/playlist', qs),
            ie=YoutubeTabIE.ie_key(), video_id=playlist_id)


class YoutubeYtBeIE(InfoExtractor):
    IE_DESC = 'youtu.be'
    _VALID_URL = r'https?://youtu\.be/(?P<id>[0-9A-Za-z_-]{11})/*?.*?\blist=(?P<playlist_id>%(playlist_id)s)' % {'playlist_id': YoutubeBaseInfoExtractor._PLAYLIST_ID_RE}
    _TESTS = [{
        'url': 'https://youtu.be/yeWKywCrFtk?list=PL2qgrgXsNUG5ig9cat4ohreBjYLAPC0J5',
        'info_dict': {
            'id': 'yeWKywCrFtk',
            'ext': 'mp4',
            'title': 'Small Scale Baler and Braiding Rugs',
            'uploader': 'Backus-Page House Museum',
            'uploader_id': 'backuspagemuseum',
            'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/backuspagemuseum',
            'upload_date': '20161008',
            'description': 'md5:800c0c78d5eb128500bffd4f0b4f2e8a',
            'categories': ['Nonprofits & Activism'],
            'tags': list,
            'like_count': int,
            'dislike_count': int,
        },
        'params': {
            'noplaylist': True,
            'skip_download': True,
        },
    }, {
        'url': 'https://youtu.be/uWyaPkt-VOI?list=PL9D9FC436B881BA21',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id')
        playlist_id = mobj.group('playlist_id')
        return self.url_result(
            update_url_query('https://www.youtube.com/watch', {
                'v': video_id,
                'list': playlist_id,
                'feature': 'youtu.be',
            }), ie=YoutubeTabIE.ie_key(), video_id=playlist_id)


class YoutubeYtUserIE(InfoExtractor):
    IE_DESC = 'YouTube.com user videos, URL or "ytuser" keyword'
    _VALID_URL = r'ytuser:(?P<id>.+)'
    _TESTS = [{
        'url': 'ytuser:phihag',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        user_id = self._match_id(url)
        return self.url_result(
            'https://www.youtube.com/user/%s' % user_id,
            ie=YoutubeTabIE.ie_key(), video_id=user_id)


class YoutubeFavouritesIE(YoutubeBaseInfoExtractor):
    IE_NAME = 'youtube:favorites'
    IE_DESC = 'YouTube.com liked videos, ":ytfav" for short (requires authentication)'
    _VALID_URL = r':ytfav(?:ou?rite)?s?'
    _LOGIN_REQUIRED = True
    _TESTS = [{
        'url': ':ytfav',
        'only_matching': True,
    }, {
        'url': ':ytfavorites',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        return self.url_result(
            'https://www.youtube.com/playlist?list=LL',
            ie=YoutubeTabIE.ie_key())


class YoutubeSearchIE(SearchInfoExtractor, YoutubeTabIE):
    IE_DESC = 'YouTube.com searches, "ytsearch" keyword'
    # there doesn't appear to be a real limit, for example if you search for
    # 'python' you get more than 8.000.000 results
    _MAX_RESULTS = float('inf')
    IE_NAME = 'youtube:search'
    _SEARCH_KEY = 'ytsearch'
    _SEARCH_PARAMS = None
    _TESTS = []

    def _entries(self, query, n):
        data = {'query': query}
        if self._SEARCH_PARAMS:
            data['params'] = self._SEARCH_PARAMS
        total = 0
        for page_num in itertools.count(1):
            search = self._extract_response(
                item_id='query "%s" page %s' % (query, page_num), ep='search', query=data,
                check_get_keys=('contents', 'onResponseReceivedCommands')
            )
            if not search:
                break
            slr_contents = try_get(
                search,
                (lambda x: x['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents'],
                 lambda x: x['onResponseReceivedCommands'][0]['appendContinuationItemsAction']['continuationItems']),
                list)
            if not slr_contents:
                break

            # Youtube sometimes adds promoted content to searches,
            # changing the index location of videos and token.
            # So we search through all entries till we find them.
            continuation_token = None
            for slr_content in slr_contents:
                if continuation_token is None:
                    continuation_token = try_get(
                        slr_content,
                        lambda x: x['continuationItemRenderer']['continuationEndpoint']['continuationCommand']['token'],
                        compat_str)

                isr_contents = try_get(
                    slr_content,
                    lambda x: x['itemSectionRenderer']['contents'],
                    list)
                if not isr_contents:
                    continue
                for content in isr_contents:
                    if not isinstance(content, dict):
                        continue
                    video = content.get('videoRenderer')
                    if not isinstance(video, dict):
                        continue
                    video_id = video.get('videoId')
                    if not video_id:
                        continue

                    yield self._extract_video(video)
                    total += 1
                    if total == n:
                        return

            if not continuation_token:
                break
            data['continuation'] = continuation_token

    def _get_n_results(self, query, n):
        """Get a specified number of results for a query"""
        return self.playlist_result(self._entries(query, n), query)


class YoutubeSearchDateIE(YoutubeSearchIE):
    IE_NAME = YoutubeSearchIE.IE_NAME + ':date'
    _SEARCH_KEY = 'ytsearchdate'
    IE_DESC = 'YouTube.com searches, newest videos first, "ytsearchdate" keyword'
    _SEARCH_PARAMS = 'CAI%3D'


class YoutubeSearchURLIE(YoutubeSearchIE):
    IE_DESC = 'YouTube.com search URLs'
    IE_NAME = YoutubeSearchIE.IE_NAME + '_url'
    _VALID_URL = r'https?://(?:www\.)?youtube\.com/results\?(.*?&)?(?:search_query|q)=(?:[^&]+)(?:[&]|$)'
    # _MAX_RESULTS = 100
    _TESTS = [{
        'url': 'https://www.youtube.com/results?baz=bar&search_query=youtube-dl+test+video&filters=video&lclk=video',
        'playlist_mincount': 5,
        'info_dict': {
            'title': 'youtube-dl test video',
        }
    }, {
        'url': 'https://www.youtube.com/results?q=test&sp=EgQIBBgB',
        'only_matching': True,
    }]

    @classmethod
    def _make_valid_url(cls):
        return cls._VALID_URL

    def _real_extract(self, url):
        qs = compat_parse_qs(compat_urllib_parse_urlparse(url).query)
        query = (qs.get('search_query') or qs.get('q'))[0]
        self._SEARCH_PARAMS = qs.get('sp', ('',))[0]
        return self._get_n_results(query, self._MAX_RESULTS)


class YoutubeFeedsInfoExtractor(YoutubeTabIE):
    """
    Base class for feed extractors
    Subclasses must define the _FEED_NAME property.
    """
    _LOGIN_REQUIRED = True
    _TESTS = []

    @property
    def IE_NAME(self):
        return 'youtube:%s' % self._FEED_NAME

    def _real_initialize(self):
        self._login()

    def _real_extract(self, url):
        return self.url_result(
            'https://www.youtube.com/feed/%s' % self._FEED_NAME,
            ie=YoutubeTabIE.ie_key())


class YoutubeWatchLaterIE(InfoExtractor):
    IE_NAME = 'youtube:watchlater'
    IE_DESC = 'Youtube watch later list, ":ytwatchlater" for short (requires authentication)'
    _VALID_URL = r':ytwatchlater'
    _TESTS = [{
        'url': ':ytwatchlater',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        return self.url_result(
            'https://www.youtube.com/playlist?list=WL', ie=YoutubeTabIE.ie_key())


class YoutubeRecommendedIE(YoutubeFeedsInfoExtractor):
    IE_DESC = 'YouTube.com recommended videos, ":ytrec" for short (requires authentication)'
    _VALID_URL = r'https?://(?:www\.)?youtube\.com/?(?:[?#]|$)|:ytrec(?:ommended)?'
    _FEED_NAME = 'recommended'
    _TESTS = [{
        'url': ':ytrec',
        'only_matching': True,
    }, {
        'url': ':ytrecommended',
        'only_matching': True,
    }, {
        'url': 'https://youtube.com',
        'only_matching': True,
    }]


class YoutubeSubscriptionsIE(YoutubeFeedsInfoExtractor):
    IE_DESC = 'YouTube.com subscriptions feed, ":ytsubs" for short (requires authentication)'
    _VALID_URL = r':ytsub(?:scription)?s?'
    _FEED_NAME = 'subscriptions'
    _TESTS = [{
        'url': ':ytsubs',
        'only_matching': True,
    }, {
        'url': ':ytsubscriptions',
        'only_matching': True,
    }]


class YoutubeHistoryIE(YoutubeFeedsInfoExtractor):
    IE_DESC = 'Youtube watch history, ":ythis" for short (requires authentication)'
    _VALID_URL = r':ythis(?:tory)?'
    _FEED_NAME = 'history'
    _TESTS = [{
        'url': ':ythistory',
        'only_matching': True,
    }]


class YoutubeTruncatedURLIE(InfoExtractor):
    IE_NAME = 'youtube:truncated_url'
    IE_DESC = False  # Do not list
    _VALID_URL = r'''(?x)
        (?:https?://)?
        (?:\w+\.)?[yY][oO][uU][tT][uU][bB][eE](?:-nocookie)?\.com/
        (?:watch\?(?:
            feature=[a-z_]+|
            annotation_id=annotation_[^&]+|
            x-yt-cl=[0-9]+|
            hl=[^&]*|
            t=[0-9]+
        )?
        |
            attribution_link\?a=[^&]+
        )
        $
    '''

    _TESTS = [{
        'url': 'https://www.youtube.com/watch?annotation_id=annotation_3951667041',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/watch?',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/watch?x-yt-cl=84503534',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/watch?feature=foo',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/watch?hl=en-GB',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/watch?t=2372',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        raise ExtractorError(
            'Did you forget to quote the URL? Remember that & is a meta '
            'character in most shells, so you want to put the URL in quotes, '
            'like  youtube-dl '
            '"https://www.youtube.com/watch?feature=foo&v=BaW_jenozKc" '
            ' or simply  youtube-dl BaW_jenozKc  .',
            expected=True)


class YoutubeTruncatedIDIE(InfoExtractor):
    IE_NAME = 'youtube:truncated_id'
    IE_DESC = False  # Do not list
    _VALID_URL = r'https?://(?:www\.)?youtube\.com/watch\?v=(?P<id>[0-9A-Za-z_-]{1,10})$'

    _TESTS = [{
        'url': 'https://www.youtube.com/watch?v=N_708QY7Ob',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        raise ExtractorError(
            'Incomplete YouTube ID %s. URL %s looks truncated.' % (video_id, url),
            expected=True)
