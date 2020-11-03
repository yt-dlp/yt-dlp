# coding: utf-8

from __future__ import unicode_literals


import itertools
import json
import os.path
import random
import re
import time
import traceback

from .common import InfoExtractor, SearchInfoExtractor
from ..jsinterp import JSInterpreter
from ..swfinterp import SWFInterpreter
from ..compat import (
    compat_chr,
    compat_HTTPError,
    compat_kwargs,
    compat_parse_qs,
    compat_urllib_parse_unquote,
    compat_urllib_parse_unquote_plus,
    compat_urllib_parse_urlencode,
    compat_urllib_parse_urlparse,
    compat_urlparse,
    compat_str,
)
from ..utils import (
    bool_or_none,
    clean_html,
    error_to_compat_str,
    extract_attributes,
    ExtractorError,
    float_or_none,
    get_element_by_attribute,
    get_element_by_id,
    int_or_none,
    mimetype2ext,
    orderedSet,
    parse_codecs,
    parse_count,
    parse_duration,
    remove_quotes,
    remove_start,
    smuggle_url,
    str_or_none,
    str_to_int,
    try_get,
    unescapeHTML,
    unified_strdate,
    unsmuggle_url,
    uppercase_escape,
    url_or_none,
    urlencode_postdata,
)


class YoutubeBaseInfoExtractor(InfoExtractor):
    """Provide base functions for Youtube extractors"""
    _LOGIN_URL = 'https://accounts.google.com/ServiceLogin'
    _TWOFACTOR_URL = 'https://accounts.google.com/signin/challenge'

    _LOOKUP_URL = 'https://accounts.google.com/_/signin/sl/lookup'
    _CHALLENGE_URL = 'https://accounts.google.com/_/signin/sl/challenge'
    _TFA_URL = 'https://accounts.google.com/_/signin/challenge?hl=en&TL={0}'

    _NETRC_MACHINE = 'youtube'
    # If True it will raise an error if no login info is provided
    _LOGIN_REQUIRED = False

    _PLAYLIST_ID_RE = r'(?:PL|LL|EC|UU|FL|RD|UL|TL|PU|OLAK5uy_)[0-9A-Za-z-_]{10,}'

    _YOUTUBE_CLIENT_HEADERS = {
        'x-youtube-client-name': '1',
        'x-youtube-client-version': '1.20200609.04.02',
    }

    def _set_language(self):
        self._set_cookie(
            '.youtube.com', 'PREF', 'f1=50000000&f6=8&hl=en',
            # YouTube sets the expire time to about two months
            expire_time=time.time() + 2 * 30 * 24 * 3600)

    def _ids_to_results(self, ids):
        return [
            self.url_result(vid_id, 'Youtube', video_id=vid_id)
            for vid_id in ids]

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
            if self._downloader.params.get('cookiefile') and False:  # TODO remove 'and False' later - too many people using outdated cookies and open issues, remind them.
                self.to_screen('[Cookies] Reminder - Make sure to always use up to date cookies!')
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
            self._downloader.report_warning(message)

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

    def _download_webpage_handle(self, *args, **kwargs):
        query = kwargs.get('query', {}).copy()
        query['disable_polymer'] = 'true'
        kwargs['query'] = query
        return super(YoutubeBaseInfoExtractor, self)._download_webpage_handle(
            *args, **compat_kwargs(kwargs))

    def _get_yt_initial_data(self, video_id, webpage):
        config = self._search_regex(
            (r'window\["ytInitialData"\]\s*=\s*(.*?)(?<=});',
             r'var\s+ytInitialData\s*=\s*(.*?)(?<=});'),
            webpage, 'ytInitialData', default=None)
        if config:
            return self._parse_json(
                uppercase_escape(config), video_id, fatal=False)

    def _real_initialize(self):
        if self._downloader is None:
            return
        self._set_language()
        if not self._login():
            return


class YoutubeEntryListBaseInfoExtractor(YoutubeBaseInfoExtractor):
    # Extract entries from page with "Load more" button
    def _entries(self, page, playlist_id):
        more_widget_html = content_html = page
        for page_num in itertools.count(1):
            for entry in self._process_page(content_html):
                yield entry

            mobj = re.search(r'data-uix-load-more-href="/?(?P<more>[^"]+)"', more_widget_html)
            if not mobj:
                break

            count = 0
            retries = 3
            while count <= retries:
                try:
                    # Downloading page may result in intermittent 5xx HTTP error
                    # that is usually worked around with a retry
                    more = self._download_json(
                        'https://www.youtube.com/%s' % mobj.group('more'), playlist_id,
                        'Downloading page #%s%s'
                        % (page_num, ' (retry #%d)' % count if count else ''),
                        transform_source=uppercase_escape,
                        headers=self._YOUTUBE_CLIENT_HEADERS)
                    break
                except ExtractorError as e:
                    if isinstance(e.cause, compat_HTTPError) and e.cause.code in (500, 503):
                        count += 1
                        if count <= retries:
                            continue
                    raise

            content_html = more['content_html']
            if not content_html.strip():
                # Some webpages show a "Load more" button but they don't
                # have more videos
                break
            more_widget_html = more['load_more_widget_html']


class YoutubePlaylistBaseInfoExtractor(YoutubeEntryListBaseInfoExtractor):
    def _process_page(self, content):
        for video_id, video_title in self.extract_videos_from_page(content):
            yield self.url_result(video_id, 'Youtube', video_id, video_title)

    def extract_videos_from_page_impl(self, video_re, page, ids_in_page, titles_in_page):
        for mobj in re.finditer(video_re, page):
            # The link with index 0 is not the first video of the playlist (not sure if still actual)
            if 'index' in mobj.groupdict() and mobj.group('id') == '0':
                continue
            video_id = mobj.group('id')
            video_title = unescapeHTML(
                mobj.group('title')) if 'title' in mobj.groupdict() else None
            if video_title:
                video_title = video_title.strip()
            if video_title == '► Play all':
                video_title = None
            try:
                idx = ids_in_page.index(video_id)
                if video_title and not titles_in_page[idx]:
                    titles_in_page[idx] = video_title
            except ValueError:
                ids_in_page.append(video_id)
                titles_in_page.append(video_title)

    def extract_videos_from_page(self, page):
        ids_in_page = []
        titles_in_page = []
        self.extract_videos_from_page_impl(
            self._VIDEO_RE, page, ids_in_page, titles_in_page)
        return zip(ids_in_page, titles_in_page)


class YoutubePlaylistsBaseInfoExtractor(YoutubeEntryListBaseInfoExtractor):
    def _process_page(self, content):
        for playlist_id in orderedSet(re.findall(
                r'<h3[^>]+class="[^"]*yt-lockup-title[^"]*"[^>]*><a[^>]+href="/?playlist\?list=([0-9A-Za-z-_]{10,})"',
                content)):
            yield self.url_result(
                'https://www.youtube.com/playlist?list=%s' % playlist_id, 'YoutubePlaylist')

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)
        title = self._og_search_title(webpage, fatal=False)
        return self.playlist_result(self._entries(webpage, playlist_id), playlist_id, title)


