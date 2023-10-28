import json
import random
import re

from .common import InfoExtractor
from .periscope import PeriscopeBaseIE, PeriscopeIE
from ..compat import functools  # isort: split
from ..compat import (
    compat_parse_qs,
    compat_urllib_parse_unquote,
    compat_urllib_parse_urlparse,
)
from ..utils import (
    ExtractorError,
    dict_get,
    filter_dict,
    float_or_none,
    format_field,
    int_or_none,
    make_archive_id,
    remove_end,
    str_or_none,
    strip_or_none,
    traverse_obj,
    try_call,
    try_get,
    unified_timestamp,
    update_url_query,
    url_or_none,
    xpath_text,
)


class TwitterBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'twitter'
    _API_BASE = 'https://api.twitter.com/1.1/'
    _GRAPHQL_API_BASE = 'https://twitter.com/i/api/graphql/'
    _BASE_REGEX = r'https?://(?:(?:www|m(?:obile)?)\.)?(?:twitter\.com|twitter3e4tixl4xyajtrzo62zg5vztmjuricljdp2c5kshju4avyoid\.onion)/'
    _AUTH = 'AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA'
    _LEGACY_AUTH = 'AAAAAAAAAAAAAAAAAAAAAIK1zgAAAAAA2tUWuhGZ2JceoId5GwYWU5GspY4%3DUq7gzFoCZs1QfwGoVdvSac3IniczZEYXIcDyumCauIXpcAPorE'
    _flow_token = None

    _LOGIN_INIT_DATA = json.dumps({
        'input_flow_data': {
            'flow_context': {
                'debug_overrides': {},
                'start_location': {
                    'location': 'unknown'
                }
            }
        },
        'subtask_versions': {
            'action_list': 2,
            'alert_dialog': 1,
            'app_download_cta': 1,
            'check_logged_in_account': 1,
            'choice_selection': 3,
            'contacts_live_sync_permission_prompt': 0,
            'cta': 7,
            'email_verification': 2,
            'end_flow': 1,
            'enter_date': 1,
            'enter_email': 2,
            'enter_password': 5,
            'enter_phone': 2,
            'enter_recaptcha': 1,
            'enter_text': 5,
            'enter_username': 2,
            'generic_urt': 3,
            'in_app_notification': 1,
            'interest_picker': 3,
            'js_instrumentation': 1,
            'menu_dialog': 1,
            'notifications_permission_prompt': 2,
            'open_account': 2,
            'open_home_timeline': 1,
            'open_link': 1,
            'phone_verification': 4,
            'privacy_options': 1,
            'security_key': 3,
            'select_avatar': 4,
            'select_banner': 2,
            'settings_list': 7,
            'show_code': 1,
            'sign_up': 2,
            'sign_up_review': 4,
            'tweet_selection_urt': 1,
            'update_users': 1,
            'upload_media': 1,
            'user_recommendations_list': 4,
            'user_recommendations_urt': 1,
            'wait_spinner': 3,
            'web_modal': 1
        }
    }, separators=(',', ':')).encode()

    def _extract_variant_formats(self, variant, video_id):
        variant_url = variant.get('url')
        if not variant_url:
            return [], {}
        elif '.m3u8' in variant_url:
            return self._extract_m3u8_formats_and_subtitles(
                variant_url, video_id, 'mp4', 'm3u8_native',
                m3u8_id='hls', fatal=False)
        else:
            tbr = int_or_none(dict_get(variant, ('bitrate', 'bit_rate')), 1000) or None
            f = {
                'url': variant_url,
                'format_id': 'http' + ('-%d' % tbr if tbr else ''),
                'tbr': tbr,
            }
            self._search_dimensions_in_video_url(f, variant_url)
            return [f], {}

    def _extract_formats_from_vmap_url(self, vmap_url, video_id):
        vmap_url = url_or_none(vmap_url)
        if not vmap_url:
            return [], {}
        vmap_data = self._download_xml(vmap_url, video_id)
        formats = []
        subtitles = {}
        urls = []
        for video_variant in vmap_data.findall('.//{http://twitter.com/schema/videoVMapV2.xsd}videoVariant'):
            video_variant.attrib['url'] = compat_urllib_parse_unquote(
                video_variant.attrib['url'])
            urls.append(video_variant.attrib['url'])
            fmts, subs = self._extract_variant_formats(
                video_variant.attrib, video_id)
            formats.extend(fmts)
            subtitles = self._merge_subtitles(subtitles, subs)
        video_url = strip_or_none(xpath_text(vmap_data, './/MediaFile'))
        if video_url not in urls:
            fmts, subs = self._extract_variant_formats({'url': video_url}, video_id)
            formats.extend(fmts)
            subtitles = self._merge_subtitles(subtitles, subs)
        return formats, subtitles

    @staticmethod
    def _search_dimensions_in_video_url(a_format, video_url):
        m = re.search(r'/(?P<width>\d+)x(?P<height>\d+)/', video_url)
        if m:
            a_format.update({
                'width': int(m.group('width')),
                'height': int(m.group('height')),
            })

    @property
    def is_logged_in(self):
        return bool(self._get_cookies(self._API_BASE).get('auth_token'))

    @functools.cached_property
    def _selected_api(self):
        return self._configuration_arg('api', ['graphql'], ie_key='Twitter')[0]

    def _fetch_guest_token(self, display_id):
        guest_token = traverse_obj(self._download_json(
            f'{self._API_BASE}guest/activate.json', display_id, 'Downloading guest token', data=b'',
            headers=self._set_base_headers(legacy=display_id and self._selected_api == 'legacy')),
            ('guest_token', {str}))
        if not guest_token:
            raise ExtractorError('Could not retrieve guest token')
        return guest_token

    def _set_base_headers(self, legacy=False):
        bearer_token = self._LEGACY_AUTH if legacy and not self.is_logged_in else self._AUTH
        return filter_dict({
            'Authorization': f'Bearer {bearer_token}',
            'x-csrf-token': try_call(lambda: self._get_cookies(self._API_BASE)['ct0'].value),
        })

    def _call_login_api(self, note, headers, query={}, data=None):
        response = self._download_json(
            f'{self._API_BASE}onboarding/task.json', None, note,
            headers=headers, query=query, data=data, expected_status=400)
        error = traverse_obj(response, ('errors', 0, 'message', {str}))
        if error:
            raise ExtractorError(f'Login failed, Twitter API says: {error}', expected=True)
        elif traverse_obj(response, 'status') != 'success':
            raise ExtractorError('Login was unsuccessful')

        subtask = traverse_obj(
            response, ('subtasks', ..., 'subtask_id', {str}), get_all=False)
        if not subtask:
            raise ExtractorError('Twitter API did not return next login subtask')

        self._flow_token = response['flow_token']

        return subtask

    def _perform_login(self, username, password):
        if self.is_logged_in:
            return

        webpage = self._download_webpage('https://twitter.com/', None, 'Downloading login page')
        guest_token = self._search_regex(
            r'\.cookie\s*=\s*["\']gt=(\d+);', webpage, 'gt', default=None) or self._fetch_guest_token(None)
        headers = {
            **self._set_base_headers(),
            'content-type': 'application/json',
            'x-guest-token': guest_token,
            'x-twitter-client-language': 'en',
            'x-twitter-active-user': 'yes',
            'Referer': 'https://twitter.com/',
            'Origin': 'https://twitter.com',
        }

        def build_login_json(*subtask_inputs):
            return json.dumps({
                'flow_token': self._flow_token,
                'subtask_inputs': subtask_inputs
            }, separators=(',', ':')).encode()

        def input_dict(subtask_id, text):
            return {
                'subtask_id': subtask_id,
                'enter_text': {
                    'text': text,
                    'link': 'next_link'
                }
            }

        next_subtask = self._call_login_api(
            'Downloading flow token', headers, query={'flow_name': 'login'}, data=self._LOGIN_INIT_DATA)

        while not self.is_logged_in:
            if next_subtask == 'LoginJsInstrumentationSubtask':
                next_subtask = self._call_login_api(
                    'Submitting JS instrumentation response', headers, data=build_login_json({
                        'subtask_id': next_subtask,
                        'js_instrumentation': {
                            'response': '{}',
                            'link': 'next_link'
                        }
                    }))

            elif next_subtask == 'LoginEnterUserIdentifierSSO':
                next_subtask = self._call_login_api(
                    'Submitting username', headers, data=build_login_json({
                        'subtask_id': next_subtask,
                        'settings_list': {
                            'setting_responses': [{
                                'key': 'user_identifier',
                                'response_data': {
                                    'text_data': {
                                        'result': username
                                    }
                                }
                            }],
                            'link': 'next_link'
                        }
                    }))

            elif next_subtask == 'LoginEnterAlternateIdentifierSubtask':
                next_subtask = self._call_login_api(
                    'Submitting alternate identifier', headers,
                    data=build_login_json(input_dict(next_subtask, self._get_tfa_info(
                        'one of username, phone number or email that was not used as --username'))))

            elif next_subtask == 'LoginEnterPassword':
                next_subtask = self._call_login_api(
                    'Submitting password', headers, data=build_login_json({
                        'subtask_id': next_subtask,
                        'enter_password': {
                            'password': password,
                            'link': 'next_link'
                        }
                    }))

            elif next_subtask == 'AccountDuplicationCheck':
                next_subtask = self._call_login_api(
                    'Submitting account duplication check', headers, data=build_login_json({
                        'subtask_id': next_subtask,
                        'check_logged_in_account': {
                            'link': 'AccountDuplicationCheck_false'
                        }
                    }))

            elif next_subtask == 'LoginTwoFactorAuthChallenge':
                next_subtask = self._call_login_api(
                    'Submitting 2FA token', headers, data=build_login_json(input_dict(
                        next_subtask, self._get_tfa_info('two-factor authentication token'))))

            elif next_subtask == 'LoginAcid':
                next_subtask = self._call_login_api(
                    'Submitting confirmation code', headers, data=build_login_json(input_dict(
                        next_subtask, self._get_tfa_info('confirmation code sent to your email or phone'))))

            elif next_subtask == 'ArkoseLogin':
                self.raise_login_required('Twitter is requiring captcha for this login attempt', method='cookies')

            elif next_subtask == 'DenyLoginSubtask':
                self.raise_login_required('Twitter rejected this login attempt as suspicious', method='cookies')

            elif next_subtask == 'LoginSuccessSubtask':
                raise ExtractorError('Twitter API did not grant auth token cookie')

            else:
                raise ExtractorError(f'Unrecognized subtask ID "{next_subtask}"')

        self.report_login()

    def _call_api(self, path, video_id, query={}, graphql=False):
        headers = self._set_base_headers(legacy=not graphql and self._selected_api == 'legacy')
        headers.update({
            'x-twitter-auth-type': 'OAuth2Session',
            'x-twitter-client-language': 'en',
            'x-twitter-active-user': 'yes',
        } if self.is_logged_in else {
            'x-guest-token': self._fetch_guest_token(video_id)
        })
        allowed_status = {400, 401, 403, 404} if graphql else {403}
        result = self._download_json(
            (self._GRAPHQL_API_BASE if graphql else self._API_BASE) + path,
            video_id, headers=headers, query=query, expected_status=allowed_status,
            note=f'Downloading {"GraphQL" if graphql else "legacy API"} JSON')

        if result.get('errors'):
            errors = ', '.join(set(traverse_obj(result, ('errors', ..., 'message', {str}))))
            if errors and 'not authorized' in errors:
                self.raise_login_required(remove_end(errors, '.'))
            raise ExtractorError(f'Error(s) while querying API: {errors or "Unknown error"}')

        return result

    def _build_graphql_query(self, media_id):
        raise NotImplementedError('Method must be implemented to support GraphQL')

    def _call_graphql_api(self, endpoint, media_id):
        data = self._build_graphql_query(media_id)
        query = {key: json.dumps(value, separators=(',', ':')) for key, value in data.items()}
        return traverse_obj(self._call_api(endpoint, media_id, query=query, graphql=True), 'data')