class YoutubeIE(YoutubeBaseInfoExtractor):
    IE_DESC = 'YouTube.com'
    _VALID_URL = r"""(?x)^
                     (
                         (?:https?://|//)                                    # http(s):// or protocol-independent URL
                         (?:(?:(?:(?:\w+\.)?[yY][oO][uU][tT][uU][bB][eE](?:-nocookie|kids)?\.com/|
                            (?:www\.)?deturl\.com/www\.youtube\.com/|
                            (?:www\.)?pwnyoutube\.com/|
                            (?:www\.)?hooktube\.com/|
                            (?:www\.)?yourepeat\.com/|
                            tube\.majestyc\.net/|
                            # Invidious instances taken from https://github.com/omarroth/invidious/wiki/Invidious-Instances
                            (?:(?:www|dev)\.)?invidio\.us/|
                            (?:(?:www|no)\.)?invidiou\.sh/|
                            (?:(?:www|fi|de)\.)?invidious\.snopyta\.org/|
                            (?:www\.)?invidious\.kabi\.tk/|
                            (?:www\.)?invidious\.13ad\.de/|
                            (?:www\.)?invidious\.mastodon\.host/|
                            (?:www\.)?invidious\.nixnet\.xyz/|
                            (?:www\.)?invidious\.drycat\.fr/|
                            (?:www\.)?tube\.poal\.co/|
                            (?:www\.)?vid\.wxzm\.sx/|
                            (?:www\.)?yewtu\.be/|
                            (?:www\.)?yt\.elukerio\.org/|
                            (?:www\.)?yt\.lelux\.fi/|
                            (?:www\.)?invidious\.ggc-project\.de/|
                            (?:www\.)?yt\.maisputain\.ovh/|
                            (?:www\.)?invidious\.13ad\.de/|
                            (?:www\.)?invidious\.toot\.koeln/|
                            (?:www\.)?invidious\.fdn\.fr/|
                            (?:www\.)?watch\.nettohikari\.com/|
                            (?:www\.)?kgg2m7yk5aybusll\.onion/|
                            (?:www\.)?qklhadlycap4cnod\.onion/|
                            (?:www\.)?axqzx4s6s54s32yentfqojs3x5i7faxza6xo3ehd4bzzsg2ii4fv2iid\.onion/|
                            (?:www\.)?c7hqkpkpemu6e7emz5b4vyz7idjgdvgaaa3dyimmeojqbgpea3xqjoid\.onion/|
                            (?:www\.)?fz253lmuao3strwbfbmx46yu7acac2jz27iwtorgmbqlkurlclmancad\.onion/|
                            (?:www\.)?invidious\.l4qlywnpwqsluw65ts7md3khrivpirse744un3x7mlskqauz5pyuzgqd\.onion/|
                            (?:www\.)?owxfohz4kjyv25fvlqilyxast7inivgiktls3th44jhk3ej3i7ya\.b32\.i2p/|
                            (?:www\.)?4l2dgddgsrkf2ous66i6seeyi6etzfgrue332grh2n7madpwopotugyd\.onion/|
                            youtube\.googleapis\.com/)                        # the various hostnames, with wildcard subdomains
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
                         )/
                         |(?:www\.)?cleanvideosearch\.com/media/action/yt/watch\?videoId=
                         )
                     )?                                                       # all until now is optional -> you can pass the naked ID
                     ([0-9A-Za-z_-]{11})                                      # here is it! the YouTube video ID
                     (?!.*?\blist=
                        (?:
                            %(playlist_id)s|                                  # combined list/video URLs are handled by the playlist IE
                            WL                                                # WL are handled by the watch later IE
                        )
                     )
                     (?(1).+)?                                                # if we found the ID, everything can follow
                     $""" % {'playlist_id': YoutubeBaseInfoExtractor._PLAYLIST_ID_RE}
    _NEXT_URL_RE = r'[\?&]next_url=([^&]+)'
    _PLAYER_INFO_RE = (
        r'/(?P<id>[a-zA-Z0-9_-]{8,})/player_ias\.vflset(?:/[a-zA-Z]{2,3}_[a-zA-Z]{2,3})?/base\.(?P<ext>[a-z]+)$',
        r'\b(?P<id>vfl[a-zA-Z0-9_-]+)\b.*?\.(?P<ext>[a-z]+)$',
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
            }
        },
        {
            'url': 'https://www.youtube.com/watch?v=BaW_jenozKc&v=UxxajLWwzqY',
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
                'description': 'SUBSCRIBE: http://www.youtube.com/saturninefilms\n\nEven Obama has taken a stand against freedom on this issue: http://www.huffingtonpost.com/2010/09/09/obama-gma-interview-quran_n_710282.html',
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
            'url': 'https://www.youtube.com/watch?v=jqWvoWXjCVs',
            'info_dict': {
                'id': 'jqWvoWXjCVs',
                'title': 'teamPGP: Rocket League Noob Stream',
                'description': 'md5:dc7872fb300e143831327f1bae3af010',
            },
            'playlist': [{
                'info_dict': {
                    'id': 'jqWvoWXjCVs',
                    'ext': 'mp4',
                    'title': 'teamPGP: Rocket League Noob Stream (Main Camera)',
                    'description': 'md5:dc7872fb300e143831327f1bae3af010',
                    'duration': 7335,
                    'upload_date': '20150721',
                    'uploader': 'Beer Games Beer',
                    'uploader_id': 'beergamesbeer',
                    'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/beergamesbeer',
                    'license': 'Standard YouTube License',
                },
            }, {
                'info_dict': {
                    'id': '6h8e8xoXJzg',
                    'ext': 'mp4',
                    'title': 'teamPGP: Rocket League Noob Stream (kreestuh)',
                    'description': 'md5:dc7872fb300e143831327f1bae3af010',
                    'duration': 7337,
                    'upload_date': '20150721',
                    'uploader': 'Beer Games Beer',
                    'uploader_id': 'beergamesbeer',
                    'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/beergamesbeer',
                    'license': 'Standard YouTube License',
                },
            }, {
                'info_dict': {
                    'id': 'PUOgX5z9xZw',
                    'ext': 'mp4',
                    'title': 'teamPGP: Rocket League Noob Stream (grizzle)',
                    'description': 'md5:dc7872fb300e143831327f1bae3af010',
                    'duration': 7337,
                    'upload_date': '20150721',
                    'uploader': 'Beer Games Beer',
                    'uploader_id': 'beergamesbeer',
                    'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/beergamesbeer',
                    'license': 'Standard YouTube License',
                },
            }, {
                'info_dict': {
                    'id': 'teuwxikvS5k',
                    'ext': 'mp4',
                    'title': 'teamPGP: Rocket League Noob Stream (zim)',
                    'description': 'md5:dc7872fb300e143831327f1bae3af010',
                    'duration': 7334,
                    'upload_date': '20150721',
                    'uploader': 'Beer Games Beer',
                    'uploader_id': 'beergamesbeer',
                    'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/beergamesbeer',
                    'license': 'Standard YouTube License',
                },
            }],
            'params': {
                'skip_download': True,
            },
            'skip': 'This video is not available.',
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
                'description': 'md5:dda0d780d5a6e120758d1711d062a867',
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
                'description': 'md5:46a29be4ceffa65b92d277b93f463c0f',
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
            'url': 'https://www.youtube.com/watch?v=MuAGGZNfUkU&list=RDMM',
            'only_matching': True,
        },
        {
            'url': 'https://invidio.us/watch?v=BaW_jenozKc',
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
            # Youtube Music Auto-generated description
            # Retrieve 'artist' field from 'Artist:' in video description
            # when it is present on youtube music video
            'url': 'https://www.youtube.com/watch?v=k0jLE7tTwjY',
            'info_dict': {
                'id': 'k0jLE7tTwjY',
                'ext': 'mp4',
                'title': 'Latch Feat. Sam Smith',
                'description': 'md5:3cb1e8101a7c85fcba9b4fb41b951335',
                'upload_date': '20150110',
                'uploader': 'Various Artists - Topic',
                'uploader_id': 'UCNkEcmYdjrH4RqtNgh7BZ9w',
                'artist': 'Disclosure',
                'track': 'Latch Feat. Sam Smith',
                'album': 'Latch Featuring Sam Smith',
                'release_date': '20121008',
                'release_year': 2012,
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # Youtube Music Auto-generated description
            # handle multiple artists on youtube music video
            'url': 'https://www.youtube.com/watch?v=74qn0eJSjpA',
            'info_dict': {
                'id': '74qn0eJSjpA',
                'ext': 'mp4',
                'title': 'Eastside',
                'description': 'md5:290516bb73dcbfab0dcc4efe6c3de5f2',
                'upload_date': '20180710',
                'uploader': 'Benny Blanco - Topic',
                'uploader_id': 'UCzqz_ksRu_WkIzmivMdIS7A',
                'artist': 'benny blanco, Halsey, Khalid',
                'track': 'Eastside',
                'album': 'Eastside',
                'release_date': '20180713',
                'release_year': 2018,
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # Youtube Music Auto-generated description
            # handle youtube music video with release_year and no release_date
            'url': 'https://www.youtube.com/watch?v=-hcAI0g-f5M',
            'info_dict': {
                'id': '-hcAI0g-f5M',
                'ext': 'mp4',
                'title': 'Put It On Me',
                'description': 'md5:f6422397c07c4c907c6638e1fee380a5',
                'upload_date': '20180426',
                'uploader': 'Matt Maeson - Topic',
                'uploader_id': 'UCnEkIGqtGcQMLk73Kp-Q5LQ',
                'artist': 'Matt Maeson',
                'track': 'Put It On Me',
                'album': 'The Hearse',
                'release_date': None,
                'release_year': 2018,
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
    ]

    def __init__(self, *args, **kwargs):
        super(YoutubeIE, self).__init__(*args, **kwargs)
        self._player_cache = {}

    def report_video_info_webpage_download(self, video_id):
        """Report attempt to download video info webpage."""
        self.to_screen('%s: Downloading video info webpage' % video_id)

    def report_information_extraction(self, video_id):
        """Report attempt to extract video information."""
        self.to_screen('%s: Extracting video information' % video_id)

    def report_unavailable_format(self, video_id, format):
        """Report extracted video URL."""
        self.to_screen('%s: Format %s not available' % (video_id, format))

    def report_rtmp_download(self):
        """Indicate the download will use the RTMP protocol."""
        self.to_screen('RTMP download detected')

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
        return id_m.group('ext'), id_m.group('id')

    def _extract_signature_function(self, video_id, player_url, example_sig):
        player_type, player_id = self._extract_player_info(player_url)

        # Read from filesystem cache
        func_id = '%s_%s_%s' % (
            player_type, player_id, self._signature_cache_id(example_sig))
        assert os.path.basename(func_id) == func_id

        cache_spec = self._downloader.cache.load('youtube-sigfuncs', func_id)
        if cache_spec is not None:
            return lambda s: ''.join(s[i] for i in cache_spec)

        download_note = (
            'Downloading player %s' % player_url
            if self._downloader.params.get('verbose') else
            'Downloading %s player %s' % (player_type, player_id)
        )
        if player_type == 'js':
            code = self._download_webpage(
                player_url, video_id,
                note=download_note,
                errnote='Download of %s failed' % player_url)
            res = self._parse_sig_js(code)
        elif player_type == 'swf':
            urlh = self._request_webpage(
                player_url, video_id,
                note=download_note,
                errnote='Download of %s failed' % player_url)
            code = urlh.read()
            res = self._parse_sig_swf(code)
        else:
            assert False, 'Invalid player type %r' % player_type

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

    def _parse_sig_swf(self, file_contents):
        swfi = SWFInterpreter(file_contents)
        TARGET_CLASSNAME = 'SignatureDecipher'
        searched_class = swfi.extract_class(TARGET_CLASSNAME)
        initial_function = swfi.extract_function(searched_class, 'decipher')
        return lambda s: initial_function([s])

    def _decrypt_signature(self, s, video_id, player_url, age_gate=False):
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

    def _get_subtitles(self, video_id, webpage, has_live_chat_replay):
        try:
            subs_doc = self._download_xml(
                'https://video.google.com/timedtext?hl=en&type=list&v=%s' % video_id,
                video_id, note=False)
        except ExtractorError as err:
            self._downloader.report_warning('unable to download video subtitles: %s' % error_to_compat_str(err))
            return {}

        sub_lang_list = {}
        for track in subs_doc.findall('track'):
            lang = track.attrib['lang_code']
            if lang in sub_lang_list:
                continue
            sub_formats = []
            for ext in self._SUBTITLE_FORMATS:
                params = compat_urllib_parse_urlencode({
                    'lang': lang,
                    'v': video_id,
                    'fmt': ext,
                    'name': track.attrib['name'].encode('utf-8'),
                })
                sub_formats.append({
                    'url': 'https://www.youtube.com/api/timedtext?' + params,
                    'ext': ext,
                })
            sub_lang_list[lang] = sub_formats
        if has_live_chat_replay:
            sub_lang_list['live_chat'] = [
                {
                    'video_id': video_id,
                    'ext': 'json',
                    'protocol': 'youtube_live_chat_replay',
                },
            ]
        if not sub_lang_list:
            self._downloader.report_warning('video doesn\'t have subtitles')
            return {}
        return sub_lang_list

    def _get_ytplayer_config(self, video_id, webpage):
        patterns = (
            # User data may contain arbitrary character sequences that may affect
            # JSON extraction with regex, e.g. when '};' is contained the second
            # regex won't capture the whole JSON. Yet working around by trying more
            # concrete regex first keeping in mind proper quoted string handling
            # to be implemented in future that will replace this workaround (see
            # https://github.com/ytdl-org/youtube-dl/issues/7468,
            # https://github.com/ytdl-org/youtube-dl/pull/7599)
            r';ytplayer\.config\s*=\s*({.+?});ytplayer',
            r';ytplayer\.config\s*=\s*({.+?});',
            r'ytInitialPlayerResponse\s*=\s*({.+?});var meta'
        )
        config = self._search_regex(
            patterns, webpage, 'ytplayer.config', default=None)
        if config:
            return self._parse_json(
                uppercase_escape(config), video_id, fatal=False)

    def _get_music_metadata_from_yt_initial(self, yt_initial):
        music_metadata = []
        key_map = {
            'Album': 'album',
            'Artist': 'artist',
            'Song': 'track'
        }
        contents = try_get(yt_initial, lambda x: x['contents']['twoColumnWatchNextResults']['results']['results']['contents'])
        if type(contents) is list:
            for content in contents:
                music_track = {}
                if type(content) is not dict:
                    continue
                videoSecondaryInfoRenderer = try_get(content, lambda x: x['videoSecondaryInfoRenderer'])
                if type(videoSecondaryInfoRenderer) is not dict:
                    continue
                rows = try_get(videoSecondaryInfoRenderer, lambda x: x['metadataRowContainer']['metadataRowContainerRenderer']['rows'])
                if type(rows) is not list:
                    continue
                for row in rows:
                    metadataRowRenderer = try_get(row, lambda x: x['metadataRowRenderer'])
                    if type(metadataRowRenderer) is not dict:
                        continue
                    key = try_get(metadataRowRenderer, lambda x: x['title']['simpleText'])
                    value = try_get(metadataRowRenderer, lambda x: x['contents'][0]['simpleText']) or \
                        try_get(metadataRowRenderer, lambda x: x['contents'][0]['runs'][0]['text'])
                    if type(key) is not str or type(value) is not str:
                        continue
                    if key in key_map:
                        if key_map[key] in music_track:
                            # we've started on a new track
                            music_metadata.append(music_track)
                            music_track = {}
                        music_track[key_map[key]] = value
                if len(music_track.keys()):
                    music_metadata.append(music_track)
        return music_metadata

    def _get_automatic_captions(self, video_id, webpage):
        """We need the webpage for getting the captions url, pass it as an
           argument to speed up the process."""
        self.to_screen('%s: Looking for automatic captions' % video_id)
        player_config = self._get_ytplayer_config(video_id, webpage)
        err_msg = 'Couldn\'t find automatic captions for %s' % video_id
        if not player_config:
            self._downloader.report_warning(err_msg)
            return {}
        try:
            if "args" in player_config and "ttsurl" in player_config["args"]:
                args = player_config['args']
                caption_url = args['ttsurl']
                timestamp = args['timestamp']

                # We get the available subtitles
                list_params = compat_urllib_parse_urlencode({
                    'type': 'list',
                    'tlangs': 1,
                    'asrs': 1,
                })
                list_url = caption_url + '&' + list_params
                caption_list = self._download_xml(list_url, video_id)
                original_lang_node = caption_list.find('track')
                if original_lang_node is None:
                    self._downloader.report_warning('Video doesn\'t have automatic captions')
                    return {}
                original_lang = original_lang_node.attrib['lang_code']
                caption_kind = original_lang_node.attrib.get('kind', '')

                sub_lang_list = {}
                for lang_node in caption_list.findall('target'):
                    sub_lang = lang_node.attrib['lang_code']
                    sub_formats = []
                    for ext in self._SUBTITLE_FORMATS:
                        params = compat_urllib_parse_urlencode({
                            'lang': original_lang,
                            'tlang': sub_lang,
                            'fmt': ext,
                            'ts': timestamp,
                            'kind': caption_kind,
                        })
                        sub_formats.append({
                            'url': caption_url + '&' + params,
                            'ext': ext,
                        })
                    sub_lang_list[sub_lang] = sub_formats
                return sub_lang_list

            def make_captions(sub_url, sub_langs):
                parsed_sub_url = compat_urllib_parse_urlparse(sub_url)
                caption_qs = compat_parse_qs(parsed_sub_url.query)
                captions = {}
                for sub_lang in sub_langs:
                    sub_formats = []
                    for ext in self._SUBTITLE_FORMATS:
                        caption_qs.update({
                            'tlang': [sub_lang],
                            'fmt': [ext],
                        })
                        sub_url = compat_urlparse.urlunparse(parsed_sub_url._replace(
                            query=compat_urllib_parse_urlencode(caption_qs, True)))
                        sub_formats.append({
                            'url': sub_url,
                            'ext': ext,
                        })
                    captions[sub_lang] = sub_formats
                return captions

            # New captions format as of 22.06.2017
            if "args" in player_config:
                player_response = player_config["args"].get('player_response')
            else:
                # New player system (ytInitialPlayerResponse) as of October 2020
                player_response = player_config

            if player_response:
                if isinstance(player_response, compat_str):
                    player_response = self._parse_json(
                        player_response, video_id, fatal=False)

                renderer = player_response['captions']['playerCaptionsTracklistRenderer']
                caption_tracks = renderer['captionTracks']
                for caption_track in caption_tracks:
                    if 'kind' not in caption_track:
                        # not an automatic transcription
                        continue
                    base_url = caption_track['baseUrl']
                    sub_lang_list = []
                    for lang in renderer['translationLanguages']:
                        lang_code = lang.get('languageCode')
                        if lang_code:
                            sub_lang_list.append(lang_code)
                    return make_captions(base_url, sub_lang_list)

                self._downloader.report_warning("Couldn't find automatic captions for %s" % video_id)
                return {}

            if "args" in player_config:
                args = player_config["args"]

                # Some videos don't provide ttsurl but rather caption_tracks and
                # caption_translation_languages (e.g. 20LmZk1hakA)
                # Does not used anymore as of 22.06.2017
                caption_tracks = args['caption_tracks']
                caption_translation_languages = args['caption_translation_languages']
                caption_url = compat_parse_qs(caption_tracks.split(',')[0])['u'][0]
                sub_lang_list = []
                for lang in caption_translation_languages.split(','):
                    lang_qs = compat_parse_qs(compat_urllib_parse_unquote_plus(lang))
                    sub_lang = lang_qs.get('lc', [None])[0]
                    if sub_lang:
                        sub_lang_list.append(sub_lang)
                return make_captions(caption_url, sub_lang_list)
        # An extractor error can be raise by the download process if there are
        # no automatic captions but there are subtitles
        except (KeyError, IndexError, ExtractorError):
            self._downloader.report_warning(err_msg)
            return {}

    def _mark_watched(self, video_id, video_info, player_response):
        playback_url = url_or_none(try_get(
            player_response,
            lambda x: x['playbackTracking']['videostatsPlaybackUrl']['baseUrl']) or try_get(
            video_info, lambda x: x['videostats_playback_base_url'][0]))
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

    def _extract_chapters_from_json(self, webpage, video_id, duration):
        if not webpage:
            return
        initial_data = self._parse_json(
            self._search_regex(
                r'window\["ytInitialData"\] = (.+);\n', webpage,
                'player args', default='{}'),
            video_id, fatal=False)
        if not initial_data or not isinstance(initial_data, dict):
            return
        chapters_list = try_get(
            initial_data,
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

    @staticmethod
    def _extract_chapters_from_description(description, duration):
        if not description:
            return None
        chapter_lines = re.findall(
            r'(?:^|<br\s*/>)([^<]*<a[^>]+onclick=["\']yt\.www\.watch\.player\.seekTo[^>]+>(\d{1,2}:\d{1,2}(?::\d{1,2})?)</a>[^>]*)(?=$|<br\s*/>)',
            description)
        if not chapter_lines:
            return None
        chapters = []
        for next_num, (chapter_line, time_point) in enumerate(
                chapter_lines, start=1):
            start_time = parse_duration(time_point)
            if start_time is None:
                continue
            if start_time > duration:
                break
            end_time = (duration if next_num == len(chapter_lines)
                        else parse_duration(chapter_lines[next_num][1]))
            if end_time is None:
                continue
            if end_time > duration:
                end_time = duration
            if start_time > end_time:
                break
            chapter_title = re.sub(
                r'<a[^>]+>[^<]+</a>', '', chapter_line).strip(' \t-')
            chapter_title = re.sub(r'\s+', ' ', chapter_title)
            chapters.append({
                'start_time': start_time,
                'end_time': end_time,
                'title': chapter_title,
            })
        return chapters

    def _extract_chapters(self, webpage, description, video_id, duration):
        return (self._extract_chapters_from_json(webpage, video_id, duration)
                or self._extract_chapters_from_description(description, duration))

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})

        proto = (
            'http' if self._downloader.params.get('prefer_insecure', False)
            else 'https')

        start_time = None
        end_time = None
        parsed_url = compat_urllib_parse_urlparse(url)
        for component in [parsed_url.fragment, parsed_url.query]:
            query = compat_parse_qs(component)
            if start_time is None and 't' in query:
                start_time = parse_duration(query['t'][0])
            if start_time is None and 'start' in query:
                start_time = parse_duration(query['start'][0])
            if end_time is None and 'end' in query:
                end_time = parse_duration(query['end'][0])

        # Extract original video URL from URL with redirection, like age verification, using next_url parameter
        mobj = re.search(self._NEXT_URL_RE, url)
        if mobj:
            url = proto + '://www.youtube.com/' + compat_urllib_parse_unquote(mobj.group(1)).lstrip('/')
        video_id = self.extract_id(url)

        # Get video webpage
        url = proto + '://www.youtube.com/watch?v=%s&gl=US&hl=en&has_verified=1&bpctr=9999999999' % video_id
        video_webpage, urlh = self._download_webpage_handle(url, video_id)

        qs = compat_parse_qs(compat_urllib_parse_urlparse(urlh.geturl()).query)
        video_id = qs.get('v', [None])[0] or video_id

        # Attempt to extract SWF player URL
        mobj = re.search(r'swfConfig.*?"(https?:\\/\\/.*?watch.*?-.*?\.swf)"', video_webpage)
        if mobj is not None:
            player_url = re.sub(r'\\(.)', r'\1', mobj.group(1))
        else:
            player_url = None

        dash_mpds = []

        def add_dash_mpd(video_info):
            dash_mpd = video_info.get('dashmpd')
            if dash_mpd and dash_mpd[0] not in dash_mpds:
                dash_mpds.append(dash_mpd[0])

        def add_dash_mpd_pr(pl_response):
            dash_mpd = url_or_none(try_get(
                pl_response, lambda x: x['streamingData']['dashManifestUrl'],
                compat_str))
            if dash_mpd and dash_mpd not in dash_mpds:
                dash_mpds.append(dash_mpd)

        is_live = None
        view_count = None

        def extract_view_count(v_info):
            return int_or_none(try_get(v_info, lambda x: x['view_count'][0]))

        def extract_player_response(player_response, video_id):
            pl_response = str_or_none(player_response)
            if not pl_response:
                return
            pl_response = self._parse_json(pl_response, video_id, fatal=False)
            if isinstance(pl_response, dict):
                add_dash_mpd_pr(pl_response)
                return pl_response

        def extract_embedded_config(embed_webpage, video_id):
            embedded_config = self._search_regex(
                r'setConfig\(({.*})\);',
                embed_webpage, 'ytInitialData', default=None)
            if embedded_config:
                return embedded_config

        player_response = {}

        # Get video info
        video_info = {}
        embed_webpage = None
        if (self._og_search_property('restrictions:age', video_webpage, default=None) == '18+'
                or re.search(r'player-age-gate-content">', video_webpage) is not None):
            cookie_keys = self._get_cookies('https://www.youtube.com').keys()
            age_gate = True
            # We simulate the access to the video from www.youtube.com/v/{video_id}
            # this can be viewed without login into Youtube
            url = proto + '://www.youtube.com/embed/%s' % video_id
            embed_webpage = self._download_webpage(url, video_id, 'Downloading embed webpage')
            ext = extract_embedded_config(embed_webpage, video_id)
            # playabilityStatus = re.search(r'{\\\"status\\\":\\\"(?P<playabilityStatus>[^\"]+)\\\"', ext)
            playable_in_embed = re.search(r'{\\\"playableInEmbed\\\":(?P<playableinEmbed>[^\,]+)', ext)
            if not playable_in_embed:
                self.to_screen('Could not determine whether playabale in embed for video %s' % video_id)
                playable_in_embed = ''
            else:
                playable_in_embed = playable_in_embed.group('playableinEmbed')
            # check if video is only playable on youtube in other words not playable in embed - if so it requires auth (cookies)
            # if re.search(r'player-unavailable">', embed_webpage) is not None:
            if playable_in_embed == 'false':
                '''
                # TODO apply this patch when Support for Python 2.6(!) and above drops
                if ({'VISITOR_INFO1_LIVE', 'HSID', 'SSID', 'SID'} <= cookie_keys
                        or {'VISITOR_INFO1_LIVE', '__Secure-3PSID', 'LOGIN_INFO'} <= cookie_keys):
                '''
                if (set(('VISITOR_INFO1_LIVE', 'HSID', 'SSID', 'SID')) <= set(cookie_keys)
                        or set(('VISITOR_INFO1_LIVE', '__Secure-3PSID', 'LOGIN_INFO')) <= set(cookie_keys)):
                    age_gate = False
                    # Try looking directly into the video webpage
                    ytplayer_config = self._get_ytplayer_config(video_id, video_webpage)
                    if ytplayer_config:
                        args = ytplayer_config.get("args")
                        if args is not None:
                            if args.get('url_encoded_fmt_stream_map') or args.get('hlsvp'):
                                # Convert to the same format returned by compat_parse_qs
                                video_info = dict((k, [v]) for k, v in args.items())
                                add_dash_mpd(video_info)
                            # Rental video is not rented but preview is available (e.g.
                            # https://www.youtube.com/watch?v=yYr8q0y5Jfg,
                            # https://github.com/ytdl-org/youtube-dl/issues/10532)
                            if not video_info and args.get('ypc_vid'):
                                return self.url_result(
                                    args['ypc_vid'], YoutubeIE.ie_key(), video_id=args['ypc_vid'])
                            if args.get('livestream') == '1' or args.get('live_playback') == 1:
                                is_live = True
                            if not player_response:
                                player_response = extract_player_response(args.get('player_response'), video_id)
                        elif not player_response:
                            player_response = ytplayer_config
                    if not video_info or self._downloader.params.get('youtube_include_dash_manifest', True):
                        add_dash_mpd_pr(player_response)
                else:
                    raise ExtractorError('Video is age restricted and only playable on Youtube. Requires cookies!', expected=True)
            else:
                data = compat_urllib_parse_urlencode({
                    'video_id': video_id,
                    'eurl': 'https://youtube.googleapis.com/v/' + video_id,
                    'sts': self._search_regex(
                        r'"sts"\s*:\s*(\d+)', embed_webpage, 'sts', default=''),
                })
                video_info_url = proto + '://www.youtube.com/get_video_info?' + data
                try:
                    video_info_webpage = self._download_webpage(
                        video_info_url, video_id,
                        note='Refetching age-gated info webpage',
                        errnote='unable to download video info webpage')
                except ExtractorError:
                    video_info_webpage = None
                if video_info_webpage:
                    video_info = compat_parse_qs(video_info_webpage)
                    pl_response = video_info.get('player_response', [None])[0]
                    player_response = extract_player_response(pl_response, video_id)
                    add_dash_mpd(video_info)
                    view_count = extract_view_count(video_info)
        else:
            age_gate = False
            # Try looking directly into the video webpage
            ytplayer_config = self._get_ytplayer_config(video_id, video_webpage)
            args = ytplayer_config.get("args")
            if args is not None:
                if args.get('url_encoded_fmt_stream_map') or args.get('hlsvp'):
                    # Convert to the same format returned by compat_parse_qs
                    video_info = dict((k, [v]) for k, v in args.items())
                    add_dash_mpd(video_info)
                # Rental video is not rented but preview is available (e.g.
                # https://www.youtube.com/watch?v=yYr8q0y5Jfg,
                # https://github.com/ytdl-org/youtube-dl/issues/10532)
                if not video_info and args.get('ypc_vid'):
                    return self.url_result(
                        args['ypc_vid'], YoutubeIE.ie_key(), video_id=args['ypc_vid'])
                if args.get('livestream') == '1' or args.get('live_playback') == 1:
                    is_live = True
                if not player_response:
                    player_response = extract_player_response(args.get('player_response'), video_id)
            elif not player_response:
                player_response = ytplayer_config
            if not video_info or self._downloader.params.get('youtube_include_dash_manifest', True):
                add_dash_mpd_pr(player_response)

        def extract_unavailable_message():
            messages = []
            for tag, kind in (('h1', 'message'), ('div', 'submessage')):
                msg = self._html_search_regex(
                    r'(?s)<{tag}[^>]+id=["\']unavailable-{kind}["\'][^>]*>(.+?)</{tag}>'.format(tag=tag, kind=kind),
                    video_webpage, 'unavailable %s' % kind, default=None)
                if msg:
                    messages.append(msg)
            if messages:
                return '\n'.join(messages)

        if not video_info and not player_response:
            unavailable_message = extract_unavailable_message()
            if not unavailable_message:
                unavailable_message = 'Unable to extract video data'
            raise ExtractorError(
                'YouTube said: %s' % unavailable_message, expected=True, video_id=video_id)

        if not isinstance(video_info, dict):
            video_info = {}

        video_details = try_get(
            player_response, lambda x: x['videoDetails'], dict) or {}

        microformat = try_get(
            player_response, lambda x: x['microformat']['playerMicroformatRenderer'], dict) or {}

        video_title = video_info.get('title', [None])[0] or video_details.get('title')
        if not video_title:
            self._downloader.report_warning('Unable to extract video title')
            video_title = '_'

        description_original = video_description = get_element_by_id("eow-description", video_webpage)
        if video_description:

            def replace_url(m):
                redir_url = compat_urlparse.urljoin(url, m.group(1))
                parsed_redir_url = compat_urllib_parse_urlparse(redir_url)
                if re.search(r'^(?:www\.)?(?:youtube(?:-nocookie)?\.com|youtu\.be)$', parsed_redir_url.netloc) and parsed_redir_url.path == '/redirect':
                    qs = compat_parse_qs(parsed_redir_url.query)
                    q = qs.get('q')
                    if q and q[0]:
                        return q[0]
                return redir_url

            description_original = video_description = re.sub(r'''(?x)
                <a\s+
                    (?:[a-zA-Z-]+="[^"]*"\s+)*?
                    (?:title|href)="([^"]+)"\s+
                    (?:[a-zA-Z-]+="[^"]*"\s+)*?
                    class="[^"]*"[^>]*>
                [^<]+\.{3}\s*
                </a>
            ''', replace_url, video_description)
            video_description = clean_html(video_description)
        else:
            video_description = video_details.get('shortDescription')
            if video_description is None:
                video_description = self._html_search_meta('description', video_webpage)

        if not smuggled_data.get('force_singlefeed', False):
            if not self._downloader.params.get('noplaylist'):
                multifeed_metadata_list = try_get(
                    player_response,
                    lambda x: x['multicamera']['playerLegacyMulticameraRenderer']['metadataList'],
                    compat_str) or try_get(
                    video_info, lambda x: x['multifeed_metadata_list'][0], compat_str)
                if multifeed_metadata_list:
                    entries = []
                    feed_ids = []
                    for feed in multifeed_metadata_list.split(','):
                        # Unquote should take place before split on comma (,) since textual
                        # fields may contain comma as well (see
                        # https://github.com/ytdl-org/youtube-dl/issues/8536)
                        feed_data = compat_parse_qs(compat_urllib_parse_unquote_plus(feed))

                        def feed_entry(name):
                            return try_get(feed_data, lambda x: x[name][0], compat_str)

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
                                '%s://www.youtube.com/watch?v=%s' % (proto, feed_data['id'][0]),
                                {'force_singlefeed': True}),
                            'title': title,
                        })
                        feed_ids.append(feed_id)
                    self.to_screen(
                        'Downloading multifeed video (%s) - add --no-playlist to just download video %s'
                        % (', '.join(feed_ids), video_id))
                    return self.playlist_result(entries, video_id, video_title, video_description)
            else:
                self.to_screen('Downloading just video %s because of --no-playlist' % video_id)

        if view_count is None:
            view_count = extract_view_count(video_info)
        if view_count is None and video_details:
            view_count = int_or_none(video_details.get('viewCount'))
        if view_count is None and microformat:
            view_count = int_or_none(microformat.get('viewCount'))

        if is_live is None:
            is_live = bool_or_none(video_details.get('isLive'))

        has_live_chat_replay = False
        if not is_live:
            yt_initial_data = self._get_yt_initial_data(video_id, video_webpage)
            try:
                yt_initial_data['contents']['twoColumnWatchNextResults']['conversationBar']['liveChatRenderer']['continuations'][0]['reloadContinuationData']['continuation']
                has_live_chat_replay = True
            except (KeyError, IndexError, TypeError):
                pass

        # Check for "rental" videos
        if 'ypc_video_rental_bar_text' in video_info and 'author' not in video_info:
            raise ExtractorError('"rental" videos not supported. See https://github.com/ytdl-org/youtube-dl/issues/359 for more information.', expected=True)

        def _extract_filesize(media_url):
            return int_or_none(self._search_regex(
                r'\bclen[=/](\d+)', media_url, 'filesize', default=None))

        streaming_formats = try_get(player_response, lambda x: x['streamingData']['formats'], list) or []
        streaming_formats.extend(try_get(player_response, lambda x: x['streamingData']['adaptiveFormats'], list) or [])

        if 'conn' in video_info and video_info['conn'][0].startswith('rtmp'):
            self.report_rtmp_download()
            formats = [{
                'format_id': '_rtmp',
                'protocol': 'rtmp',
                'url': video_info['conn'][0],
                'player_url': player_url,
            }]
        elif not is_live and (streaming_formats or len(video_info.get('url_encoded_fmt_stream_map', [''])[0]) >= 1 or len(video_info.get('adaptive_fmts', [''])[0]) >= 1):
            encoded_url_map = video_info.get('url_encoded_fmt_stream_map', [''])[0] + ',' + video_info.get('adaptive_fmts', [''])[0]
            if 'rtmpe%3Dyes' in encoded_url_map:
                raise ExtractorError('rtmpe downloads are not supported, see https://github.com/ytdl-org/youtube-dl/issues/343 for more information.', expected=True)
            formats = []
            formats_spec = {}
            fmt_list = video_info.get('fmt_list', [''])[0]
            if fmt_list:
                for fmt in fmt_list.split(','):
                    spec = fmt.split('/')
                    if len(spec) > 1:
                        width_height = spec[1].split('x')
                        if len(width_height) == 2:
                            formats_spec[spec[0]] = {
                                'resolution': spec[1],
                                'width': int_or_none(width_height[0]),
                                'height': int_or_none(width_height[1]),
                            }
            for fmt in streaming_formats:
                itag = str_or_none(fmt.get('itag'))
                if not itag:
                    continue
                quality = fmt.get('quality')
                quality_label = fmt.get('qualityLabel') or quality
                formats_spec[itag] = {
                    'asr': int_or_none(fmt.get('audioSampleRate')),
                    'filesize': int_or_none(fmt.get('contentLength')),
                    'format_note': quality_label,
                    'fps': int_or_none(fmt.get('fps')),
                    'height': int_or_none(fmt.get('height')),
                    # bitrate for itag 43 is always 2147483647
                    'tbr': float_or_none(fmt.get('averageBitrate') or fmt.get('bitrate'), 1000) if itag != '43' else None,
                    'width': int_or_none(fmt.get('width')),
                }

            for fmt in streaming_formats:
                if fmt.get('drmFamilies') or fmt.get('drm_families'):
                    continue
                url = url_or_none(fmt.get('url'))

                if not url:
                    cipher = fmt.get('cipher') or fmt.get('signatureCipher')
                    if not cipher:
                        continue
                    url_data = compat_parse_qs(cipher)
                    url = url_or_none(try_get(url_data, lambda x: x['url'][0], compat_str))
                    if not url:
                        continue
                else:
                    cipher = None
                    url_data = compat_parse_qs(compat_urllib_parse_urlparse(url).query)

                stream_type = int_or_none(try_get(url_data, lambda x: x['stream_type'][0]))
                # Unsupported FORMAT_STREAM_TYPE_OTF
                if stream_type == 3:
                    continue

                format_id = fmt.get('itag') or url_data['itag'][0]
                if not format_id:
                    continue
                format_id = compat_str(format_id)

                if cipher:
                    if 's' in url_data or self._downloader.params.get('youtube_include_dash_manifest', True):
                        ASSETS_RE = r'(?:"assets":.+?"js":\s*("[^"]+"))|(?:"jsUrl":\s*("[^"]+"))'
                        jsplayer_url_json = self._search_regex(
                            ASSETS_RE,
                            embed_webpage if age_gate else video_webpage,
                            'JS player URL (1)', default=None)
                        if not jsplayer_url_json and not age_gate:
                            # We need the embed website after all
                            if embed_webpage is None:
                                embed_url = proto + '://www.youtube.com/embed/%s' % video_id
                                embed_webpage = self._download_webpage(
                                    embed_url, video_id, 'Downloading embed webpage')
                            jsplayer_url_json = self._search_regex(
                                ASSETS_RE, embed_webpage, 'JS player URL')

                        player_url = json.loads(jsplayer_url_json)
                        if player_url is None:
                            player_url_json = self._search_regex(
                                r'ytplayer\.config.*?"url"\s*:\s*("[^"]+")',
                                video_webpage, 'age gate player URL')
                            player_url = json.loads(player_url_json)

                    if 'sig' in url_data:
                        url += '&signature=' + url_data['sig'][0]
                    elif 's' in url_data:
                        encrypted_sig = url_data['s'][0]

                        if self._downloader.params.get('verbose'):
                            if player_url is None:
                                player_desc = 'unknown'
                            else:
                                player_type, player_version = self._extract_player_info(player_url)
                                player_desc = '%s player %s' % ('flash' if player_type == 'swf' else 'html5', player_version)
                            parts_sizes = self._signature_cache_id(encrypted_sig)
                            self.to_screen('{%s} signature length %s, %s' %
                                           (format_id, parts_sizes, player_desc))

                        signature = self._decrypt_signature(
                            encrypted_sig, video_id, player_url, age_gate)
                        sp = try_get(url_data, lambda x: x['sp'][0], compat_str) or 'signature'
                        url += '&%s=%s' % (sp, signature)
                if 'ratebypass' not in url:
                    url += '&ratebypass=yes'

                dct = {
                    'format_id': format_id,
                    'url': url,
                    'player_url': player_url,
                }
                if format_id in self._formats:
                    dct.update(self._formats[format_id])
                if format_id in formats_spec:
                    dct.update(formats_spec[format_id])

                # Some itags are not included in DASH manifest thus corresponding formats will
                # lack metadata (see https://github.com/ytdl-org/youtube-dl/pull/5993).
                # Trying to extract metadata from url_encoded_fmt_stream_map entry.
                mobj = re.search(r'^(?P<width>\d+)[xX](?P<height>\d+)$', url_data.get('size', [''])[0])
                width, height = (int(mobj.group('width')), int(mobj.group('height'))) if mobj else (None, None)

                if width is None:
                    width = int_or_none(fmt.get('width'))
                if height is None:
                    height = int_or_none(fmt.get('height'))

                filesize = int_or_none(url_data.get(
                    'clen', [None])[0]) or _extract_filesize(url)

                quality = url_data.get('quality', [None])[0] or fmt.get('quality')
                quality_label = url_data.get('quality_label', [None])[0] or fmt.get('qualityLabel')

                tbr = (float_or_none(url_data.get('bitrate', [None])[0], 1000)
                       or float_or_none(fmt.get('bitrate'), 1000)) if format_id != '43' else None
                fps = int_or_none(url_data.get('fps', [None])[0]) or int_or_none(fmt.get('fps'))

                more_fields = {
                    'filesize': filesize,
                    'tbr': tbr,
                    'width': width,
                    'height': height,
                    'fps': fps,
                    'format_note': quality_label or quality,
                }
                for key, value in more_fields.items():
                    if value:
                        dct[key] = value
                type_ = url_data.get('type', [None])[0] or fmt.get('mimeType')
                if type_:
                    type_split = type_.split(';')
                    kind_ext = type_split[0].split('/')
                    if len(kind_ext) == 2:
                        kind, _ = kind_ext
                        dct['ext'] = mimetype2ext(type_split[0])
                        if kind in ('audio', 'video'):
                            codecs = None
                            for mobj in re.finditer(
                                    r'(?P<key>[a-zA-Z_-]+)=(?P<quote>["\']?)(?P<val>.+?)(?P=quote)(?:;|$)', type_):
                                if mobj.group('key') == 'codecs':
                                    codecs = mobj.group('val')
                                    break
                            if codecs:
                                dct.update(parse_codecs(codecs))
                if dct.get('acodec') == 'none' or dct.get('vcodec') == 'none':
                    dct['downloader_options'] = {
                        # Youtube throttles chunks >~10M
                        'http_chunk_size': 10485760,
                    }
                formats.append(dct)
        else:
            manifest_url = (
                url_or_none(try_get(
                    player_response,
                    lambda x: x['streamingData']['hlsManifestUrl'],
                    compat_str))
                or url_or_none(try_get(
                    video_info, lambda x: x['hlsvp'][0], compat_str)))
            if manifest_url:
                formats = []
                m3u8_formats = self._extract_m3u8_formats(
                    manifest_url, video_id, 'mp4', fatal=False)
                for a_format in m3u8_formats:
                    itag = self._search_regex(
                        r'/itag/(\d+)/', a_format['url'], 'itag', default=None)
                    if itag:
                        a_format['format_id'] = itag
                        if itag in self._formats:
                            dct = self._formats[itag].copy()
                            dct.update(a_format)
                            a_format = dct
                    a_format['player_url'] = player_url
                    # Accept-Encoding header causes failures in live streams on Youtube and Youtube Gaming
                    a_format.setdefault('http_headers', {})['Youtubedl-no-compression'] = 'True'
                    if self._downloader.params.get('youtube_include_hls_manifest', True):
                        formats.append(a_format)
            else:
                error_message = extract_unavailable_message()
                if not error_message:
                    error_message = clean_html(try_get(
                        player_response, lambda x: x['playabilityStatus']['reason'],
                        compat_str))
                if not error_message:
                    error_message = clean_html(
                        try_get(video_info, lambda x: x['reason'][0], compat_str))
                if error_message:
                    raise ExtractorError(error_message, expected=True)
                raise ExtractorError('no conn, hlsvp, hlsManifestUrl or url_encoded_fmt_stream_map information found in video info')

        # uploader
        video_uploader = try_get(
            video_info, lambda x: x['author'][0],
            compat_str) or str_or_none(video_details.get('author'))
        if video_uploader:
            video_uploader = compat_urllib_parse_unquote_plus(video_uploader)
        else:
            self._downloader.report_warning('unable to extract uploader name')

        # uploader_id
        video_uploader_id = None
        video_uploader_url = None
        mobj = re.search(
            r'<link itemprop="url" href="(?P<uploader_url>https?://www\.youtube\.com/(?:user|channel)/(?P<uploader_id>[^"]+))">',
            video_webpage)
        if mobj is not None:
            video_uploader_id = mobj.group('uploader_id')
            video_uploader_url = mobj.group('uploader_url')
        else:
            owner_profile_url = url_or_none(microformat.get('ownerProfileUrl'))
            if owner_profile_url:
                video_uploader_id = self._search_regex(
                    r'(?:user|channel)/([^/]+)', owner_profile_url, 'uploader id',
                    default=None)
                video_uploader_url = owner_profile_url

        channel_id = (
            str_or_none(video_details.get('channelId'))
            or self._html_search_meta(
                'channelId', video_webpage, 'channel id', default=None)
            or self._search_regex(
                r'data-channel-external-id=(["\'])(?P<id>(?:(?!\1).)+)\1',
                video_webpage, 'channel id', default=None, group='id'))
        channel_url = 'http://www.youtube.com/channel/%s' % channel_id if channel_id else None

        thumbnails = []
        thumbnails_list = try_get(
            video_details, lambda x: x['thumbnail']['thumbnails'], list) or []
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

        if not thumbnails:
            video_thumbnail = None
            # We try first to get a high quality image:
            m_thumb = re.search(r'<span itemprop="thumbnail".*?href="(.*?)">',
                                video_webpage, re.DOTALL)
            if m_thumb is not None:
                video_thumbnail = m_thumb.group(1)
            thumbnail_url = try_get(video_info, lambda x: x['thumbnail_url'][0], compat_str)
            if thumbnail_url:
                video_thumbnail = compat_urllib_parse_unquote_plus(thumbnail_url)
            if video_thumbnail:
                thumbnails.append({'url': video_thumbnail})

        # upload date
        upload_date = self._html_search_meta(
            'datePublished', video_webpage, 'upload date', default=None)
        if not upload_date:
            upload_date = self._search_regex(
                [r'(?s)id="eow-date.*?>(.*?)</span>',
                 r'(?:id="watch-uploader-info".*?>.*?|["\']simpleText["\']\s*:\s*["\'])(?:Published|Uploaded|Streamed live|Started) on (.+?)[<"\']'],
                video_webpage, 'upload date', default=None)
        if not upload_date:
            upload_date = microformat.get('publishDate') or microformat.get('uploadDate')
        upload_date = unified_strdate(upload_date)

        video_license = self._html_search_regex(
            r'<h4[^>]+class="title"[^>]*>\s*License\s*</h4>\s*<ul[^>]*>\s*<li>(.+?)</li',
            video_webpage, 'license', default=None)

        m_music = re.search(
            r'''(?x)
                <h4[^>]+class="title"[^>]*>\s*Music\s*</h4>\s*
                <ul[^>]*>\s*
                <li>(?P<title>.+?)
                by (?P<creator>.+?)
                (?:
                    \(.+?\)|
                    <a[^>]*
                        (?:
                            \bhref=["\']/red[^>]*>|             # drop possible
                            >\s*Listen ad-free with YouTube Red # YouTube Red ad
                        )
                    .*?
                )?</li
            ''',
            video_webpage)
        if m_music:
            video_alt_title = remove_quotes(unescapeHTML(m_music.group('title')))
            video_creator = clean_html(m_music.group('creator'))
        else:
            video_alt_title = video_creator = None

        def extract_meta(field):
            return self._html_search_regex(
                r'<h4[^>]+class="title"[^>]*>\s*%s\s*</h4>\s*<ul[^>]*>\s*<li>(.+?)</li>\s*' % field,
                video_webpage, field, default=None)

        track = extract_meta('Song')
        artist = extract_meta('Artist')
        album = extract_meta('Album')

        # Youtube Music Auto-generated description
        release_date = release_year = None
        if video_description:
            mobj = re.search(r'(?s)Provided to YouTube by [^\n]+\n+(?P<track>[^·]+)·(?P<artist>[^\n]+)\n+(?P<album>[^\n]+)(?:.+?℗\s*(?P<release_year>\d{4})(?!\d))?(?:.+?Released on\s*:\s*(?P<release_date>\d{4}-\d{2}-\d{2}))?(.+?\nArtist\s*:\s*(?P<clean_artist>[^\n]+))?', video_description)
            if mobj:
                if not track:
                    track = mobj.group('track').strip()
                if not artist:
                    artist = mobj.group('clean_artist') or ', '.join(a.strip() for a in mobj.group('artist').split('·'))
                if not album:
                    album = mobj.group('album'.strip())
                release_year = mobj.group('release_year')
                release_date = mobj.group('release_date')
                if release_date:
                    release_date = release_date.replace('-', '')
                    if not release_year:
                        release_year = int(release_date[:4])
                if release_year:
                    release_year = int(release_year)

        yt_initial = self._get_yt_initial_data(video_id, video_webpage)
        if yt_initial:
            music_metadata = self._get_music_metadata_from_yt_initial(yt_initial)
            if len(music_metadata):
                album = music_metadata[0].get('album')
                artist = music_metadata[0].get('artist')
                track = music_metadata[0].get('track')

        m_episode = re.search(
            r'<div[^>]+id="watch7-headline"[^>]*>\s*<span[^>]*>.*?>(?P<series>[^<]+)</a></b>\s*S(?P<season>\d+)\s*•\s*E(?P<episode>\d+)</span>',
            video_webpage)
        if m_episode:
            series = unescapeHTML(m_episode.group('series'))
            season_number = int(m_episode.group('season'))
            episode_number = int(m_episode.group('episode'))
        else:
            series = season_number = episode_number = None

        m_cat_container = self._search_regex(
            r'(?s)<h4[^>]*>\s*Category\s*</h4>\s*<ul[^>]*>(.*?)</ul>',
            video_webpage, 'categories', default=None)
        category = None
        if m_cat_container:
            category = self._html_search_regex(
                r'(?s)<a[^<]+>(.*?)</a>', m_cat_container, 'category',
                default=None)
        if not category:
            category = try_get(
                microformat, lambda x: x['category'], compat_str)
        video_categories = None if category is None else [category]

        video_tags = [
            unescapeHTML(m.group('content'))
            for m in re.finditer(self._meta_regex('og:video:tag'), video_webpage)]
        if not video_tags:
            video_tags = try_get(video_details, lambda x: x['keywords'], list)

        def _extract_count(count_name):
            return str_to_int(self._search_regex(
                r'"accessibilityData":\{"label":"([\d,\w]+) %ss"\}'
                % re.escape(count_name),
                video_webpage, count_name, default=None))

        like_count = _extract_count('like')
        dislike_count = _extract_count('dislike')

        if view_count is None:
            view_count = str_to_int(self._search_regex(
                r'<[^>]+class=["\']watch-view-count[^>]+>\s*([\d,\s]+)', video_webpage,
                'view count', default=None))

        average_rating = (
            float_or_none(video_details.get('averageRating'))
            or try_get(video_info, lambda x: float_or_none(x['avg_rating'][0])))

        # subtitles
        video_subtitles = self.extract_subtitles(
            video_id, video_webpage, has_live_chat_replay)
        automatic_captions = self.extract_automatic_captions(video_id, video_webpage)

        video_duration = try_get(
            video_info, lambda x: int_or_none(x['length_seconds'][0]))
        if not video_duration:
            video_duration = int_or_none(video_details.get('lengthSeconds'))
        if not video_duration:
            video_duration = parse_duration(self._html_search_meta(
                'duration', video_webpage, 'video duration'))

        # Get Subscriber Count of channel
        subscriber_count = parse_count(self._search_regex(
            r'"text":"([\d\.]+\w?) subscribers"',
            video_webpage,
            'subscriber count',
            default=None
        ))

        # annotations
        video_annotations = None
        if self._downloader.params.get('writeannotations', False):
            xsrf_token = self._search_regex(
                r'([\'"])XSRF_TOKEN\1\s*:\s*([\'"])(?P<xsrf_token>[A-Za-z0-9+/=]+)\2',
                video_webpage, 'xsrf token', group='xsrf_token', fatal=False)
            invideo_url = try_get(
                player_response, lambda x: x['annotations'][0]['playerAnnotationsUrlsRenderer']['invideoUrl'], compat_str)
            if xsrf_token and invideo_url:
                xsrf_field_name = self._search_regex(
                    r'([\'"])XSRF_FIELD_NAME\1\s*:\s*([\'"])(?P<xsrf_field_name>\w+)\2',
                    video_webpage, 'xsrf field name',
                    group='xsrf_field_name', default='session_token')
                video_annotations = self._download_webpage(
                    self._proto_relative_url(invideo_url),
                    video_id, note='Downloading annotations',
                    errnote='Unable to download video annotations', fatal=False,
                    data=urlencode_postdata({xsrf_field_name: xsrf_token}))

        chapters = self._extract_chapters(video_webpage, description_original, video_id, video_duration)

        # Look for the DASH manifest
        if self._downloader.params.get('youtube_include_dash_manifest', True):
            dash_mpd_fatal = True
            for mpd_url in dash_mpds:
                dash_formats = {}
                try:
                    def decrypt_sig(mobj):
                        s = mobj.group(1)
                        dec_s = self._decrypt_signature(s, video_id, player_url, age_gate)
                        return '/signature/%s' % dec_s

                    mpd_url = re.sub(r'/s/([a-fA-F0-9\.]+)', decrypt_sig, mpd_url)

                    for df in self._extract_mpd_formats(
                            mpd_url, video_id, fatal=dash_mpd_fatal,
                            formats_dict=self._formats):
                        if not df.get('filesize'):
                            df['filesize'] = _extract_filesize(df['url'])
                        # Do not overwrite DASH format found in some previous DASH manifest
                        if df['format_id'] not in dash_formats:
                            dash_formats[df['format_id']] = df
                        # Additional DASH manifests may end up in HTTP Error 403 therefore
                        # allow them to fail without bug report message if we already have
                        # some DASH manifest succeeded. This is temporary workaround to reduce
                        # burst of bug reports until we figure out the reason and whether it
                        # can be fixed at all.
                        dash_mpd_fatal = False
                except (ExtractorError, KeyError) as e:
                    self.report_warning(
                        'Skipping DASH manifest: %r' % e, video_id)
                if dash_formats:
                    # Remove the formats we found through non-DASH, they
                    # contain less info and it can be wrong, because we use
                    # fixed values (for example the resolution). See
                    # https://github.com/ytdl-org/youtube-dl/issues/5774 for an
                    # example.
                    formats = [f for f in formats if f['format_id'] not in dash_formats.keys()]
                    formats.extend(dash_formats.values())

        # Check for malformed aspect ratio
        stretched_m = re.search(
            r'<meta\s+property="og:video:tag".*?content="yt:stretch=(?P<w>[0-9]+):(?P<h>[0-9]+)">',
            video_webpage)
        if stretched_m:
            w = float(stretched_m.group('w'))
            h = float(stretched_m.group('h'))
            # yt:stretch may hold invalid ratio data (e.g. for Q39EVAstoRM ratio is 17:0).
            # We will only process correct ratios.
            if w > 0 and h > 0:
                ratio = w / h
                for f in formats:
                    if f.get('vcodec') != 'none':
                        f['stretched_ratio'] = ratio

        if not formats:
            if 'reason' in video_info:
                if 'The uploader has not made this video available in your country.' in video_info['reason']:
                    regions_allowed = self._html_search_meta(
                        'regionsAllowed', video_webpage, default=None)
                    countries = regions_allowed.split(',') if regions_allowed else None
                    self.raise_geo_restricted(
                        msg=video_info['reason'][0], countries=countries)
                reason = video_info['reason'][0]
                if 'Invalid parameters' in reason:
                    unavailable_message = extract_unavailable_message()
                    if unavailable_message:
                        reason = unavailable_message
                raise ExtractorError(
                    'YouTube said: %s' % reason,
                    expected=True, video_id=video_id)
            if video_info.get('license_info') or try_get(player_response, lambda x: x['streamingData']['licenseInfos']):
                raise ExtractorError('This video is DRM protected.', expected=True)

        self._sort_formats(formats)

        self.mark_watched(video_id, video_info, player_response)

        return {
            'id': video_id,
            'uploader': video_uploader,
            'uploader_id': video_uploader_id,
            'uploader_url': video_uploader_url,
            'channel_id': channel_id,
            'channel_url': channel_url,
            'upload_date': upload_date,
            'license': video_license,
            'creator': video_creator or artist,
            'title': video_title,
            'alt_title': video_alt_title or track,
            'thumbnails': thumbnails,
            'description': video_description,
            'categories': video_categories,
            'tags': video_tags,
            'subtitles': video_subtitles,
            'automatic_captions': automatic_captions,
            'duration': video_duration,
            'age_limit': 18 if age_gate else 0,
            'annotations': video_annotations,
            'chapters': chapters,
            'webpage_url': proto + '://www.youtube.com/watch?v=%s' % video_id,
            'view_count': view_count,
            'like_count': like_count,
            'dislike_count': dislike_count,
            'average_rating': average_rating,
            'formats': formats,
            'is_live': is_live,
            'start_time': start_time,
            'end_time': end_time,
            'series': series,
            'season_number': season_number,
            'episode_number': episode_number,
            'track': track,
            'artist': artist,
            'album': album,
            'release_date': release_date,
            'release_year': release_year,
            'subscriber_count': subscriber_count,
        }


class YoutubePlaylistIE(YoutubePlaylistBaseInfoExtractor):
    IE_DESC = 'YouTube.com playlists'
    _VALID_URL = r"""(?x)(?:
                        (?:https?://)?
                        (?:\w+\.)?
                        (?:
                            (?:
                                youtube(?:kids)?\.com|
                                invidio\.us
                            )
                            /
                            (?:
                               (?:course|view_play_list|my_playlists|artist|playlist|watch|embed/(?:videoseries|[0-9A-Za-z_-]{11}))
                               \? (?:.*?[&;])*? (?:p|a|list)=
                            |  p/
                            )|
                            youtu\.be/[0-9A-Za-z_-]{11}\?.*?\blist=
                        )
                        (
                            (?:PL|LL|EC|UU|FL|RD|UL|TL|PU|OLAK5uy_)?[0-9A-Za-z-_]{10,}
                            # Top tracks, they can also include dots
                            |(?:MC)[\w\.]*
                        )
                        .*
                     |
                        (%(playlist_id)s)
                     )""" % {'playlist_id': YoutubeBaseInfoExtractor._PLAYLIST_ID_RE}
    _TEMPLATE_URL = 'https://www.youtube.com/playlist?list=%s'
    _VIDEO_RE_TPL = r'href="\s*/watch\?v=%s(?:&amp;(?:[^"]*?index=(?P<index>\d+))?(?:[^>]+>(?P<title>[^<]+))?)?'
    _VIDEO_RE = _VIDEO_RE_TPL % r'(?P<id>[0-9A-Za-z_-]{11})'
    IE_NAME = 'youtube:playlist'
    _TESTS = [{
        'url': 'https://www.youtube.com/playlist?list=PL4lCao7KL_QFVb7Iudeipvc2BCavECqzc',
        'info_dict': {
            'uploader_id': 'UCmlqkdCBesrv2Lak1mF_MxA',
            'uploader': 'Sergey M.',
            'id': 'PL4lCao7KL_QFVb7Iudeipvc2BCavECqzc',
            'title': 'youtube-dl public playlist',
        },
        'playlist_count': 1,
    }, {
        'url': 'https://www.youtube.com/playlist?list=PL4lCao7KL_QFodcLWhDpGCYnngnHtQ-Xf',
        'info_dict': {
            'uploader_id': 'UCmlqkdCBesrv2Lak1mF_MxA',
            'uploader': 'Sergey M.',
            'id': 'PL4lCao7KL_QFodcLWhDpGCYnngnHtQ-Xf',
            'title': 'youtube-dl empty playlist',
        },
        'playlist_count': 0,
    }, {
        'note': 'Playlist with deleted videos (#651). As a bonus, the video #51 is also twice in this list.',
        'url': 'https://www.youtube.com/playlist?list=PLwP_SiAcdui0KVebT0mU9Apz359a4ubsC',
        'info_dict': {
            'title': '29C3: Not my department',
            'id': 'PLwP_SiAcdui0KVebT0mU9Apz359a4ubsC',
            'uploader': 'Christiaan008',
            'uploader_id': 'ChRiStIaAn008',
        },
        'playlist_count': 96,
    }, {
        'note': 'issue #673',
        'url': 'PLBB231211A4F62143',
        'info_dict': {
            'title': '[OLD]Team Fortress 2 (Class-based LP)',
            'id': 'PLBB231211A4F62143',
            'uploader': 'Wickydoo',
            'uploader_id': 'Wickydoo',
        },
        'playlist_mincount': 26,
    }, {
        'note': 'Large playlist',
        'url': 'https://www.youtube.com/playlist?list=UUBABnxM4Ar9ten8Mdjj1j0Q',
        'info_dict': {
            'title': 'Uploads from Cauchemar',
            'id': 'UUBABnxM4Ar9ten8Mdjj1j0Q',
            'uploader': 'Cauchemar',
            'uploader_id': 'Cauchemar89',
        },
        'playlist_mincount': 799,
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
        'playlist_mincount': 485,
        'info_dict': {
            'title': '2018 Chinese New Singles (11/6 updated)',
            'id': 'PLsyOSbh5bs16vubvKePAQ1x3PhKavfBIl',
            'uploader': 'LBK',
            'uploader_id': 'sdragonfang',
        }
    }, {
        'note': 'Embedded SWF player',
        'url': 'https://www.youtube.com/p/YN5VISEtHet5D4NEvfTd0zcgFk84NqFZ?hl=en_US&fs=1&rel=0',
        'playlist_count': 4,
        'info_dict': {
            'title': 'JODA7',
            'id': 'YN5VISEtHet5D4NEvfTd0zcgFk84NqFZ',
        },
        'skip': 'This playlist does not exist',
    }, {
        'note': 'Buggy playlist: the webpage has a "Load more" button but it doesn\'t have more videos',
        'url': 'https://www.youtube.com/playlist?list=UUXw-G3eDE9trcvY2sBMM_aA',
        'info_dict': {
            'title': 'Uploads from Interstellar Movie',
            'id': 'UUXw-G3eDE9trcvY2sBMM_aA',
            'uploader': 'Interstellar Movie',
            'uploader_id': 'InterstellarMovie1',
        },
        'playlist_mincount': 21,
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
        # https://github.com/ytdl-org/youtube-dl/issues/21844
        'url': 'https://www.youtube.com/playlist?list=PLzH6n4zXuckpfMu_4Ff8E7Z1behQks5ba',
        'info_dict': {
            'title': 'Data Analysis with Dr Mike Pound',
            'id': 'PLzH6n4zXuckpfMu_4Ff8E7Z1behQks5ba',
            'uploader_id': 'Computerphile',
            'uploader': 'Computerphile',
        },
        'playlist_mincount': 11,
    }, {
        'url': 'https://youtu.be/uWyaPkt-VOI?list=PL9D9FC436B881BA21',
        'only_matching': True,
    }, {
        'url': 'TLGGrESM50VT6acwMjAyMjAxNw',
        'only_matching': True,
    }, {
        # music album playlist
        'url': 'OLAK5uy_m4xAFdmMC5rX3Ji3g93pQe3hqLZw_9LhM',
        'only_matching': True,
    }, {
        'url': 'https://invidio.us/playlist?list=PLDIoUOhQQPlXr63I_vwF9GD8sAKh77dWU',
        'only_matching': True,
    }, {
        'url': 'https://www.youtubekids.com/watch?v=Agk7R8I8o5U&list=PUZ6jURNr1WQZCNHF0ao-c0g',
        'only_matching': True,
    }]

    def _real_initialize(self):
        self._login()

    def extract_videos_from_page(self, page):
        ids_in_page = []
        titles_in_page = []

        for item in re.findall(
                r'(<[^>]*\bdata-video-id\s*=\s*["\'][0-9A-Za-z_-]{11}[^>]+>)', page):
            attrs = extract_attributes(item)
            video_id = attrs['data-video-id']
            video_title = unescapeHTML(attrs.get('data-title'))
            if video_title:
                video_title = video_title.strip()
            ids_in_page.append(video_id)
            titles_in_page.append(video_title)

        # Fallback with old _VIDEO_RE
        self.extract_videos_from_page_impl(
            self._VIDEO_RE, page, ids_in_page, titles_in_page)

        # Relaxed fallbacks
        self.extract_videos_from_page_impl(
            r'href="\s*/watch\?v\s*=\s*(?P<id>[0-9A-Za-z_-]{11})', page,
            ids_in_page, titles_in_page)
        self.extract_videos_from_page_impl(
            r'data-video-ids\s*=\s*["\'](?P<id>[0-9A-Za-z_-]{11})', page,
            ids_in_page, titles_in_page)

        return zip(ids_in_page, titles_in_page)

    def _extract_mix_ids_from_yt_initial(self, yt_initial):
        ids = []
        playlist_contents = try_get(yt_initial, lambda x: x['contents']['twoColumnWatchNextResults']['playlist']['playlist']['contents'], list)
        if playlist_contents:
            for item in playlist_contents:
                videoId = try_get(item, lambda x: x['playlistPanelVideoRenderer']['videoId'], compat_str)
                if videoId:
                    ids.append(videoId)
        return ids

    def _extract_mix(self, playlist_id):
        # The mixes are generated from a single video
        # the id of the playlist is just 'RD' + video_id
        ids = []
        last_id = playlist_id[-11:]
        for n in itertools.count(1):
            url = 'https://www.youtube.com/watch?v=%s&list=%s' % (last_id, playlist_id)
            webpage = self._download_webpage(
                url, playlist_id, 'Downloading page {0} of Youtube mix'.format(n))
            new_ids = orderedSet(re.findall(
                r'''(?xs)data-video-username=".*?".*?
                           href="/watch\?v=([0-9A-Za-z_-]{11})&amp;[^"]*?list=%s''' % re.escape(playlist_id),
                webpage))

            # if no ids in html of page, try using embedded json
            if (len(new_ids) == 0):
                yt_initial = self._get_yt_initial_data(playlist_id, webpage)
                if yt_initial:
                    new_ids = self._extract_mix_ids_from_yt_initial(yt_initial)

            # Fetch new pages until all the videos are repeated, it seems that
            # there are always 51 unique videos.
            new_ids = [_id for _id in new_ids if _id not in ids]
            if not new_ids:
                break
            ids.extend(new_ids)
            last_id = ids[-1]

        url_results = self._ids_to_results(ids)

        search_title = lambda class_name: get_element_by_attribute('class', class_name, webpage)
        title_span = (
            search_title('playlist-title')
            or search_title('title long-title')
            or search_title('title'))
        title = clean_html(title_span)

        return self.playlist_result(url_results, playlist_id, title)

    def _extract_playlist(self, playlist_id):
        url = self._TEMPLATE_URL % playlist_id
        page = self._download_webpage(url, playlist_id)

        # the yt-alert-message now has tabindex attribute (see https://github.com/ytdl-org/youtube-dl/issues/11604)
        for match in re.findall(r'<div class="yt-alert-message"[^>]*>([^<]+)</div>', page):
            match = match.strip()
            # Check if the playlist exists or is private
            mobj = re.match(r'[^<]*(?:The|This) playlist (?P<reason>does not exist|is private)[^<]*', match)
            if mobj:
                reason = mobj.group('reason')
                message = 'This playlist %s' % reason
                if 'private' in reason:
                    message += ', use --username or --netrc to access it'
                message += '.'
                raise ExtractorError(message, expected=True)
            elif re.match(r'[^<]*Invalid parameters[^<]*', match):
                raise ExtractorError(
                    'Invalid parameters. Maybe URL is incorrect.',
                    expected=True)
            elif re.match(r'[^<]*Choose your language[^<]*', match):
                continue
            else:
                self.report_warning('Youtube gives an alert message: ' + match)

        playlist_title = self._html_search_regex(
            r'(?s)<h1 class="pl-header-title[^"]*"[^>]*>\s*(.*?)\s*</h1>',
            page, 'title', default=None)

        _UPLOADER_BASE = r'class=["\']pl-header-details[^>]+>\s*<li>\s*<a[^>]+\bhref='
        uploader = self._html_search_regex(
            r'%s["\']/(?:user|channel)/[^>]+>([^<]+)' % _UPLOADER_BASE,
            page, 'uploader', default=None)
        mobj = re.search(
            r'%s(["\'])(?P<path>/(?:user|channel)/(?P<uploader_id>.+?))\1' % _UPLOADER_BASE,
            page)
        if mobj:
            uploader_id = mobj.group('uploader_id')
            uploader_url = compat_urlparse.urljoin(url, mobj.group('path'))
        else:
            uploader_id = uploader_url = None

        has_videos = True

        if not playlist_title:
            try:
                # Some playlist URLs don't actually serve a playlist (e.g.
                # https://www.youtube.com/watch?v=FqZTN594JQw&list=PLMYEtVRpaqY00V9W81Cwmzp6N6vZqfUKD4)
                next(self._entries(page, playlist_id))
            except StopIteration:
                has_videos = False

        playlist = self.playlist_result(
            self._entries(page, playlist_id), playlist_id, playlist_title)
        playlist.update({
            'uploader': uploader,
            'uploader_id': uploader_id,
            'uploader_url': uploader_url,
        })

        return has_videos, playlist

    def _check_download_just_video(self, url, playlist_id):
        # Check if it's a video-specific URL
        query_dict = compat_urlparse.parse_qs(compat_urlparse.urlparse(url).query)
        video_id = query_dict.get('v', [None])[0] or self._search_regex(
            r'(?:(?:^|//)youtu\.be/|youtube\.com/embed/(?!videoseries))([0-9A-Za-z_-]{11})', url,
            'video id', default=None)
        if video_id:
            if self._downloader.params.get('noplaylist'):
                self.to_screen('Downloading just video %s because of --no-playlist' % video_id)
                return video_id, self.url_result(video_id, 'Youtube', video_id=video_id)
            else:
                self.to_screen('Downloading playlist %s - add --no-playlist to just download video %s' % (playlist_id, video_id))
                return video_id, None
        return None, None

    def _real_extract(self, url):
        # Extract playlist id
        mobj = re.match(self._VALID_URL, url)
        if mobj is None:
            raise ExtractorError('Invalid URL: %s' % url)
        playlist_id = mobj.group(1) or mobj.group(2)

        video_id, video = self._check_download_just_video(url, playlist_id)
        if video:
            return video

        if playlist_id.startswith(('RD', 'UL', 'PU')):
            # Mixes require a custom extraction process
            return self._extract_mix(playlist_id)

        has_videos, playlist = self._extract_playlist(playlist_id)
        if has_videos or not video_id:
            return playlist

        # Some playlist URLs don't actually serve a playlist (see
        # https://github.com/ytdl-org/youtube-dl/issues/10537).
        # Fallback to plain video extraction if there is a video id
        # along with playlist id.
        return self.url_result(video_id, 'Youtube', video_id=video_id)