class TwitterCardIE(InfoExtractor):
    IE_NAME = 'twitter:card'
    _VALID_URL = TwitterBaseIE._BASE_REGEX + r'i/(?:cards/tfw/v1|videos(?:/tweet)?)/(?P<id>\d+)'
    _TESTS = [
        {
            'url': 'https://twitter.com/i/cards/tfw/v1/560070183650213889',
            # MD5 checksums are different in different places
            'info_dict': {
                'id': '560070131976392705',
                'ext': 'mp4',
                'title': "Twitter - You can now shoot, edit and share video on Twitter. Capture life's most moving moments from your perspective.",
                'description': 'md5:18d3e24bb4f6e5007487dd546e53bd96',
                'uploader': 'Twitter',
                'uploader_id': 'Twitter',
                'thumbnail': r're:^https?://.*\.jpg',
                'duration': 30.033,
                'timestamp': 1422366112,
                'upload_date': '20150127',
                'age_limit': 0,
                'comment_count': int,
                'tags': [],
                'repost_count': int,
                'like_count': int,
                'display_id': '560070183650213889',
                'uploader_url': 'https://twitter.com/Twitter',
            },
        },
        {
            'url': 'https://twitter.com/i/cards/tfw/v1/623160978427936768',
            'md5': '7137eca597f72b9abbe61e5ae0161399',
            'info_dict': {
                'id': '623160978427936768',
                'ext': 'mp4',
                'title': "NASA - Fly over Pluto's icy Norgay Mountains and Sputnik Plain in this @NASANewHorizons #PlutoFlyby video.",
                'description': "Fly over Pluto's icy Norgay Mountains and Sputnik Plain in this @NASANewHorizons #PlutoFlyby video. https://t.co/BJYgOjSeGA",
                'uploader': 'NASA',
                'uploader_id': 'NASA',
                'timestamp': 1437408129,
                'upload_date': '20150720',
                'uploader_url': 'https://twitter.com/NASA',
                'age_limit': 0,
                'comment_count': int,
                'like_count': int,
                'repost_count': int,
                'tags': ['PlutoFlyby'],
            },
            'params': {'format': '[protocol=https]'}
        },
        {
            'url': 'https://twitter.com/i/cards/tfw/v1/654001591733886977',
            'md5': 'b6d9683dd3f48e340ded81c0e917ad46',
            'info_dict': {
                'id': 'dq4Oj5quskI',
                'ext': 'mp4',
                'title': 'Ubuntu 11.10 Overview',
                'description': 'md5:a831e97fa384863d6e26ce48d1c43376',
                'upload_date': '20111013',
                'uploader': 'OMG! UBUNTU!',
                'uploader_id': 'omgubuntu',
                'channel_url': 'https://www.youtube.com/channel/UCIiSwcm9xiFb3Y4wjzR41eQ',
                'channel_id': 'UCIiSwcm9xiFb3Y4wjzR41eQ',
                'channel_follower_count': int,
                'chapters': 'count:8',
                'uploader_url': 'http://www.youtube.com/user/omgubuntu',
                'duration': 138,
                'categories': ['Film & Animation'],
                'age_limit': 0,
                'comment_count': int,
                'availability': 'public',
                'like_count': int,
                'thumbnail': 'https://i.ytimg.com/vi/dq4Oj5quskI/maxresdefault.jpg',
                'view_count': int,
                'tags': 'count:12',
                'channel': 'OMG! UBUNTU!',
                'playable_in_embed': True,
            },
            'add_ie': ['Youtube'],
        },
        {
            'url': 'https://twitter.com/i/cards/tfw/v1/665289828897005568',
            'info_dict': {
                'id': 'iBb2x00UVlv',
                'ext': 'mp4',
                'upload_date': '20151113',
                'uploader_id': '1189339351084113920',
                'uploader': 'ArsenalTerje',
                'title': 'Vine by ArsenalTerje',
                'timestamp': 1447451307,
                'alt_title': 'Vine by ArsenalTerje',
                'comment_count': int,
                'like_count': int,
                'thumbnail': r're:^https?://[^?#]+\.jpg',
                'view_count': int,
                'repost_count': int,
            },
            'add_ie': ['Vine'],
            'params': {'skip_download': 'm3u8'},
        },
        {
            'url': 'https://twitter.com/i/videos/tweet/705235433198714880',
            'md5': '884812a2adc8aaf6fe52b15ccbfa3b88',
            'info_dict': {
                'id': '705235433198714880',
                'ext': 'mp4',
                'title': "Brent Yarina - Khalil Iverson's missed highlight dunk. And made highlight dunk. In one highlight.",
                'description': "Khalil Iverson's missed highlight dunk. And made highlight dunk. In one highlight. https://t.co/OrxcJ28Bns",
                'uploader': 'Brent Yarina',
                'uploader_id': 'BTNBrentYarina',
                'timestamp': 1456976204,
                'upload_date': '20160303',
            },
            'skip': 'This content is no longer available.',
        },
        {
            'url': 'https://twitter.com/i/videos/752274308186120192',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        status_id = self._match_id(url)
        return self.url_result(
            'https://twitter.com/statuses/' + status_id,
            TwitterIE.ie_key(), status_id)


class TwitterIE(TwitterBaseIE):
    IE_NAME = 'twitter'
    _VALID_URL = TwitterBaseIE._BASE_REGEX + r'(?:(?:i/web|[^/]+)/status|statuses)/(?P<id>\d+)(?:/(?:video|photo)/(?P<index>\d+))?'

    _TESTS = [{
        'url': 'https://twitter.com/freethenipple/status/643211948184596480',
        'info_dict': {
            'id': '643211870443208704',
            'display_id': '643211948184596480',
            'ext': 'mp4',
            'title': 'FREE THE NIPPLE - FTN supporters on Hollywood Blvd today!',
            'thumbnail': r're:^https?://.*\.jpg',
            'description': 'FTN supporters on Hollywood Blvd today! http://t.co/c7jHH749xJ',
            'uploader': 'FREE THE NIPPLE',
            'uploader_id': 'freethenipple',
            'duration': 12.922,
            'timestamp': 1442188653,
            'upload_date': '20150913',
            'uploader_url': 'https://twitter.com/freethenipple',
            'comment_count': int,
            'repost_count': int,
            'like_count': int,
            'view_count': int,
            'tags': [],
            'age_limit': 18,
        },
    }, {
        'url': 'https://twitter.com/giphz/status/657991469417025536/photo/1',
        'md5': 'f36dcd5fb92bf7057f155e7d927eeb42',
        'info_dict': {
            'id': '657991469417025536',
            'ext': 'mp4',
            'title': 'Gifs - tu vai cai tu vai cai tu nao eh capaz disso tu vai cai',
            'description': 'Gifs on Twitter: "tu vai cai tu vai cai tu nao eh capaz disso tu vai cai https://t.co/tM46VHFlO5"',
            'thumbnail': r're:^https?://.*\.png',
            'uploader': 'Gifs',
            'uploader_id': 'giphz',
        },
        'expected_warnings': ['height', 'width'],
        'skip': 'Account suspended',
    }, {
        'url': 'https://twitter.com/starwars/status/665052190608723968',
        'info_dict': {
            'id': '665052190608723968',
            'display_id': '665052190608723968',
            'ext': 'mp4',
            'title': r're:Star Wars.*A new beginning is coming December 18.*',
            'description': 'A new beginning is coming December 18. Watch the official 60 second #TV spot for #StarWars: #TheForceAwakens. https://t.co/OkSqT2fjWJ',
            'uploader_id': 'starwars',
            'uploader': r're:Star Wars.*',
            'timestamp': 1447395772,
            'upload_date': '20151113',
            'uploader_url': 'https://twitter.com/starwars',
            'comment_count': int,
            'repost_count': int,
            'like_count': int,
            'tags': ['TV', 'StarWars', 'TheForceAwakens'],
            'age_limit': 0,
        },
    }, {
        'url': 'https://twitter.com/BTNBrentYarina/status/705235433198714880',
        'info_dict': {
            'id': '705235433198714880',
            'ext': 'mp4',
            'title': "Brent Yarina - Khalil Iverson's missed highlight dunk. And made highlight dunk. In one highlight.",
            'description': "Khalil Iverson's missed highlight dunk. And made highlight dunk. In one highlight. https://t.co/OrxcJ28Bns",
            'uploader_id': 'BTNBrentYarina',
            'uploader': 'Brent Yarina',
            'timestamp': 1456976204,
            'upload_date': '20160303',
            'uploader_url': 'https://twitter.com/BTNBrentYarina',
            'comment_count': int,
            'repost_count': int,
            'like_count': int,
            'tags': [],
            'age_limit': 0,
        },
        'params': {
            # The same video as https://twitter.com/i/videos/tweet/705235433198714880
            # Test case of TwitterCardIE
            'skip_download': True,
        },
        'skip': 'Dead external link',
    }, {
        'url': 'https://twitter.com/jaydingeer/status/700207533655363584',
        'info_dict': {
            'id': '700207414000242688',
            'display_id': '700207533655363584',
            'ext': 'mp4',
            'title': 'jaydin donte geer - BEAT PROD: @suhmeduh #Damndaniel',
            'description': 'BEAT PROD: @suhmeduh  https://t.co/HBrQ4AfpvZ #Damndaniel https://t.co/byBooq2ejZ',
            'thumbnail': r're:^https?://.*\.jpg',
            'uploader': 'jaydin donte geer',
            'uploader_id': 'jaydingeer',
            'duration': 30.0,
            'timestamp': 1455777459,
            'upload_date': '20160218',
            'uploader_url': 'https://twitter.com/jaydingeer',
            'comment_count': int,
            'repost_count': int,
            'like_count': int,
            'view_count': int,
            'tags': ['Damndaniel'],
            'age_limit': 0,
        },
    }, {
        'url': 'https://twitter.com/Filmdrunk/status/713801302971588609',
        'md5': '89a15ed345d13b86e9a5a5e051fa308a',
        'info_dict': {
            'id': 'MIOxnrUteUd',
            'ext': 'mp4',
            'title': 'Dr.Pepperの飲み方 #japanese #バカ #ドクペ #電動ガン',
            'uploader': 'TAKUMA',
            'uploader_id': '1004126642786242560',
            'timestamp': 1402826626,
            'upload_date': '20140615',
            'thumbnail': r're:^https?://.*\.jpg',
            'alt_title': 'Vine by TAKUMA',
            'comment_count': int,
            'repost_count': int,
            'like_count': int,
            'view_count': int,
        },
        'add_ie': ['Vine'],
    }, {
        'url': 'https://twitter.com/captainamerica/status/719944021058060289',
        'info_dict': {
            'id': '717462543795523584',
            'display_id': '719944021058060289',
            'ext': 'mp4',
            'title': 'Captain America - @King0fNerd Are you sure you made the right choice? Find out in theaters.',
            'description': '@King0fNerd Are you sure you made the right choice? Find out in theaters. https://t.co/GpgYi9xMJI',
            'uploader_id': 'CaptainAmerica',
            'uploader': 'Captain America',
            'duration': 3.17,
            'timestamp': 1460483005,
            'upload_date': '20160412',
            'uploader_url': 'https://twitter.com/CaptainAmerica',
            'thumbnail': r're:^https?://.*\.jpg',
            'comment_count': int,
            'repost_count': int,
            'like_count': int,
            'view_count': int,
            'tags': [],
            'age_limit': 0,
        },
    }, {
        'url': 'https://twitter.com/OPP_HSD/status/779210622571536384',
        'info_dict': {
            'id': '1zqKVVlkqLaKB',
            'ext': 'mp4',
            'title': 'Sgt Kerry Schmidt - Ontario Provincial Police - Road rage, mischief, assault, rollover and fire in one occurrence',
            'upload_date': '20160923',
            'uploader_id': '1PmKqpJdOJQoY',
            'uploader': 'Sgt Kerry Schmidt - Ontario Provincial Police',
            'timestamp': 1474613214,
            'thumbnail': r're:^https?://.*\.jpg',
        },
        'add_ie': ['Periscope'],
    }, {
        # has mp4 formats via mobile API
        'url': 'https://twitter.com/news_al3alm/status/852138619213144067',
        'info_dict': {
            'id': '852077943283097602',
            'ext': 'mp4',
            'title': 'عالم الأخبار - كلمة تاريخية بجلسة الجناسي التاريخية.. النائب خالد مؤنس العتيبي للمعارضين : اتقوا الله .. الظلم ظلمات يوم القيامة',
            'description': 'كلمة تاريخية بجلسة الجناسي التاريخية.. النائب خالد مؤنس العتيبي للمعارضين : اتقوا الله .. الظلم ظلمات يوم القيامة   https://t.co/xg6OhpyKfN',
            'uploader': 'عالم الأخبار',
            'uploader_id': 'news_al3alm',
            'duration': 277.4,
            'timestamp': 1492000653,
            'upload_date': '20170412',
            'display_id': '852138619213144067',
            'age_limit': 0,
            'uploader_url': 'https://twitter.com/news_al3alm',
            'thumbnail': r're:^https?://.*\.jpg',
            'tags': [],
            'repost_count': int,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
        },
    }, {
        'url': 'https://twitter.com/i/web/status/910031516746514432',
        'info_dict': {
            'id': '910030238373089285',
            'display_id': '910031516746514432',
            'ext': 'mp4',
            'title': 'Préfet de Guadeloupe - [Direct] #Maria Le centre se trouve actuellement au sud de Basse-Terre. Restez confinés. Réfugiez-vous dans la pièce la + sûre.',
            'thumbnail': r're:^https?://.*\.jpg',
            'description': '[Direct] #Maria Le centre se trouve actuellement au sud de Basse-Terre. Restez confinés. Réfugiez-vous dans la pièce la + sûre. https://t.co/mwx01Rs4lo',
            'uploader': 'Préfet de Guadeloupe',
            'uploader_id': 'Prefet971',
            'duration': 47.48,
            'timestamp': 1505803395,
            'upload_date': '20170919',
            'uploader_url': 'https://twitter.com/Prefet971',
            'comment_count': int,
            'repost_count': int,
            'like_count': int,
            'view_count': int,
            'tags': ['Maria'],
            'age_limit': 0,
        },
        'params': {
            'skip_download': True,  # requires ffmpeg
        },
    }, {
        # card via api.twitter.com/1.1/videos/tweet/config
        'url': 'https://twitter.com/LisPower1/status/1001551623938805763',
        'info_dict': {
            'id': '1001551417340022785',
            'display_id': '1001551623938805763',
            'ext': 'mp4',
            'title': 're:.*?Shep is on a roll today.*?',
            'thumbnail': r're:^https?://.*\.jpg',
            'description': 'md5:37b9f2ff31720cef23b2bd42ee8a0f09',
            'uploader': 'Lis Power',
            'uploader_id': 'LisPower1',
            'duration': 111.278,
            'timestamp': 1527623489,
            'upload_date': '20180529',
            'uploader_url': 'https://twitter.com/LisPower1',
            'comment_count': int,
            'repost_count': int,
            'like_count': int,
            'view_count': int,
            'tags': [],
            'age_limit': 0,
        },
        'params': {
            'skip_download': True,  # requires ffmpeg
        },
    }, {
        'url': 'https://twitter.com/foobar/status/1087791357756956680',
        'info_dict': {
            'id': '1087791272830607360',
            'display_id': '1087791357756956680',
            'ext': 'mp4',
            'title': 'X - A new is coming.  Some of you got an opt-in to try it now. Check out the emoji button, quick keyboard shortcuts, upgraded trends, advanced search, and more. Let us know your thoughts!',
            'thumbnail': r're:^https?://.*\.jpg',
            'description': 'md5:6dfd341a3310fb97d80d2bf7145df976',
            'uploader': 'X',
            'uploader_id': 'X',
            'duration': 61.567,
            'timestamp': 1548184644,
            'upload_date': '20190122',
            'uploader_url': 'https://twitter.com/X',
            'comment_count': int,
            'repost_count': int,
            'like_count': int,
            'view_count': int,
            'tags': [],
            'age_limit': 0,
        },
        'skip': 'This Tweet is unavailable',
    }, {
        # not available in Periscope
        'url': 'https://twitter.com/ViviEducation/status/1136534865145286656',
        'info_dict': {
            'id': '1vOGwqejwoWxB',
            'ext': 'mp4',
            'title': 'Vivi - Vivi founder @lior_rauchy announcing our new student feedback tool live at @EduTECH_AU #EduTECH2019',
            'uploader': 'Vivi',
            'uploader_id': '1eVjYOLGkGrQL',
            'thumbnail': r're:^https?://.*\.jpg',
            'tags': ['EduTECH2019'],
            'view_count': int,
        },
        'add_ie': ['TwitterBroadcast'],
        'skip': 'Broadcast no longer exists',
    }, {
        # unified card
        'url': 'https://twitter.com/BrooklynNets/status/1349794411333394432?s=20',
        'info_dict': {
            'id': '1349774757969989634',
            'display_id': '1349794411333394432',
            'ext': 'mp4',
            'title': 'md5:d1c4941658e4caaa6cb579260d85dcba',
            'thumbnail': r're:^https?://.*\.jpg',
            'description': 'md5:71ead15ec44cee55071547d6447c6a3e',
            'uploader': 'Brooklyn Nets',
            'uploader_id': 'BrooklynNets',
            'duration': 324.484,
            'timestamp': 1610651040,
            'upload_date': '20210114',
            'uploader_url': 'https://twitter.com/BrooklynNets',
            'comment_count': int,
            'repost_count': int,
            'like_count': int,
            'tags': [],
            'age_limit': 0,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://twitter.com/oshtru/status/1577855540407197696',
        'info_dict': {
            'id': '1577855447914409984',
            'display_id': '1577855540407197696',
            'ext': 'mp4',
            'title': 'md5:9d198efb93557b8f8d5b78c480407214',
            'description': 'md5:b9c3699335447391d11753ab21c70a74',
            'upload_date': '20221006',
            'uploader': 'oshtru',
            'uploader_id': 'oshtru',
            'uploader_url': 'https://twitter.com/oshtru',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 30.03,
            'timestamp': 1665025050,
            'comment_count': int,
            'repost_count': int,
            'like_count': int,
            'view_count': int,
            'tags': [],
            'age_limit': 0,
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://twitter.com/UltimaShadowX/status/1577719286659006464',
        'info_dict': {
            'id': '1577719286659006464',
            'title': 'Ultima📛| New Era - Test',
            'description': 'Test https://t.co/Y3KEZD7Dad',
            'uploader': 'Ultima📛| New Era',
            'uploader_id': 'UltimaShadowX',
            'uploader_url': 'https://twitter.com/UltimaShadowX',
            'upload_date': '20221005',
            'timestamp': 1664992565,
            'comment_count': int,
            'repost_count': int,
            'like_count': int,
            'tags': [],
            'age_limit': 0,
        },
        'playlist_count': 4,
        'params': {'skip_download': True},
    }, {
        'url': 'https://twitter.com/MesoMax919/status/1575560063510810624',
        'info_dict': {
            'id': '1575559336759263233',
            'display_id': '1575560063510810624',
            'ext': 'mp4',
            'title': 'md5:eec26382babd0f7c18f041db8ae1c9c9',
            'thumbnail': r're:^https?://.*\.jpg',
            'description': 'md5:95aea692fda36a12081b9629b02daa92',
            'uploader': 'Max Olson',
            'uploader_id': 'MesoMax919',
            'uploader_url': 'https://twitter.com/MesoMax919',
            'duration': 21.321,
            'timestamp': 1664477766,
            'upload_date': '20220929',
            'comment_count': int,
            'repost_count': int,
            'like_count': int,
            'view_count': int,
            'tags': ['HurricaneIan'],
            'age_limit': 0,
        },
    }, {
        # Adult content, fails if not logged in
        'url': 'https://twitter.com/Rizdraws/status/1575199173472927762',
        'info_dict': {
            'id': '1575199163847000068',
            'display_id': '1575199173472927762',
            'ext': 'mp4',
            'title': str,
            'description': str,
            'uploader': str,
            'uploader_id': 'Rizdraws',
            'uploader_url': 'https://twitter.com/Rizdraws',
            'upload_date': '20220928',
            'timestamp': 1664391723,
            'thumbnail': r're:^https?://.+\.jpg',
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'age_limit': 18,
            'tags': []
        },
        'params': {'skip_download': 'The media could not be played'},
        'skip': 'Requires authentication',
    }, {
        # Playlist result only with graphql API
        'url': 'https://twitter.com/Srirachachau/status/1395079556562706435',
        'playlist_mincount': 2,
        'info_dict': {
            'id': '1395079556562706435',
            'title': str,
            'tags': [],
            'uploader': str,
            'like_count': int,
            'upload_date': '20210519',
            'age_limit': 0,
            'repost_count': int,
            'description': 'Here it is! Finished my gothic western cartoon. Pretty proud of it. It\'s got some goofs and lots of splashy over the top violence, something for everyone, hope you like it https://t.co/fOsG5glUnw',
            'uploader_id': 'Srirachachau',
            'comment_count': int,
            'uploader_url': 'https://twitter.com/Srirachachau',
            'timestamp': 1621447860,
        },
    }, {
        'url': 'https://twitter.com/DavidToons_/status/1578353380363501568',
        'playlist_mincount': 2,
        'info_dict': {
            'id': '1578353380363501568',
            'title': str,
            'uploader_id': 'DavidToons_',
            'repost_count': int,
            'like_count': int,
            'uploader': str,
            'timestamp': 1665143744,
            'uploader_url': 'https://twitter.com/DavidToons_',
            'description': 'Chris sounds like Linda from Bob\'s Burgers, so as an animator: this had to be done. https://t.co/WgJauwIW1w',
            'tags': [],
            'comment_count': int,
            'upload_date': '20221007',
            'age_limit': 0,
        },
    }, {
        'url': 'https://twitter.com/primevideouk/status/1578401165338976258',
        'playlist_count': 2,
        'info_dict': {
            'id': '1578401165338976258',
            'title': str,
            'description': 'md5:659a6b517a034b4cee5d795381a2dc41',
            'uploader': str,
            'uploader_id': 'primevideouk',
            'timestamp': 1665155137,
            'upload_date': '20221007',
            'age_limit': 0,
            'uploader_url': 'https://twitter.com/primevideouk',
            'comment_count': int,
            'repost_count': int,
            'like_count': int,
            'tags': ['TheRingsOfPower'],
        },
    }, {
        # Twitter Spaces
        'url': 'https://twitter.com/MoniqueCamarra/status/1550101959377551360',
        'info_dict': {
            'id': '1lPJqmBeeNAJb',
            'ext': 'm4a',
            'title': 'EuroFile@6 Ukraine Up-date-Draghi Defenestration-the West',
            'uploader': r're:Monique Camarra.+?',
            'uploader_id': 'MoniqueCamarra',
            'live_status': 'was_live',
            'release_timestamp': 1658417414,
            'description': 'md5:acce559345fd49f129c20dbcda3f1201',
            'timestamp': 1658407771,
            'release_date': '20220721',
            'upload_date': '20220721',
        },
        'add_ie': ['TwitterSpaces'],
        'params': {'skip_download': 'm3u8'},
        'skip': 'Requires authentication',
    }, {
        # URL specifies video number but --yes-playlist
        'url': 'https://twitter.com/CTVJLaidlaw/status/1600649710662213632/video/1',
        'playlist_mincount': 2,
        'info_dict': {
            'id': '1600649710662213632',
            'title': 'md5:be05989b0722e114103ed3851a0ffae2',
            'timestamp': 1670459604.0,
            'description': 'md5:591c19ce66fadc2359725d5cd0d1052c',
            'comment_count': int,
            'uploader_id': 'CTVJLaidlaw',
            'repost_count': int,
            'tags': ['colorectalcancer', 'cancerjourney', 'imnotaquitter'],
            'upload_date': '20221208',
            'age_limit': 0,
            'uploader': 'Jocelyn Laidlaw',
            'uploader_url': 'https://twitter.com/CTVJLaidlaw',
            'like_count': int,
        },
    }, {
        # URL specifies video number and --no-playlist
        'url': 'https://twitter.com/CTVJLaidlaw/status/1600649710662213632/video/2',
        'info_dict': {
            'id': '1600649511827013632',
            'ext': 'mp4',
            'title': 'md5:7662a0a27ce6faa3e5b160340f3cfab1',
            'thumbnail': r're:^https?://.+\.jpg',
            'timestamp': 1670459604.0,
            'uploader_id': 'CTVJLaidlaw',
            'uploader': 'Jocelyn Laidlaw',
            'repost_count': int,
            'comment_count': int,
            'tags': ['colorectalcancer', 'cancerjourney', 'imnotaquitter'],
            'duration': 102.226,
            'uploader_url': 'https://twitter.com/CTVJLaidlaw',
            'display_id': '1600649710662213632',
            'like_count': int,
            'view_count': int,
            'description': 'md5:591c19ce66fadc2359725d5cd0d1052c',
            'upload_date': '20221208',
            'age_limit': 0,
        },
        'params': {'noplaylist': True},
    }, {
        # id pointing to TweetWithVisibilityResults type entity which wraps the actual Tweet over
        # note the id different between extraction and url
        'url': 'https://twitter.com/s2FAKER/status/1621117700482416640',
        'info_dict': {
            'id': '1621117577354424321',
            'display_id': '1621117700482416640',
            'ext': 'mp4',
            'title': '뽀 - 아 최우제 이동속도 봐',
            'description': '아 최우제 이동속도 봐 https://t.co/dxu2U5vXXB',
            'duration': 24.598,
            'uploader': '뽀',
            'uploader_id': 's2FAKER',
            'uploader_url': 'https://twitter.com/s2FAKER',
            'upload_date': '20230202',
            'timestamp': 1675339553.0,
            'thumbnail': r're:https?://pbs\.twimg\.com/.+',
            'age_limit': 18,
            'tags': [],
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'view_count': int,
        },
    }, {
        'url': 'https://twitter.com/hlo_again/status/1599108751385972737/video/2',
        'info_dict': {
            'id': '1599108643743473680',
            'display_id': '1599108751385972737',
            'ext': 'mp4',
            'title': '\u06ea - \U0001F48B',
            'uploader_url': 'https://twitter.com/hlo_again',
            'like_count': int,
            'uploader_id': 'hlo_again',
            'thumbnail': 'https://pbs.twimg.com/ext_tw_video_thumb/1599108643743473680/pu/img/UG3xjov4rgg5sbYM.jpg?name=orig',
            'repost_count': int,
            'duration': 9.531,
            'comment_count': int,
            'view_count': int,
            'upload_date': '20221203',
            'age_limit': 0,
            'timestamp': 1670092210.0,
            'tags': [],
            'uploader': '\u06ea',
            'description': '\U0001F48B https://t.co/bTj9Qz7vQP',
        },
        'params': {'noplaylist': True},
    }, {
        'url': 'https://twitter.com/MunTheShinobi/status/1600009574919962625',
        'info_dict': {
            'id': '1600009362759733248',
            'display_id': '1600009574919962625',
            'ext': 'mp4',
            'uploader_url': 'https://twitter.com/MunTheShinobi',
            'description': 'This is a genius ad by Apple. \U0001f525\U0001f525\U0001f525\U0001f525\U0001f525 https://t.co/cNsA0MoOml',
            'view_count': int,
            'thumbnail': 'https://pbs.twimg.com/ext_tw_video_thumb/1600009362759733248/pu/img/XVhFQivj75H_YxxV.jpg?name=orig',
            'age_limit': 0,
            'uploader': 'Mün',
            'repost_count': int,
            'upload_date': '20221206',
            'title': 'Mün - This is a genius ad by Apple. \U0001f525\U0001f525\U0001f525\U0001f525\U0001f525',
            'comment_count': int,
            'like_count': int,
            'tags': [],
            'uploader_id': 'MunTheShinobi',
            'duration': 139.987,
            'timestamp': 1670306984.0,
        },
    }, {
        # retweeted_status (private)
        'url': 'https://twitter.com/liberdalau/status/1623739803874349067',
        'info_dict': {
            'id': '1623274794488659969',
            'display_id': '1623739803874349067',
            'ext': 'mp4',
            'title': 'Johnny Bullets - Me after going viral to over 30million people:    Whoopsie-daisy',
            'description': 'md5:b06864cd3dc2554821cc327f5348485a',
            'uploader': 'Johnny Bullets',
            'uploader_id': 'Johnnybull3ts',
            'uploader_url': 'https://twitter.com/Johnnybull3ts',
            'age_limit': 0,
            'tags': [],
            'duration': 8.033,
            'timestamp': 1675853859.0,
            'upload_date': '20230208',
            'thumbnail': r're:https://pbs\.twimg\.com/ext_tw_video_thumb/.+',
            'like_count': int,
            'repost_count': int,
        },
        'skip': 'Protected tweet',
    }, {
        # retweeted_status
        'url': 'https://twitter.com/playstrumpcard/status/1695424220702888009',
        'info_dict': {
            'id': '1694928337846538240',
            'ext': 'mp4',
            'display_id': '1695424220702888009',
            'title': 'md5:e8daa9527bc2b947121395494f786d9d',
            'description': 'md5:004f2d37fd58737724ec75bc7e679938',
            'uploader': 'Benny Johnson',
            'uploader_id': 'bennyjohnson',
            'uploader_url': 'https://twitter.com/bennyjohnson',
            'age_limit': 0,
            'tags': [],
            'duration': 45.001,
            'timestamp': 1692962814.0,
            'upload_date': '20230825',
            'thumbnail': r're:https://pbs\.twimg\.com/amplify_video_thumb/.+',
            'like_count': int,
            'repost_count': int,
            'view_count': int,
            'comment_count': int,
        },
    }, {
        # retweeted_status w/ legacy API
        'url': 'https://twitter.com/playstrumpcard/status/1695424220702888009',
        'info_dict': {
            'id': '1694928337846538240',
            'ext': 'mp4',
            'display_id': '1695424220702888009',
            'title': 'md5:e8daa9527bc2b947121395494f786d9d',
            'description': 'md5:004f2d37fd58737724ec75bc7e679938',
            'uploader': 'Benny Johnson',
            'uploader_id': 'bennyjohnson',
            'uploader_url': 'https://twitter.com/bennyjohnson',
            'age_limit': 0,
            'tags': [],
            'duration': 45.001,
            'timestamp': 1692962814.0,
            'upload_date': '20230825',
            'thumbnail': r're:https://pbs\.twimg\.com/amplify_video_thumb/.+',
            'like_count': int,
            'repost_count': int,
        },
        'params': {'extractor_args': {'twitter': {'api': ['legacy']}}},
    }, {
        # Broadcast embedded in tweet
        'url': 'https://twitter.com/JessicaDobsonWX/status/1693057346933600402',
        'info_dict': {
            'id': '1yNGaNLjEblJj',
            'ext': 'mp4',
            'title': 'Jessica Dobson - WAVE Weather Now - Saturday 8/19/23 Update',
            'uploader': 'Jessica Dobson',
            'uploader_id': '1DZEoDwDovRQa',
            'thumbnail': r're:^https?://.*\.jpg',
            'view_count': int,
        },
        'add_ie': ['TwitterBroadcast'],
    }, {
        # Animated gif and quote tweet video, with syndication API
        'url': 'https://twitter.com/BAKKOOONN/status/1696256659889565950',
        'playlist_mincount': 2,
        'info_dict': {
            'id': '1696256659889565950',
            'title': 'BAKOON - https://t.co/zom968d0a0',
            'description': 'https://t.co/zom968d0a0',
            'tags': [],
            'uploader': 'BAKOON',
            'uploader_id': 'BAKKOOONN',
            'uploader_url': 'https://twitter.com/BAKKOOONN',
            'age_limit': 18,
            'timestamp': 1693254077.0,
            'upload_date': '20230828',
            'like_count': int,
        },
        'params': {'extractor_args': {'twitter': {'api': ['syndication']}}},
        'expected_warnings': ['Not all metadata'],
    }, {
        # onion route
        'url': 'https://twitter3e4tixl4xyajtrzo62zg5vztmjuricljdp2c5kshju4avyoid.onion/TwitterBlue/status/1484226494708662273',
        'only_matching': True,
    }, {
        # Twitch Clip Embed
        'url': 'https://twitter.com/GunB1g/status/1163218564784017422',
        'only_matching': True,
    }, {
        # promo_video_website card
        'url': 'https://twitter.com/GunB1g/status/1163218564784017422',
        'only_matching': True,
    }, {
        # promo_video_convo card
        'url': 'https://twitter.com/poco_dandy/status/1047395834013384704',
        'only_matching': True,
    }, {
        # appplayer card
        'url': 'https://twitter.com/poco_dandy/status/1150646424461176832',
        'only_matching': True,
    }, {
        # video_direct_message card
        'url': 'https://twitter.com/qarev001/status/1348948114569269251',
        'only_matching': True,
    }, {
        # poll2choice_video card
        'url': 'https://twitter.com/CAF_Online/status/1349365911120195585',
        'only_matching': True,
    }, {
        # poll3choice_video card
        'url': 'https://twitter.com/SamsungMobileSA/status/1348609186725289984',
        'only_matching': True,
    }, {
        # poll4choice_video card
        'url': 'https://twitter.com/SouthamptonFC/status/1347577658079641604',
        'only_matching': True,
    }]

    _MEDIA_ID_RE = re.compile(r'_video/(\d+)/')

    @property
    def _GRAPHQL_ENDPOINT(self):
        if self.is_logged_in:
            return 'zZXycP0V6H7m-2r0mOnFcA/TweetDetail'
        return '2ICDjqPd81tulZcYrtpTuQ/TweetResultByRestId'

    def _graphql_to_legacy(self, data, twid):
        result = traverse_obj(data, (
            'threaded_conversation_with_injections_v2', 'instructions', 0, 'entries',
            lambda _, v: v['entryId'] == f'tweet-{twid}', 'content', 'itemContent',
            'tweet_results', 'result', ('tweet', None), {dict},
        ), default={}, get_all=False) if self.is_logged_in else traverse_obj(
            data, ('tweetResult', 'result', {dict}), default={})

        if result.get('__typename') not in ('Tweet', 'TweetTombstone', 'TweetUnavailable', None):
            self.report_warning(f'Unknown typename: {result.get("__typename")}', twid, only_once=True)

        if 'tombstone' in result:
            cause = remove_end(traverse_obj(result, ('tombstone', 'text', 'text', {str})), '. Learn more')
            raise ExtractorError(f'Twitter API says: {cause or "Unknown error"}', expected=True)
        elif result.get('__typename') == 'TweetUnavailable':
            reason = result.get('reason')
            if reason == 'NsfwLoggedOut':
                self.raise_login_required('NSFW tweet requires authentication')
            elif reason == 'Protected':
                self.raise_login_required('You are not authorized to view this protected tweet')
            raise ExtractorError(reason or 'Requested tweet is unavailable', expected=True)

        status = result.get('legacy', {})
        status.update(traverse_obj(result, {
            'user': ('core', 'user_results', 'result', 'legacy'),
            'card': ('card', 'legacy'),
            'quoted_status': ('quoted_status_result', 'result', 'legacy'),
            'retweeted_status': ('legacy', 'retweeted_status_result', 'result', 'legacy'),
        }, expected_type=dict, default={}))

        # extra transformations needed since result does not match legacy format
        if status.get('retweeted_status'):
            status['retweeted_status']['user'] = traverse_obj(status, (
                'retweeted_status_result', 'result', 'core', 'user_results', 'result', 'legacy', {dict})) or {}

        binding_values = {
            binding_value.get('key'): binding_value.get('value')
            for binding_value in traverse_obj(status, ('card', 'binding_values', ..., {dict}))
        }
        if binding_values:
            status['card']['binding_values'] = binding_values

        return status

    def _build_graphql_query(self, media_id):
        return {
            'variables': {
                'focalTweetId': media_id,
                'includePromotedContent': True,
                'with_rux_injections': False,
                'withBirdwatchNotes': True,
                'withCommunity': True,
                'withDownvotePerspective': False,
                'withQuickPromoteEligibilityTweetFields': True,
                'withReactionsMetadata': False,
                'withReactionsPerspective': False,
                'withSuperFollowsTweetFields': True,
                'withSuperFollowsUserFields': True,
                'withV2Timeline': True,
                'withVoice': True,
            },
            'features': {
                'graphql_is_translatable_rweb_tweet_is_translatable_enabled': False,
                'interactive_text_enabled': True,
                'responsive_web_edit_tweet_api_enabled': True,
                'responsive_web_enhance_cards_enabled': True,
                'responsive_web_graphql_timeline_navigation_enabled': False,
                'responsive_web_text_conversations_enabled': False,
                'responsive_web_uc_gql_enabled': True,
                'standardized_nudges_misinfo': True,
                'tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled': False,
                'tweetypie_unmention_optimization_enabled': True,
                'unified_cards_ad_metadata_container_dynamic_card_content_query_enabled': True,
                'verified_phone_label_enabled': False,
                'vibe_api_enabled': True,
            },
        } if self.is_logged_in else {
            'variables': {
                'tweetId': media_id,
                'withCommunity': False,
                'includePromotedContent': False,
                'withVoice': False,
            },
            'features': {
                'creator_subscriptions_tweet_preview_api_enabled': True,
                'tweetypie_unmention_optimization_enabled': True,
                'responsive_web_edit_tweet_api_enabled': True,
                'graphql_is_translatable_rweb_tweet_is_translatable_enabled': True,
                'view_counts_everywhere_api_enabled': True,
                'longform_notetweets_consumption_enabled': True,
                'responsive_web_twitter_article_tweet_consumption_enabled': False,
                'tweet_awards_web_tipping_enabled': False,
                'freedom_of_speech_not_reach_fetch_enabled': True,
                'standardized_nudges_misinfo': True,
                'tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled': True,
                'longform_notetweets_rich_text_read_enabled': True,
                'longform_notetweets_inline_media_enabled': True,
                'responsive_web_graphql_exclude_directive_enabled': True,
                'verified_phone_label_enabled': False,
                'responsive_web_media_download_video_enabled': False,
                'responsive_web_graphql_skip_user_profile_image_extensions_enabled': False,
                'responsive_web_graphql_timeline_navigation_enabled': True,
                'responsive_web_enhance_cards_enabled': False
            },
            'fieldToggles': {
                'withArticleRichContentState': False
            }
        }

    def _extract_status(self, twid):
        if self.is_logged_in or self._selected_api == 'graphql':
            status = self._graphql_to_legacy(self._call_graphql_api(self._GRAPHQL_ENDPOINT, twid), twid)

        elif self._selected_api == 'legacy':
            status = self._call_api(f'statuses/show/{twid}.json', twid, {
                'cards_platform': 'Web-12',
                'include_cards': 1,
                'include_reply_count': 1,
                'include_user_entities': 0,
                'tweet_mode': 'extended',
            })

        elif self._selected_api == 'syndication':
            self.report_warning(
                'Not all metadata or media is available via syndication endpoint', twid, only_once=True)
            status = self._download_json(
                'https://cdn.syndication.twimg.com/tweet-result', twid, 'Downloading syndication JSON',
                headers={'User-Agent': 'Googlebot'}, query={
                    'id': twid,
                    # TODO: token = ((Number(twid) / 1e15) * Math.PI).toString(36).replace(/(0+|\.)/g, '')
                    'token': ''.join(random.choices('123456789abcdefghijklmnopqrstuvwxyz', k=10)),
                })
            if not status:
                raise ExtractorError('Syndication endpoint returned empty JSON response')
            # Transform the result so its structure matches that of legacy/graphql
            media = []
            for detail in traverse_obj(status, ((None, 'quoted_tweet'), 'mediaDetails', ..., {dict})):
                detail['id_str'] = traverse_obj(detail, (
                    'video_info', 'variants', ..., 'url', {self._MEDIA_ID_RE.search}, 1), get_all=False) or twid
                media.append(detail)
            status['extended_entities'] = {'media': media}

        else:
            raise ExtractorError(f'"{self._selected_api}" is not a valid API selection', expected=True)

        return traverse_obj(status, 'retweeted_status', None, expected_type=dict) or {}

    def _real_extract(self, url):
        twid, selected_index = self._match_valid_url(url).group('id', 'index')
        status = self._extract_status(twid)

        title = description = traverse_obj(
            status, (('full_text', 'text'), {lambda x: x.replace('\n', ' ')}), get_all=False) or ''
        # strip  'https -_t.co_BJYgOjSeGA' junk from filenames
        title = re.sub(r'\s+(https?://[^ ]+)', '', title)
        user = status.get('user') or {}
        uploader = user.get('name')
        if uploader:
            title = f'{uploader} - {title}'
        uploader_id = user.get('screen_name')

        info = {
            'id': twid,
            'title': title,
            'description': description,
            'uploader': uploader,
            'timestamp': unified_timestamp(status.get('created_at')),
            'uploader_id': uploader_id,
            'uploader_url': format_field(uploader_id, None, 'https://twitter.com/%s'),
            'like_count': int_or_none(status.get('favorite_count')),
            'repost_count': int_or_none(status.get('retweet_count')),
            'comment_count': int_or_none(status.get('reply_count')),
            'age_limit': 18 if status.get('possibly_sensitive') else 0,
            'tags': traverse_obj(status, ('entities', 'hashtags', ..., 'text')),
        }

        def extract_from_video_info(media):
            media_id = traverse_obj(media, 'id_str', 'id', expected_type=str_or_none)
            self.write_debug(f'Extracting from video info: {media_id}')

            formats = []
            subtitles = {}
            for variant in traverse_obj(media, ('video_info', 'variants', ...)):
                fmts, subs = self._extract_variant_formats(variant, twid)
                subtitles = self._merge_subtitles(subtitles, subs)
                formats.extend(fmts)

            thumbnails = []
            media_url = media.get('media_url_https') or media.get('media_url')
            if media_url:
                def add_thumbnail(name, size):
                    thumbnails.append({
                        'id': name,
                        'url': update_url_query(media_url, {'name': name}),
                        'width': int_or_none(size.get('w') or size.get('width')),
                        'height': int_or_none(size.get('h') or size.get('height')),
                    })
                for name, size in media.get('sizes', {}).items():
                    add_thumbnail(name, size)
                add_thumbnail('orig', media.get('original_info') or {})

            return {
                'id': media_id,
                'formats': formats,
                'subtitles': subtitles,
                'thumbnails': thumbnails,
                'view_count': traverse_obj(media, ('mediaStats', 'viewCount', {int_or_none})),
                'duration': float_or_none(traverse_obj(media, ('video_info', 'duration_millis')), 1000),
                # The codec of http formats are unknown
                '_format_sort_fields': ('res', 'br', 'size', 'proto'),
            }

        def extract_from_card_info(card):
            if not card:
                return

            self.write_debug(f'Extracting from card info: {card.get("url")}')
            binding_values = card['binding_values']

            def get_binding_value(k):
                o = binding_values.get(k) or {}
                return try_get(o, lambda x: x[x['type'].lower() + '_value'])

            card_name = card['name'].split(':')[-1]
            if card_name == 'player':
                yield {
                    '_type': 'url',
                    'url': get_binding_value('player_url'),
                }
            elif card_name == 'periscope_broadcast':
                yield {
                    '_type': 'url',
                    'url': get_binding_value('url') or get_binding_value('player_url'),
                    'ie_key': PeriscopeIE.ie_key(),
                }
            elif card_name == 'broadcast':
                yield {
                    '_type': 'url',
                    'url': get_binding_value('broadcast_url'),
                    'ie_key': TwitterBroadcastIE.ie_key(),
                }
            elif card_name == 'audiospace':
                yield {
                    '_type': 'url',
                    'url': f'https://twitter.com/i/spaces/{get_binding_value("id")}',
                    'ie_key': TwitterSpacesIE.ie_key(),
                }
            elif card_name == 'summary':
                yield {
                    '_type': 'url',
                    'url': get_binding_value('card_url'),
                }
            elif card_name == 'unified_card':
                unified_card = self._parse_json(get_binding_value('unified_card'), twid)
                yield from map(extract_from_video_info, traverse_obj(
                    unified_card, ('media_entities', ...), expected_type=dict))
            # amplify, promo_video_website, promo_video_convo, appplayer,
            # video_direct_message, poll2choice_video, poll3choice_video,
            # poll4choice_video, ...
            else:
                is_amplify = card_name == 'amplify'
                vmap_url = get_binding_value('amplify_url_vmap') if is_amplify else get_binding_value('player_stream_url')
                content_id = get_binding_value('%s_content_id' % (card_name if is_amplify else 'player'))
                formats, subtitles = self._extract_formats_from_vmap_url(vmap_url, content_id or twid)

                thumbnails = []
                for suffix in ('_small', '', '_large', '_x_large', '_original'):
                    image = get_binding_value('player_image' + suffix) or {}
                    image_url = image.get('url')
                    if not image_url or '/player-placeholder' in image_url:
                        continue
                    thumbnails.append({
                        'id': suffix[1:] if suffix else 'medium',
                        'url': image_url,
                        'width': int_or_none(image.get('width')),
                        'height': int_or_none(image.get('height')),
                    })

                yield {
                    'formats': formats,
                    'subtitles': subtitles,
                    'thumbnails': thumbnails,
                    'duration': int_or_none(get_binding_value(
                        'content_duration_seconds')),
                }

        videos = traverse_obj(status, (
            (None, 'quoted_status'), 'extended_entities', 'media', lambda _, m: m['type'] != 'photo', {dict}))

        if self._yes_playlist(twid, selected_index, video_label='URL-specified video number'):
            selected_entries = (*map(extract_from_video_info, videos), *extract_from_card_info(status.get('card')))
        else:
            desired_obj = traverse_obj(status, (
                (None, 'quoted_status'), 'extended_entities', 'media', int(selected_index) - 1, {dict}), get_all=False)
            if not desired_obj:
                raise ExtractorError(f'Video #{selected_index} is unavailable', expected=True)
            elif desired_obj.get('type') != 'video':
                raise ExtractorError(f'Media #{selected_index} is not a video', expected=True)

            # Restore original archive id and video index in title
            for index, entry in enumerate(videos, 1):
                if entry.get('id') != desired_obj.get('id'):
                    continue
                if index == 1:
                    info['_old_archive_ids'] = [make_archive_id(self, twid)]
                if len(videos) != 1:
                    info['title'] += f' #{index}'
                break

            return {**info, **extract_from_video_info(desired_obj), 'display_id': twid}

        entries = [{**info, **data, 'display_id': twid} for data in selected_entries]
        if not entries:
            expanded_url = traverse_obj(status, ('entities', 'urls', 0, 'expanded_url'), expected_type=url_or_none)
            if not expanded_url or expanded_url == url:
                self.raise_no_formats('No video could be found in this tweet', expected=True)
                return info

            return self.url_result(expanded_url, display_id=twid, **info)

        entries[0]['_old_archive_ids'] = [make_archive_id(self, twid)]

        if len(entries) == 1:
            return entries[0]

        for index, entry in enumerate(entries, 1):
            entry['title'] += f' #{index}'

        return self.playlist_result(entries, **info)


class TwitterAmplifyIE(TwitterBaseIE):
    IE_NAME = 'twitter:amplify'
    _VALID_URL = r'https?://amp\.twimg\.com/v/(?P<id>[0-9a-f\-]{36})'

    _TEST = {
        'url': 'https://amp.twimg.com/v/0ba0c3c7-0af3-4c0a-bed5-7efd1ffa2951',
        'md5': 'fec25801d18a4557c5c9f33d2c379ffa',
        'info_dict': {
            'id': '0ba0c3c7-0af3-4c0a-bed5-7efd1ffa2951',
            'ext': 'mp4',
            'title': 'Twitter Video',
            'thumbnail': 're:^https?://.*',
        },
        'params': {'format': '[protocol=https]'},
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        vmap_url = self._html_search_meta(
            'twitter:amplify:vmap', webpage, 'vmap url')
        formats, _ = self._extract_formats_from_vmap_url(vmap_url, video_id)

        thumbnails = []
        thumbnail = self._html_search_meta(
            'twitter:image:src', webpage, 'thumbnail', fatal=False)

        def _find_dimension(target):
            w = int_or_none(self._html_search_meta(
                'twitter:%s:width' % target, webpage, fatal=False))
            h = int_or_none(self._html_search_meta(
                'twitter:%s:height' % target, webpage, fatal=False))
            return w, h

        if thumbnail:
            thumbnail_w, thumbnail_h = _find_dimension('image')
            thumbnails.append({
                'url': thumbnail,
                'width': thumbnail_w,
                'height': thumbnail_h,
            })

        video_w, video_h = _find_dimension('player')
        formats[0].update({
            'width': video_w,
            'height': video_h,
        })

        return {
            'id': video_id,
            'title': 'Twitter Video',
            'formats': formats,
            'thumbnails': thumbnails,
        }


class TwitterBroadcastIE(TwitterBaseIE, PeriscopeBaseIE):
    IE_NAME = 'twitter:broadcast'
    _VALID_URL = TwitterBaseIE._BASE_REGEX + r'i/broadcasts/(?P<id>[0-9a-zA-Z]{13})'

    _TEST = {
        # untitled Periscope video
        'url': 'https://twitter.com/i/broadcasts/1yNGaQLWpejGj',
        'info_dict': {
            'id': '1yNGaQLWpejGj',
            'ext': 'mp4',
            'title': 'Andrea May Sahouri - Periscope Broadcast',
            'uploader': 'Andrea May Sahouri',
            'uploader_id': '1PXEdBZWpGwKe',
            'thumbnail': r're:^https?://[^?#]+\.jpg\?token=',
            'view_count': int,
        },
    }

    def _real_extract(self, url):
        broadcast_id = self._match_id(url)
        broadcast = self._call_api(
            'broadcasts/show.json', broadcast_id,
            {'ids': broadcast_id})['broadcasts'][broadcast_id]
        if not broadcast:
            raise ExtractorError('Broadcast no longer exists', expected=True)
        info = self._parse_broadcast_data(broadcast, broadcast_id)
        media_key = broadcast['media_key']
        source = self._call_api(
            f'live_video_stream/status/{media_key}', media_key)['source']
        m3u8_url = source.get('noRedirectPlaybackUrl') or source['location']
        if '/live_video_stream/geoblocked/' in m3u8_url:
            self.raise_geo_restricted()
        m3u8_id = compat_parse_qs(compat_urllib_parse_urlparse(
            m3u8_url).query).get('type', [None])[0]
        state, width, height = self._extract_common_format_info(broadcast)
        info['formats'] = self._extract_pscp_m3u8_formats(
            m3u8_url, broadcast_id, m3u8_id, state, width, height)
        return info


class TwitterSpacesIE(TwitterBaseIE):
    IE_NAME = 'twitter:spaces'
    _VALID_URL = TwitterBaseIE._BASE_REGEX + r'i/spaces/(?P<id>[0-9a-zA-Z]{13})'

    _TESTS = [{
        'url': 'https://twitter.com/i/spaces/1RDxlgyvNXzJL',
        'info_dict': {
            'id': '1RDxlgyvNXzJL',
            'ext': 'm4a',
            'title': 'King Carlo e la mossa Kansas City per fare il Grande Centro',
            'description': 'Twitter Space participated by annarita digiorgio, Signor Ernesto, Raffaello Colosimo, Simone M. Sepe',
            'uploader': r're:Lucio Di Gaetano.*?',
            'uploader_id': 'luciodigaetano',
            'live_status': 'was_live',
            'timestamp': 1659877956,
            'upload_date': '20220807',
            'release_timestamp': 1659904215,
            'release_date': '20220807',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # post_live/TimedOut but downloadable
        'url': 'https://twitter.com/i/spaces/1vAxRAVQWONJl',
        'info_dict': {
            'id': '1vAxRAVQWONJl',
            'ext': 'm4a',
            'title': 'Framing Up FinOps: Billing Tools',
            'description': 'Twitter Space participated by rupa, Alfonso Hernandez',
            'uploader': 'Google Cloud',
            'uploader_id': 'googlecloud',
            'live_status': 'post_live',
            'timestamp': 1681409554,
            'upload_date': '20230413',
            'release_timestamp': 1681839000,
            'release_date': '20230418',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # Needs ffmpeg as downloader, see: https://github.com/yt-dlp/yt-dlp/issues/7536
        'url': 'https://twitter.com/i/spaces/1eaKbrQbjoRKX',
        'info_dict': {
            'id': '1eaKbrQbjoRKX',
            'ext': 'm4a',
            'title': 'あ',
            'description': 'Twitter Space participated by nobody yet',
            'uploader': '息根とめる🔪Twitchで復活',
            'uploader_id': 'tomeru_ikinone',
            'live_status': 'was_live',
            'timestamp': 1685617198,
            'upload_date': '20230601',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    SPACE_STATUS = {
        'notstarted': 'is_upcoming',
        'ended': 'was_live',
        'running': 'is_live',
        'timedout': 'post_live',
    }

    def _build_graphql_query(self, space_id):
        return {
            'variables': {
                'id': space_id,
                'isMetatagsQuery': True,
                'withDownvotePerspective': False,
                'withReactionsMetadata': False,
                'withReactionsPerspective': False,
                'withReplays': True,
                'withSuperFollowsUserFields': True,
                'withSuperFollowsTweetFields': True,
            },
            'features': {
                'dont_mention_me_view_api_enabled': True,
                'interactive_text_enabled': True,
                'responsive_web_edit_tweet_api_enabled': True,
                'responsive_web_enhance_cards_enabled': True,
                'responsive_web_uc_gql_enabled': True,
                'spaces_2022_h2_clipping': True,
                'spaces_2022_h2_spaces_communities': False,
                'standardized_nudges_misinfo': True,
                'tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled': False,
                'vibe_api_enabled': True,
            },
        }

    def _real_extract(self, url):
        space_id = self._match_id(url)
        if not self.is_logged_in:
            self.raise_login_required('Twitter Spaces require authentication')
        space_data = self._call_graphql_api('HPEisOmj1epUNLCWTYhUWw/AudioSpaceById', space_id)['audioSpace']
        if not space_data:
            raise ExtractorError('Twitter Space not found', expected=True)

        metadata = space_data['metadata']
        live_status = try_call(lambda: self.SPACE_STATUS[metadata['state'].lower()])
        is_live = live_status == 'is_live'

        formats = []
        headers = {'Referer': 'https://twitter.com/'}
        if live_status == 'is_upcoming':
            self.raise_no_formats('Twitter Space not started yet', expected=True)
        elif not is_live and not metadata.get('is_space_available_for_replay'):
            self.raise_no_formats('Twitter Space ended and replay is disabled', expected=True)
        elif metadata.get('media_key'):
            source = traverse_obj(
                self._call_api(f'live_video_stream/status/{metadata["media_key"]}', metadata['media_key']),
                ('source', ('noRedirectPlaybackUrl', 'location'), {url_or_none}), get_all=False)
            formats = self._extract_m3u8_formats(  # XXX: Some Spaces need ffmpeg as downloader
                source, metadata['media_key'], 'm4a', entry_protocol='m3u8', live=is_live,
                headers=headers, fatal=False) if source else []
            for fmt in formats:
                fmt.update({'vcodec': 'none', 'acodec': 'aac'})
                if not is_live:
                    fmt['container'] = 'm4a_dash'

        participants = ', '.join(traverse_obj(
            space_data, ('participants', 'speakers', ..., 'display_name'))) or 'nobody yet'

        if not formats and live_status == 'post_live':
            self.raise_no_formats('Twitter Space ended but not downloadable yet', expected=True)

        return {
            'id': space_id,
            'title': metadata.get('title'),
            'description': f'Twitter Space participated by {participants}',
            'uploader': traverse_obj(
                metadata, ('creator_results', 'result', 'legacy', 'name')),
            'uploader_id': traverse_obj(
                metadata, ('creator_results', 'result', 'legacy', 'screen_name')),
            'live_status': live_status,
            'release_timestamp': try_call(
                lambda: int_or_none(metadata['scheduled_start'], scale=1000)),
            'timestamp': int_or_none(metadata.get('created_at'), scale=1000),
            'formats': formats,
            'http_headers': headers,
        }


class TwitterShortenerIE(TwitterBaseIE):
    IE_NAME = 'twitter:shortener'
    _VALID_URL = r'https?://t\.co/(?P<id>[^?#]+)|tco:(?P<eid>[^?#]+)'
    _BASE_URL = 'https://t.co/'

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        eid, id = mobj.group('eid', 'id')
        if eid:
            id = eid
            url = self._BASE_URL + id
        new_url = self._request_webpage(url, id, headers={'User-Agent': 'curl'}).url
        __UNSAFE_LINK = "https://twitter.com/safety/unsafe_link_warning?unsafe_link="
        if new_url.startswith(__UNSAFE_LINK):
            new_url = new_url.replace(__UNSAFE_LINK, "")
        return self.url_result(new_url)