class YoutubeChannelIE(YoutubePlaylistBaseInfoExtractor):
    IE_DESC = 'YouTube.com channels'
    _VALID_URL = r'https?://(?:youtu\.be|(?:\w+\.)?youtube(?:-nocookie|kids)?\.com|(?:www\.)?invidio\.us)/channel/(?P<id>[0-9A-Za-z_-]+)'
    _TEMPLATE_URL = 'https://www.youtube.com/channel/%s/videos'
    _VIDEO_RE = r'(?:title="(?P<title>[^"]+)"[^>]+)?href="/watch\?v=(?P<id>[0-9A-Za-z_-]+)&?'
    IE_NAME = 'youtube:channel'
    _TESTS = [{
        'note': 'paginated channel',
        'url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w',
        'playlist_mincount': 91,
        'info_dict': {
            'id': 'UUKfVa3S1e4PHvxWcwyMMg8w',
            'title': 'Uploads from lex will',
            'uploader': 'lex will',
            'uploader_id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
        }
    }, {
        'note': 'Age restricted channel',
        # from https://www.youtube.com/user/DeusExOfficial
        'url': 'https://www.youtube.com/channel/UCs0ifCMCm1icqRbqhUINa0w',
        'playlist_mincount': 64,
        'info_dict': {
            'id': 'UUs0ifCMCm1icqRbqhUINa0w',
            'title': 'Uploads from Deus Ex',
            'uploader': 'Deus Ex',
            'uploader_id': 'DeusExOfficial',
        },
    }, {
        'url': 'https://invidio.us/channel/UC23qupoDRn9YOAVzeoxjOQA',
        'only_matching': True,
    }, {
        'url': 'https://www.youtubekids.com/channel/UCyu8StPfZWapR6rfW_JgqcA',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return (False if YoutubePlaylistsIE.suitable(url) or YoutubeLiveIE.suitable(url)
                else super(YoutubeChannelIE, cls).suitable(url))

    def _build_template_url(self, url, channel_id):
        return self._TEMPLATE_URL % channel_id

    def _real_extract(self, url):
        channel_id = self._match_id(url)

        url = self._build_template_url(url, channel_id)

        # Channel by page listing is restricted to 35 pages of 30 items, i.e. 1050 videos total (see #5778)
        # Workaround by extracting as a playlist if managed to obtain channel playlist URL
        # otherwise fallback on channel by page extraction
        channel_page = self._download_webpage(
            url + '?view=57', channel_id,
            'Downloading channel page', fatal=False)
        if channel_page is False:
            channel_playlist_id = False
        else:
            channel_playlist_id = self._html_search_meta(
                'channelId', channel_page, 'channel id', default=None)
            if not channel_playlist_id:
                channel_url = self._html_search_meta(
                    ('al:ios:url', 'twitter:app:url:iphone', 'twitter:app:url:ipad'),
                    channel_page, 'channel url', default=None)
                if channel_url:
                    channel_playlist_id = self._search_regex(
                        r'vnd\.youtube://user/([0-9A-Za-z_-]+)',
                        channel_url, 'channel id', default=None)
        if channel_playlist_id and channel_playlist_id.startswith('UC'):
            playlist_id = 'UU' + channel_playlist_id[2:]
            return self.url_result(
                compat_urlparse.urljoin(url, '/playlist?list=%s' % playlist_id), 'YoutubePlaylist')

        channel_page = self._download_webpage(url, channel_id, 'Downloading page #1')
        autogenerated = re.search(r'''(?x)
                class="[^"]*?(?:
                    channel-header-autogenerated-label|
                    yt-channel-title-autogenerated
                )[^"]*"''', channel_page) is not None

        if autogenerated:
            # The videos are contained in a single page
            # the ajax pages can't be used, they are empty
            entries = [
                self.url_result(
                    video_id, 'Youtube', video_id=video_id,
                    video_title=video_title)
                for video_id, video_title in self.extract_videos_from_page(channel_page)]
            return self.playlist_result(entries, channel_id)

        try:
            next(self._entries(channel_page, channel_id))
        except StopIteration:
            alert_message = self._html_search_regex(
                r'(?s)<div[^>]+class=(["\']).*?\byt-alert-message\b.*?\1[^>]*>(?P<alert>[^<]+)</div>',
                channel_page, 'alert', default=None, group='alert')
            if alert_message:
                raise ExtractorError('Youtube said: %s' % alert_message, expected=True)

        return self.playlist_result(self._entries(channel_page, channel_id), channel_id)


class YoutubeUserIE(YoutubeChannelIE):
    IE_DESC = 'YouTube.com user videos (URL or "ytuser" keyword)'
    _VALID_URL = r'(?:(?:https?://(?:\w+\.)?youtube\.com/(?:(?P<user>user|c)/)?(?!(?:attribution_link|watch|results|shared)(?:$|[^a-z_A-Z0-9%-])))|ytuser:)(?!feed/)(?P<id>[A-Za-z0-9_%-]+)'
    _TEMPLATE_URL = 'https://www.youtube.com/%s/%s/videos'
    IE_NAME = 'youtube:user'

    _TESTS = [{
        'url': 'https://www.youtube.com/user/TheLinuxFoundation',
        'playlist_mincount': 320,
        'info_dict': {
            'id': 'UUfX55Sx5hEFjoC3cNs6mCUQ',
            'title': 'Uploads from The Linux Foundation',
            'uploader': 'The Linux Foundation',
            'uploader_id': 'TheLinuxFoundation',
        }
    }, {
        # Only available via https://www.youtube.com/c/12minuteathlete/videos
        # but not https://www.youtube.com/user/12minuteathlete/videos
        'url': 'https://www.youtube.com/c/12minuteathlete/videos',
        'playlist_mincount': 249,
        'info_dict': {
            'id': 'UUVjM-zV6_opMDx7WYxnjZiQ',
            'title': 'Uploads from 12 Minute Athlete',
            'uploader': '12 Minute Athlete',
            'uploader_id': 'the12minuteathlete',
        }
    }, {
        'url': 'ytuser:phihag',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/c/gametrailers',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/c/Pawe%C5%82Zadro%C5%BCniak',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/gametrailers',
        'only_matching': True,
    }, {
        # This channel is not available, geo restricted to JP
        'url': 'https://www.youtube.com/user/kananishinoSMEJ/videos',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        # Don't return True if the url can be extracted with other youtube
        # extractor, the regex would is too permissive and it would match.
        other_yt_ies = iter(klass for (name, klass) in globals().items() if name.startswith('Youtube') and name.endswith('IE') and klass is not cls)
        if any(ie.suitable(url) for ie in other_yt_ies):
            return False
        else:
            return super(YoutubeUserIE, cls).suitable(url)

    def _build_template_url(self, url, channel_id):
        mobj = re.match(self._VALID_URL, url)
        return self._TEMPLATE_URL % (mobj.group('user') or 'user', mobj.group('id'))


class YoutubeLiveIE(YoutubeBaseInfoExtractor):
    IE_DESC = 'YouTube.com live streams'
    _VALID_URL = r'(?P<base_url>https?://(?:\w+\.)?youtube\.com/(?:(?:user|channel|c)/)?(?P<id>[^/]+))/live'
    IE_NAME = 'youtube:live'

    _TESTS = [{
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
    }, {
        'url': 'https://www.youtube.com/channel/UC1yBKRuGpC1tSM73A0ZjYjQ/live',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/c/CommanderVideoHq/live',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/TheYoungTurks/live',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        channel_id = mobj.group('id')
        base_url = mobj.group('base_url')
        webpage = self._download_webpage(url, channel_id, fatal=False)
        if webpage:
            page_type = self._og_search_property(
                'type', webpage, 'page type', default='')
            video_id = self._html_search_meta(
                'videoId', webpage, 'video id', default=None)
            if page_type.startswith('video') and video_id and re.match(
                    r'^[0-9A-Za-z_-]{11}$', video_id):
                return self.url_result(video_id, YoutubeIE.ie_key())
        return self.url_result(base_url)


class YoutubePlaylistsIE(YoutubePlaylistsBaseInfoExtractor):
    IE_DESC = 'YouTube.com user/channel playlists'
    _VALID_URL = r'https?://(?:\w+\.)?youtube\.com/(?:user|channel|c)/(?P<id>[^/]+)/playlists'
    IE_NAME = 'youtube:playlists'

    _TESTS = [{
        'url': 'https://www.youtube.com/user/ThirstForScience/playlists',
        'playlist_mincount': 4,
        'info_dict': {
            'id': 'ThirstForScience',
            'title': 'ThirstForScience',
        },
    }, {
        # with "Load more" button
        'url': 'https://www.youtube.com/user/igorkle1/playlists?view=1&sort=dd',
        'playlist_mincount': 70,
        'info_dict': {
            'id': 'igorkle1',
            'title': 'Игорь Клейнер',
        },
    }, {
        'url': 'https://www.youtube.com/channel/UCiU1dHvZObB2iP6xkJ__Icw/playlists',
        'playlist_mincount': 17,
        'info_dict': {
            'id': 'UCiU1dHvZObB2iP6xkJ__Icw',
            'title': 'Chem Player',
        },
        'skip': 'Blocked',
    }, {
        'url': 'https://www.youtube.com/c/ChristophLaimer/playlists',
        'only_matching': True,
    }]


class YoutubeSearchBaseInfoExtractor(YoutubePlaylistBaseInfoExtractor):
    _VIDEO_RE = r'href="\s*/watch\?v=(?P<id>[0-9A-Za-z_-]{11})(?:[^"]*"[^>]+\btitle="(?P<title>[^"]+))?'


class YoutubeSearchIE(SearchInfoExtractor, YoutubeSearchBaseInfoExtractor):
    IE_DESC = 'YouTube.com searches'
    # there doesn't appear to be a real limit, for example if you search for
    # 'python' you get more than 8.000.000 results
    _MAX_RESULTS = float('inf')
    IE_NAME = 'youtube:search'
    _SEARCH_KEY = 'ytsearch'
    _SEARCH_PARAMS = None
    _TESTS = []

    def _entries(self, query, n):
        data = {
            'context': {
                'client': {
                    'clientName': 'WEB',
                    'clientVersion': '2.20201021.03.00',
                }
            },
            'query': query,
        }
        if self._SEARCH_PARAMS:
            data['params'] = self._SEARCH_PARAMS
        total = 0
        for page_num in itertools.count(1):
            search = self._download_json(
                'https://www.youtube.com/youtubei/v1/search?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8',
                video_id='query "%s"' % query,
                note='Downloading page %s' % page_num,
                errnote='Unable to download API page', fatal=False,
                data=json.dumps(data).encode('utf8'),
                headers={'content-type': 'application/json'})
            if not search:
                break
            slr_contents = try_get(
                search,
                (lambda x: x['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents'],
                 lambda x: x['onResponseReceivedCommands'][0]['appendContinuationItemsAction']['continuationItems']),
                list)
            if not slr_contents:
                break
            isr_contents = try_get(
                slr_contents,
                lambda x: x[0]['itemSectionRenderer']['contents'],
                list)
            if not isr_contents:
                break
            for content in isr_contents:
                if not isinstance(content, dict):
                    continue
                video = content.get('videoRenderer')
                if not isinstance(video, dict):
                    continue
                video_id = video.get('videoId')
                if not video_id:
                    continue
                title = try_get(video, lambda x: x['title']['runs'][0]['text'], compat_str)
                description = try_get(video, lambda x: x['descriptionSnippet']['runs'][0]['text'], compat_str)
                duration = parse_duration(try_get(video, lambda x: x['lengthText']['simpleText'], compat_str))
                view_count_text = try_get(video, lambda x: x['viewCountText']['simpleText'], compat_str) or ''
                view_count = int_or_none(self._search_regex(
                    r'^(\d+)', re.sub(r'\s', '', view_count_text),
                    'view count', default=None))
                uploader = try_get(video, lambda x: x['ownerText']['runs'][0]['text'], compat_str)
                total += 1
                yield {
                    '_type': 'url_transparent',
                    'ie_key': YoutubeIE.ie_key(),
                    'id': video_id,
                    'url': video_id,
                    'title': title,
                    'description': description,
                    'duration': duration,
                    'view_count': view_count,
                    'uploader': uploader,
                }
                if total == n:
                    return
            token = try_get(
                slr_contents,
                lambda x: x[1]['continuationItemRenderer']['continuationEndpoint']['continuationCommand']['token'],
                compat_str)
            if not token:
                break
            data['continuation'] = token

    def _get_n_results(self, query, n):
        """Get a specified number of results for a query"""
        return self.playlist_result(self._entries(query, n), query)


class YoutubeSearchDateIE(YoutubeSearchIE):
    IE_NAME = YoutubeSearchIE.IE_NAME + ':date'
    _SEARCH_KEY = 'ytsearchdate'
    IE_DESC = 'YouTube.com searches, newest videos first'
    _SEARCH_PARAMS = 'CAI%3D'


class YoutubeSearchURLIE(YoutubeSearchBaseInfoExtractor):
    IE_DESC = 'YouTube.com search URLs'
    IE_NAME = 'youtube:search_url'
    _VALID_URL = r'https?://(?:www\.)?youtube\.com/results\?(.*?&)?(?:search_query|q)=(?P<query>[^&]+)(?:[&]|$)'
    _SEARCH_DATA = r'(?:window\["ytInitialData"\]|ytInitialData)\W?=\W?({.*?});'
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

    def _find_videos_in_json(self, extracted):
        videos = []

        def _real_find(obj):
            if obj is None or isinstance(obj, str):
                return

            if type(obj) is list:
                for elem in obj:
                    _real_find(elem)

            if type(obj) is dict:
                if "videoId" in obj:
                    videos.append(obj)
                    return

                for _, o in obj.items():
                    _real_find(o)

        _real_find(extracted)

        return videos

    def extract_videos_from_page_impl(self, page, ids_in_page, titles_in_page):
        search_response = self._parse_json(self._search_regex(self._SEARCH_DATA, page, 'ytInitialData'), None)

        result_items = self._find_videos_in_json(search_response)

        for renderer in result_items:
            video_id = try_get(renderer, lambda x: x['videoId'])
            video_title = try_get(renderer, lambda x: x['title']['runs'][0]['text']) or try_get(renderer, lambda x: x['title']['simpleText'])

            if video_id is None or video_title is None:
                # we do not have a videoRenderer or title extraction broke
                continue

            video_title = video_title.strip()

            try:
                idx = ids_in_page.index(video_id)
                if video_title and not titles_in_page[idx]:
                    titles_in_page[idx] = video_title
            except ValueError:
                ids_in_page.append(video_id)
                titles_in_page.append(video_title)

    def extract_videos_from_page(self, page):
        ids_in_page = []
        titles_in_page = []
        self.extract_videos_from_page_impl(page, ids_in_page, titles_in_page)
        return zip(ids_in_page, titles_in_page)

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        query = compat_urllib_parse_unquote_plus(mobj.group('query'))
        webpage = self._download_webpage(url, query)
        return self.playlist_result(self._process_page(webpage), playlist_title=query)


class YoutubeShowIE(YoutubePlaylistsBaseInfoExtractor):
    IE_DESC = 'YouTube.com (multi-season) shows'
    _VALID_URL = r'https?://(?:www\.)?youtube\.com/show/(?P<id>[^?#]*)'
    IE_NAME = 'youtube:show'
    _TESTS = [{
        'url': 'https://www.youtube.com/show/airdisasters',
        'playlist_mincount': 5,
        'info_dict': {
            'id': 'airdisasters',
            'title': 'Air Disasters',
        }
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        return super(YoutubeShowIE, self)._real_extract(
            'https://www.youtube.com/show/%s/playlists' % playlist_id)


class YoutubeFeedsInfoExtractor(YoutubeBaseInfoExtractor):
    """
    Base class for feed extractors
    Subclasses must define the _FEED_NAME and _PLAYLIST_TITLE properties.
    """
    _LOGIN_REQUIRED = True
    _FEED_DATA = r'(?:window\["ytInitialData"\]|ytInitialData)\W?=\W?({.*?});'
    _YTCFG_DATA = r"ytcfg.set\(({.*?})\)"

    @property
    def IE_NAME(self):
        return 'youtube:%s' % self._FEED_NAME

    def _real_initialize(self):
        self._login()

    def _find_videos_in_json(self, extracted):
        videos = []
        c = {}

        def _real_find(obj):
            if obj is None or isinstance(obj, str):
                return

            if type(obj) is list:
                for elem in obj:
                    _real_find(elem)

            if type(obj) is dict:
                if "videoId" in obj:
                    videos.append(obj)
                    return

                if "nextContinuationData" in obj:
                    c["continuation"] = obj["nextContinuationData"]
                    return

                for _, o in obj.items():
                    _real_find(o)

        _real_find(extracted)

        return videos, try_get(c, lambda x: x["continuation"])

    def _entries(self, page):
        info = []

        yt_conf = self._parse_json(self._search_regex(self._YTCFG_DATA, page, 'ytcfg.set', default="null"), None, fatal=False)

        search_response = self._parse_json(self._search_regex(self._FEED_DATA, page, 'ytInitialData'), None)

        for page_num in itertools.count(1):
            video_info, continuation = self._find_videos_in_json(search_response)

            new_info = []

            for v in video_info:
                v_id = try_get(v, lambda x: x['videoId'])
                if not v_id:
                    continue

                have_video = False
                for old in info:
                    if old['videoId'] == v_id:
                        have_video = True
                        break

                if not have_video:
                    new_info.append(v)

            if not new_info:
                break

            info.extend(new_info)

            for video in new_info:
                yield self.url_result(try_get(video, lambda x: x['videoId']), YoutubeIE.ie_key(), video_title=try_get(video, lambda x: x['title']['runs'][0]['text']) or try_get(video, lambda x: x['title']['simpleText']))

            if not continuation or not yt_conf:
                break

            search_response = self._download_json(
                'https://www.youtube.com/browse_ajax', self._PLAYLIST_TITLE,
                'Downloading page #%s' % page_num,
                transform_source=uppercase_escape,
                query={
                    "ctoken": try_get(continuation, lambda x: x["continuation"]),
                    "continuation": try_get(continuation, lambda x: x["continuation"]),
                    "itct": try_get(continuation, lambda x: x["clickTrackingParams"])
                },
                headers={
                    "X-YouTube-Client-Name": try_get(yt_conf, lambda x: x["INNERTUBE_CONTEXT_CLIENT_NAME"]),
                    "X-YouTube-Client-Version": try_get(yt_conf, lambda x: x["INNERTUBE_CONTEXT_CLIENT_VERSION"]),
                    "X-Youtube-Identity-Token": try_get(yt_conf, lambda x: x["ID_TOKEN"]),
                    "X-YouTube-Device": try_get(yt_conf, lambda x: x["DEVICE"]),
                    "X-YouTube-Page-CL": try_get(yt_conf, lambda x: x["PAGE_CL"]),
                    "X-YouTube-Page-Label": try_get(yt_conf, lambda x: x["PAGE_BUILD_LABEL"]),
                    "X-YouTube-Variants-Checksum": try_get(yt_conf, lambda x: x["VARIANTS_CHECKSUM"]),
                })

    def _real_extract(self, url):
        page = self._download_webpage(
            'https://www.youtube.com/feed/%s' % self._FEED_NAME,
            self._PLAYLIST_TITLE)
        return self.playlist_result(
            self._entries(page), playlist_title=self._PLAYLIST_TITLE)


class YoutubeWatchLaterIE(YoutubePlaylistIE):
    IE_NAME = 'youtube:watchlater'
    IE_DESC = 'Youtube watch later list, ":ytwatchlater" for short (requires authentication)'
    _VALID_URL = r'https?://(?:www\.)?youtube\.com/(?:feed/watch_later|(?:playlist|watch)\?(?:.+&)?list=WL)|:ytwatchlater'

    _TESTS = [{
        'url': 'https://www.youtube.com/playlist?list=WL',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/watch?v=bCNU9TrbiRk&index=1&list=WL',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        _, video = self._check_download_just_video(url, 'WL')
        if video:
            return video
        _, playlist = self._extract_playlist('WL')
        return playlist


class YoutubeFavouritesIE(YoutubeBaseInfoExtractor):
    IE_NAME = 'youtube:favorites'
    IE_DESC = 'YouTube.com favourite videos, ":ytfav" for short (requires authentication)'
    _VALID_URL = r'https?://(?:www\.)?youtube\.com/my_favorites|:ytfav(?:ou?rites)?'
    _LOGIN_REQUIRED = True

    def _real_extract(self, url):
        webpage = self._download_webpage('https://www.youtube.com/my_favorites', 'Youtube Favourites videos')
        playlist_id = self._search_regex(r'list=(.+?)["&]', webpage, 'favourites playlist id')
        return self.url_result(playlist_id, 'YoutubePlaylist')


class YoutubeRecommendedIE(YoutubeFeedsInfoExtractor):
    IE_DESC = 'YouTube.com recommended videos, ":ytrec" for short (requires authentication)'
    _VALID_URL = r'https?://(?:www\.)?youtube\.com/feed/recommended|:ytrec(?:ommended)?'
    _FEED_NAME = 'recommended'
    _PLAYLIST_TITLE = 'Youtube Recommended videos'


class YoutubeSubscriptionsIE(YoutubeFeedsInfoExtractor):
    IE_DESC = 'YouTube.com subscriptions feed, "ytsubs" keyword (requires authentication)'
    _VALID_URL = r'https?://(?:www\.)?youtube\.com/feed/subscriptions|:ytsubs(?:criptions)?'
    _FEED_NAME = 'subscriptions'
    _PLAYLIST_TITLE = 'Youtube Subscriptions'


class YoutubeHistoryIE(YoutubeFeedsInfoExtractor):
    IE_DESC = 'Youtube watch history, ":ythistory" for short (requires authentication)'
    _VALID_URL = r'https?://(?:www\.)?youtube\.com/feed/history|:ythistory'
    _FEED_NAME = 'history'
    _PLAYLIST_TITLE = 'Youtube History'


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
