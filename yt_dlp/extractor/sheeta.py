import base64
import functools
import hashlib
import json
import random
import re
import string
import urllib.parse

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    filter_dict,
    get_domain,
    int_or_none,
    parse_qs,
    unified_timestamp,
    update_url_query,
    url_or_none,
    urlencode_postdata,
    urljoin,
)
from ..utils.traversal import traverse_obj


class SheetaEmbedIE(InfoExtractor):
    _NETRC_MACHINE = 'sheeta'
    IE_NAME = 'sheeta'
    IE_DESC = 'fan club system developed by DWANGO (ドワンゴ)'
    _VALID_URL = False
    _WEBPAGE_TESTS = [{
        'url': 'https://qlover.jp/doku/video/smy4caVHR6trSddiG9uCDiy4',
        'info_dict': {
            'id': 'smy4caVHR6trSddiG9uCDiy4',
            'title': '名取さなの毒にも薬にもならないラジオ#39',
            'ext': 'mp4',
            'channel': '名取さなの毒にも薬にもならないラジオ',
            'channel_id': 'qlover.jp/doku',
            'channel_url': 'https://qlover.jp/doku',
            'age_limit': 0,
            'live_status': 'not_live',
            'thumbnail': str,
            'description': 'md5:75c2143a59b4b70141b77ddb485991fd',
            'timestamp': 1711933200,
            'duration': 1872,
            'comment_count': int,
            'view_count': int,
            'tags': ['名取さな', 'どくラジ', '文化放送', 'ラジオ'],
            'upload_date': '20240401',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://itomiku-fc.jp/live/sm4P8x6oVPFBx59bNBGSgKoE',
        'info_dict': {
            'id': 'sm4P8x6oVPFBx59bNBGSgKoE',
            'title': '【3/9(土)14:00～】「all yours」美来の日SP♪',
            'ext': 'mp4',
            'channel': '伊藤美来 Official Fanclub 「all yours」',
            'channel_id': 'itomiku-fc.jp',
            'channel_url': 'https://itomiku-fc.jp',
            'age_limit': 0,
            'live_status': 'was_live',
            'thumbnail': str,
            'description': 'md5:80a6a14db30d8506f70bec6a28a6c4ad',
            'timestamp': 1709964399,
            'duration': 4542,
            'comment_count': int,
            'view_count': int,
            'tags': ['生放送', '生放送アーカイブ'],
            'upload_date': '20240309',
            'release_timestamp': 1709959800,
            'release_date': '20240309',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://canan8181.com/video/smxar9atjfNBn27bHhcTFLyg',
        'info_dict': {
            'id': 'smxar9atjfNBn27bHhcTFLyg',
            'title': '💛【7月】ドネートお礼しながら感想＆どきどきトーク【感想会】',
            'ext': 'mp4',
            'channel': 'Canan official fanclub',
            'channel_id': 'canan8181.com',
            'channel_url': 'https://canan8181.com',
            'age_limit': 15,
            'live_status': 'was_live',
            'thumbnail': str,
            'description': 'md5:0cd80e51da82dbb89deae5ea14aad24d',
            'timestamp': 1659182206,
            'duration': 6997,
            'comment_count': int,
            'view_count': int,
            'tags': ['安眠など♡アーカイブ＆動画（わらのおうちプラン以上）'],
            'upload_date': '20220730',
            'release_timestamp': 1659175200,
            'release_date': '20220730',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://11audee.jp/audio/smx3ebEZFRnHeaGzUzgi5A98',
        'info_dict': {
            'id': 'smx3ebEZFRnHeaGzUzgi5A98',
            'title': '#相坂湯 第38回 ロコムジカちゃんの歌唱についてモノ申す！？ ある意味レアな？鼻声坂くん！',
            'ext': 'm4a',
            'channel': '相坂優歌 湯上がり何飲む？',
            'channel_id': '11audee.jp',
            'channel_url': 'https://11audee.jp',
            'age_limit': 0,
            'live_status': 'not_live',
            'thumbnail': str,
            'description': 'md5:fdf881191f8057aa6af6042fc17fb94c',
            'timestamp': 1710860400,
            'duration': 631,
            'comment_count': int,
            'view_count': int,
            'tags': ['RADIO'],
            'upload_date': '20240319',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://hololive-fc.com/videos',
        'info_dict': {
            'id': 'hololive-fc.com/videos',
            'title': '旧ホロライブ公式ファンクラブ-videos',
            'age_limit': 0,
            'timestamp': 1715652389,
            'upload_date': '20240514',
        },
        'playlist_mincount': 12,
    }, {
        'url': 'https://tokinosora-fc.com/videos?vodType=1',
        'info_dict': {
            'id': 'tokinosora-fc.com/videos',
            'title': 'ときのそらオフィシャルファンクラブ-videos',
            'age_limit': 0,
            'timestamp': 1715652399,
            'upload_date': '20240514',
        },
        'playlist_mincount': 18,
    }, {
        'url': 'https://01audee.jp/videos?tag=RADIO&vodType=1&sort=display_date',
        'info_dict': {
            'id': '01audee.jp/videos',
            'title': '大熊和奏 朝のささやき-videos',
            'age_limit': 0,
            'timestamp': 1715652369,
            'upload_date': '20240514',
        },
        'playlist_mincount': 6,
    }, {
        'url': 'https://qlover.jp/bokuao/lives',
        'info_dict': {
            'id': 'qlover.jp/bokuao/lives',
            'title': '僕が見たかった青空の 「青天のヘキレキ！」-lives',
            'age_limit': 0,
            'timestamp': 1715652429,
            'upload_date': '20240514',
        },
        'playlist_mincount': 1,
    }, {
        'url': 'https://06audee.jp/lives',
        'info_dict': {
            'id': '06audee.jp/lives',
            'title': '田中ちえ美のたなかのカナタ！-lives',
            'age_limit': 0,
            'timestamp': 1715652369,
            'upload_date': '20240514',
        },
        'playlist_mincount': 5,
    }]

    _DOMAIN = None
    _API_BASE_URL = None
    _FANCLUB_GROUP_ID = None
    _FANCLUB_SITE_ID_AUTH = None
    _FANCLUB_SITE_ID_INFO = None
    _AUTH_INFO = {}

    _AUTH0_BASE64_TRANS = str.maketrans({
        '+': '-',
        '/': '_',
        '=': None,
    })
    _LIST_PAGE_SIZE = 12

    def _extract_from_url(self, url):
        parsed_url = urllib.parse.urlparse(url)
        if '/videos' in parsed_url.path:
            return self._extract_video_list_page(url)
        elif '/lives' in parsed_url.path:
            return self._extract_live_list_page(url)
        else:
            return self._extract_player_page(url)

    def _extract_from_webpage(self, url, webpage):
        if 'GTM-KXT7G5G' in webpage or 'NicoGoogleTagManagerDataLayer' in webpage:
            yield self._extract_from_url(url)
            raise self.StopExtraction

    def _call_api(self, path, item_id, *args, **kwargs):
        return self._download_json(f'{self._API_BASE_URL}/{path}', item_id, *args, **kwargs)

    def _find_fanclub_site_id(self, channel_id):
        fanclub_list_json = self._call_api(
            'content_providers/channel_domain', f'channels/{channel_id}',
            query={'current_site_domain': urllib.parse.quote(f'https://{self._DOMAIN}/{channel_id}')},
            note='Fetching channel list', errnote='Unable to fetch channel list',
        )
        if fanclub_id := traverse_obj(
                fanclub_list_json, ('data', 'content_providers', 'id', {int_or_none}), get_all=False):
            return fanclub_id
        raise ExtractorError(f'Channel {channel_id} does not exist', expected=True)

    def _extract_base_info(self, channel_id):
        site_settings = self._download_json(
            f'https://{self._DOMAIN}/site/settings.json', None,
            note='Fetching site settings', errnote='Unable to fetch site settings')
        self.write_debug(f'site_settings = {site_settings!r}')

        self._API_BASE_URL = site_settings['api_base_url']
        self._FANCLUB_GROUP_ID = site_settings['fanclub_group_id']
        self._FANCLUB_SITE_ID_AUTH = site_settings['fanclub_site_id']

        if channel_id:
            self._FANCLUB_SITE_ID_INFO = self._find_fanclub_site_id(channel_id)
        else:
            self._FANCLUB_SITE_ID_INFO = self._FANCLUB_SITE_ID_AUTH

    @property
    def _auth_info(self):
        if not self._AUTH_INFO.get(self._DOMAIN):
            self._AUTH_INFO[self._DOMAIN] = {}
        return self._AUTH_INFO.get(self._DOMAIN)

    @_auth_info.setter
    def _auth_info(self, value):
        if not self._AUTH_INFO.get(self._DOMAIN):
            self._AUTH_INFO[self._DOMAIN] = {}
        self._AUTH_INFO[self._DOMAIN].update(value)

    @property
    def _channel_base_info(self):
        return traverse_obj(self._call_api(
            f'fanclub_sites/{self._FANCLUB_SITE_ID_INFO}/page_base_info', f'fanclub_sites/{self._FANCLUB_SITE_ID_INFO}',
            note='Fetching channel base info', errnote='Unable to fetch channel base info', fatal=False,
        ), ('data', 'fanclub_site', {dict})) or {}

    @property
    def _channel_user_info(self):
        return traverse_obj(self._call_api(
            f'fanclub_sites/{self._FANCLUB_SITE_ID_INFO}/user_info', f'fanclub_sites/{self._FANCLUB_SITE_ID_INFO}',
            note='Fetching channel user info', errnote='Unable to fetch channel user info', fatal=False,
            data=json.dumps('null').encode(),
        ), ('data', 'fanclub_site', {dict})) or {}

    def _extract_channel_info(self, channel_id):
        if channel_id:
            full_channel_id = f'{self._DOMAIN}/{channel_id}'
            channel_url = f'https://{self._DOMAIN}/{channel_id}'
        else:
            full_channel_id = self._DOMAIN
            channel_url = f'https://{self._DOMAIN}'

        return {
            'channel': self._channel_base_info.get('fanclub_site_name'),
            'channel_id': full_channel_id,
            'channel_url': channel_url,
            'age_limit': traverse_obj(self._channel_user_info, (
                'content_provider', 'age_limit', {int_or_none})),
        }

    def _extract_player_page(self, url):
        self._DOMAIN, channel_id, content_code = re.match(
            r'https?://(?P<domain>[\w.-]+)(/(?P<channel>[\w.-]+))?/(?:live|video|audio)/(?P<code>sm\w+)', url,
        ).group('domain', 'channel', 'code')
        self._extract_base_info(channel_id)

        data_json = self._call_api(
            f'video_pages/{content_code}', content_code, headers={'fc_use_device': 'null'},
            note='Fetching video page info', errnote='Unable to fetch video page info',
        )['data']['video_page']

        live_status = self._get_live_status(data_json, content_code)
        formats = self._get_formats(data_json, live_status, content_code)
        release_timestamp_str = data_json.get('live_scheduled_start_at')

        if live_status == 'is_upcoming':
            if release_timestamp_str:
                msg = f'This live event will begin at {release_timestamp_str} UTC'
            else:
                msg = 'This event has not started yet'
            self.raise_no_formats(msg, expected=True, video_id=content_code)

        return {
            'id': content_code,
            'formats': formats,
            'live_status': live_status,
            'release_timestamp': unified_timestamp(release_timestamp_str),
            **self._extract_channel_info(channel_id),
            **traverse_obj(data_json, {
                'title': ('title', {str}),
                'thumbnail': ('thumbnail_url', {url_or_none}),
                'description': ('description', {str}),
                'timestamp': ('display_date', {unified_timestamp}),
                'duration': ('active_video_filename', 'length', {int_or_none}),
                'comment_count': ('video_aggregate_info', 'number_of_comments', {int_or_none}),
                'view_count': ('video_aggregate_info', 'total_views', {int_or_none}),
                'tags': ('video_tags', ..., 'tag', {str}),
            }),
            '__post_extractor': self.extract_comments(
                content_code=content_code,
                comment_group_id=traverse_obj(data_json, ('video_comment_setting', 'comment_group_id'))),
        }

    def _get_comments(self, content_code, comment_group_id):
        item_id = f'{content_code}/comments'

        if not comment_group_id:
            return None

        comment_access_token = self._call_api(
            f'video_pages/{content_code}/comments_user_token', item_id,
            note='Getting comment token', errnote='Unable to get comment token',
        )['data']['access_token']

        comment_list, urlh = self._download_json_handle(
            'https://comm-api.sheeta.com/messages.history', video_id=item_id,
            note='Fetching comments', errnote='Unable to fetch comments',
            headers={'Content-Type': 'application/json'}, expected_status=404,
            query={
                'sort_direction': 'asc',
                'limit': int_or_none(self._configuration_arg('max_comments', [''])[0]) or 120,
            },
            data=json.dumps({
                'token': comment_access_token,
                'group_id': comment_group_id,
            }).encode())
        if urlh.status == 404:
            self.report_warning('Unable to fetch comments due to rate limit', content_code)
            return

        for comment in traverse_obj(comment_list, ...):
            yield traverse_obj(comment, {
                'author': ('nickname', {str}),
                'author_id': ('sender_id', {str}),
                'id': ('id', {str}, {lambda x: x or None}),
                'text': ('message', {str}),
                'timestamp': (('updated_at', 'sent_at', 'created_at'), {unified_timestamp}),
                'author_is_uploader': ('sender_id', {lambda x: x == '-1'}),
            }, get_all=False)

    def _get_live_status(self, data_json, content_code):
        video_type = data_json.get('type')
        live_finished_at = data_json.get('live_finished_at')

        if video_type == 'vod':
            if live_finished_at:
                live_status = 'was_live'
            else:
                live_status = 'not_live'
        elif video_type == 'live':
            if not data_json.get('live_started_at'):
                return 'is_upcoming'

            if not live_finished_at:
                live_status = 'is_live'
            else:
                live_status = 'was_live'

                video_allow_dvr_flg = traverse_obj(data_json, ('video', 'allow_dvr_flg'))
                video_convert_to_vod_flg = traverse_obj(data_json, ('video', 'convert_to_vod_flg'))

                self.write_debug(
                    f'{content_code}: allow_dvr_flg = {video_allow_dvr_flg}, convert_to_vod_flg = {video_convert_to_vod_flg}.')

                if not (video_allow_dvr_flg and video_convert_to_vod_flg):
                    raise ExtractorError(
                        'Live was ended, there is no video for download', video_id=content_code, expected=True)
        else:
            raise ExtractorError(f'Unknown type: {video_type!r}', video_id=content_code)

        self.write_debug(f'{content_code}: video_type={video_type}, live_status={live_status}')
        return live_status

    def _get_authed_info(self, query_path, item_id, dict_path, expected_code_msg, **query_kwargs):
        try:
            res = self._call_api(query_path, item_id, **query_kwargs)
            return traverse_obj(res, dict_path)
        except ExtractorError as e:
            if not isinstance(e.cause, HTTPError) or e.cause.status not in expected_code_msg:
                raise e
            self.raise_login_required(
                expected_code_msg[e.cause.status], metadata_available=True,
                method=self._auth_info.get('login_method'))
            return None

    def _get_formats(self, data_json, live_status, content_code):
        headers = filter_dict({
            'Content-Type': 'application/json',
            'fc_use_device': 'null',
            'origin': f'https://{self._DOMAIN}',
            'Authorization': self._get_auth_token(),
        })

        formats = []
        if data_json.get('video'):
            payload = {}
            if data_json.get('type') == 'live' and live_status == 'was_live':
                payload = {'broadcast_type': 'dvr'}

            session_id = self._get_authed_info(
                f'video_pages/{content_code}/session_ids', f'{content_code}/session',
                ('data', 'session_id', {str}), {
                    401: 'Members-only content',
                    403: 'Login required',
                    408: 'Outdated token',
                }, data=json.dumps(payload).encode(), headers=headers,
                note='Getting session id', errnote='Unable to get session id')

            if session_id:
                m3u8_url = data_json['video_stream']['authenticated_url'].format(session_id=session_id)
                formats = self._extract_m3u8_formats(m3u8_url, content_code)
        elif data_json.get('audio'):
            m3u8_url = self._get_authed_info(
                f'video_pages/{content_code}/content_access', f'{content_code}/content_access',
                ('data', 'resource', {url_or_none}), {
                    403: 'Login required',
                    404: 'Members-only content',
                    408: 'Outdated token',
                }, headers=headers, note='Getting content resource',
                errnote='Unable to get content resource')

            if m3u8_url:
                audio_type = traverse_obj(data_json, (
                    'audio_filename_transcoded_list', lambda _, v: v['url'] == m3u8_url,
                    'video_filename_type', 'value', {str}), get_all=False)
                if audio_type == 'audio_free':
                    # fully free audios are always of "audio_paid"
                    msg = 'You have no right to access the paid content. '
                    if traverse_obj(data_json, 'video_free_periods'):
                        msg += 'There may be some silent parts in this audio'
                    else:
                        msg += 'This audio may be completely blank'
                    self.raise_login_required(
                        msg, metadata_available=True, method=self._auth_info.get('login_method'))

                formats = [{
                    'url': m3u8_url,
                    'format_id': 'audio',
                    'protocol': 'm3u8_native',
                    'ext': 'm4a',
                    'vcodec': 'none',
                    'acodec': 'aac',
                    'format_note': audio_type,
                }]
        else:
            raise ExtractorError('Unknown media type', video_id=content_code)

        return formats

    def _get_auth_token(self):
        if not self._auth_info.get('auth_token'):
            try:
                self._login()
                return self._auth_info.get('auth_token')
            except Exception as e:
                raise ExtractorError('Unable to login due to unknown reasons') from e

        if self._auth_info.get('auth_token'):
            try:
                self._refresh_token()
                return self._auth_info.get('auth_token')
            except Exception as e:
                raise ExtractorError('Unable to refresh token due to unknown reasons') from e

        return None

    def _refresh_token(self):
        if not (refresh_func := self._auth_info.get('refresh_func')):
            return False

        res = self._download_json(
            **refresh_func(self._auth_info), expected_status=(400, 403, 404),
            note='Refreshing token', errnote='Unable to refresh token')
        if error := traverse_obj(
                res, ('error', 'message', {lambda x: base64.b64decode(x).decode()}), ('error', 'message')):
            self.report_warning(f'Unable to refresh token: {error!r}')
        elif token := traverse_obj(res, ('data', 'access_token', {str})):
            # niconico
            self._auth_info = {'auth_token': f'Bearer {token}'}
            return True
        elif token := traverse_obj(res, ('access_token', {str})):
            # auth0
            self._auth_info = {'auth_token': f'Bearer {token}'}
            if refresh_token := traverse_obj(res, ('refresh_token', {str})):
                self._auth_info = {'refresh_token': refresh_token}
                self.cache.store(
                    self._NETRC_MACHINE, self._auth_info['cache_key'], {self._auth_info['cache_name']: refresh_token})
                return True
            self.report_warning('Unable to find new refresh_token')
        else:
            self.report_warning('Unable to refresh token')

        return False

    def _login(self):
        social_login_providers = traverse_obj(self._call_api(
            f'fanclub_groups/{self._FANCLUB_GROUP_ID}/login', None),
            ('data', 'fanclub_group', 'fanclub_social_login_providers', ..., {dict})) or []
        self.write_debug(f'social_login_providers = {social_login_providers!r}')

        for provider in social_login_providers:
            provider_name = traverse_obj(provider, ('social_login_provider', 'provider_name', {str}))
            if provider_name == 'ニコニコ':
                redirect_url = update_url_query(provider['url'], {
                    'client_id': 'FCS{:05d}'.format(provider['id']),
                    'redirect_uri': f'https://{self._DOMAIN}/login',
                })
                refresh_url = f'{self._API_BASE_URL}/fanclub_groups/{self._FANCLUB_GROUP_ID}/auth/refresh'
                return self._niconico_sns_login(redirect_url, refresh_url)
            else:
                raise ExtractorError(f'Unsupported social login provider: {provider_name}')

        return self._auth0_login()

    def _niconico_sns_login(self, redirect_url, refresh_url):
        self._auth_info = {'login_method': 'any'}
        mail_tel, password = self._get_login_info()
        if not mail_tel:
            return

        cache_key = hashlib.sha1(f'{self._DOMAIN}:{mail_tel}:{password}'.encode()).hexdigest()
        self._auth_info = {'cache_key': cache_key}
        cache_name = 'niconico_sns'

        if cached_cookies := traverse_obj(self.cache.load(
                self._NETRC_MACHINE, cache_key), (cache_name, {dict})):
            for name, value in cached_cookies.items():
                self._set_cookie(get_domain(redirect_url), name, value)

        if not (auth_token := self._niconico_get_token_by_cookies(redirect_url)):
            if cached_cookies:
                self.cache.store(self._NETRC_MACHINE, cache_key, None)

            self._niconico_login(mail_tel, password)

            if not (auth_token := self._niconico_get_token_by_cookies(redirect_url)):
                self.report_warning('Unable to get token after login, please check if '
                                    'niconico channel plus is authorized to use your niconico account')
                return

        self._auth_info = {
            'refresh_func': lambda data: {
                'url_or_request': data['refresh_url'],
                'video_id': None,
                'headers': {'Authorization': data['auth_token']},
                'data': b'',
            },
            'refresh_url': refresh_url,
            'auth_token': auth_token,
        }

        cookies = dict(traverse_obj(self.cookiejar.get_cookies_for_url(
            redirect_url), (..., {lambda item: (item.name, item.value)})))
        self.cache.store(self._NETRC_MACHINE, cache_key, {cache_name: cookies})

    def _niconico_get_token_by_cookies(self, redirect_url):
        urlh = self._request_webpage(
            redirect_url, None, note='Getting niconico auth status',
            expected_status=404, errnote='Unable to get niconico auth status')
        if not urlh.url.startswith(f'https://{self._DOMAIN}/login'):
            return None

        if not (sns_login_code := traverse_obj(parse_qs(urlh.url), ('code', 0))):
            self.report_warning('Unable to get sns login code')
            return None

        token = traverse_obj(self._call_api(
            f'fanclub_groups/{self._FANCLUB_GROUP_ID}/sns_login', None, fatal=False,
            note='Fetching sns login info', errnote='Unable to fetch sns login info',
            data=json.dumps({
                'key_cloak_user': {
                    'code': sns_login_code,
                    'redirect_uri': f'https://{self._DOMAIN}/login',
                },
                'fanclub_site': {'id': int(self._FANCLUB_SITE_ID_AUTH)},
            }).encode(), headers={
                'Content-Type': 'application/json',
                'fc_use_device': 'null',
                'Referer': f'https://{self._DOMAIN}',
            }), ('data', 'access_token', {str}))
        if token:
            return f'Bearer {token}'

        self.report_warning('Unable to get token from sns login info')
        return None

    def _niconico_login(self, mail_tel, password):
        login_form_strs = {
            'mail_tel': mail_tel,
            'password': password,
        }
        page, urlh = self._download_webpage_handle(
            'https://account.nicovideo.jp/login/redirector', None,
            note='Logging into niconico', errnote='Unable to log into niconico',
            data=urlencode_postdata(login_form_strs),
            headers={
                'Referer': 'https://account.nicovideo.jp/login',
                'Content-Type': 'application/x-www-form-urlencoded',
            })
        if urlh.url.startswith('https://account.nicovideo.jp/login'):
            self.report_warning('Unable to log in: bad username or password')
            return False
        elif urlh.url.startswith('https://account.nicovideo.jp/mfa'):
            post_url = self._search_regex(
                r'<form[^>]+action=(["\'])(?P<url>.+?)\1', page, 'mfa post url', group='url')
            page, urlh = self._download_webpage_handle(
                urljoin('https://account.nicovideo.jp/', post_url), None,
                note='Performing MFA', errnote='Unable to complete MFA',
                data=urlencode_postdata({
                    'otp': self._get_tfa_info('6 digits code'),
                }), headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                })
            if urlh.url.startswith('https://account.nicovideo.jp/mfa') or 'formError' in page:
                err_msg = self._html_search_regex(
                    r'formError\b[^>]*>(.*?)</div>', page, 'form_error',
                    default='There\'s an error but the message can\'t be parsed.',
                    flags=re.DOTALL)
                self.report_warning(f'Unable to log in: MFA challenge failed, "{err_msg}"')
                return False
        return True

    def _auth0_login(self):
        self._auth_info = {'login_method': 'password'}
        username, password = self._get_login_info()
        if not username:
            return

        cache_key = hashlib.sha1(f'{self._DOMAIN}:{username}:{password}'.encode()).hexdigest()
        cache_name = 'refresh'
        self._auth_info = {
            'cache_key': cache_key,
            'cache_name': cache_name,
        }

        login_info = self._call_api(f'fanclub_sites/{self._FANCLUB_SITE_ID_AUTH}/login', None)['data']['fanclub_site']
        self.write_debug(f'login_info = {login_info}')
        auth0_web_client_id = login_info['auth0_web_client_id']
        auth0_domain = login_info['fanclub_group']['auth0_domain']

        token_url = f'https://{auth0_domain}/oauth/token'
        redirect_url = f'https://{self._DOMAIN}/login/login-redirect'

        auth0_client = base64.b64encode(json.dumps({
            'name': 'auth0-spa-js',
            'version': '2.0.6',
        }).encode()).decode()

        self._auth_info = {'refresh_func': lambda data: {
            'url_or_request': token_url,
            'video_id': None,
            'headers': {'Auth0-Client': auth0_client},
            'data': urlencode_postdata({
                'client_id': auth0_web_client_id,
                'grant_type': 'refresh_token',
                'refresh_token': data['refresh_token'],
                'redirect_uri': redirect_url,
            }),
        }}

        def random_str():
            return ''.join(random.choices(string.digits + string.ascii_letters, k=43))

        state = base64.b64encode(random_str().encode())
        nonce = base64.b64encode(random_str().encode())
        code_verifier = random_str().encode()
        code_challenge = base64.b64encode(
            hashlib.sha256(code_verifier).digest()).decode().translate(self._AUTH0_BASE64_TRANS)

        authorize_url = update_url_query(f'https://{auth0_domain}/authorize', {
            'client_id': auth0_web_client_id,
            'scope': 'openid profile email offline_access',
            'redirect_uri': redirect_url,
            'audience': f'api.{self._DOMAIN}',
            'prompt': 'login',
            'response_type': 'code',
            'response_mode': 'query',
            'state': state,
            'nonce': nonce,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'auth0Client': auth0_client,
        })

        if cached_refresh_token := traverse_obj(self.cache.load(
                self._NETRC_MACHINE, cache_key), (cache_name, {str})):
            self._auth_info = {'refresh_token': cached_refresh_token}
            if self._refresh_token():
                self.write_debug('cached tokens updated')
                return
            self.cache.store(self._NETRC_MACHINE, cache_key, None)

        login_form = self._hidden_inputs(self._download_webpage(
            authorize_url, None, note='Getting login form', errnote='Unable to get login form'))
        state_obtained = login_form['state']
        login_url = f'https://{auth0_domain}/u/login?state={state_obtained}'

        login_form.update({
            'username': username,
            'password': password,
            'action': 'default',
        })

        urlh = self._request_webpage(
            login_url, None, note='Logging in', errnote='Unable to log in',
            data=urlencode_postdata(login_form), expected_status=(400, 404))
        if urlh.status == 400:
            self.report_warning('Unable to log in: bad username or password')
            return
        if not (urlh.status == 404 and urlh.url.startswith(redirect_url)):
            self.report_warning('Unable to log in: Unknown login status')
            return

        code = parse_qs(urlh.url)['code'][0]

        token_json = self._download_json(
            token_url, None, headers={'Auth0-Client': auth0_client},
            note='Getting auth0 tokens', errnote='Unable to get auth0 tokens',
            data=urlencode_postdata({
                'client_id': auth0_web_client_id,
                'code_verifier': code_verifier,
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': redirect_url,
            }))

        access_token = token_json['access_token']
        refresh_token = token_json['refresh_token']

        auth_token = f'Bearer {access_token}'

        self._auth_info = {
            'auth_token': auth_token,
            'refresh_token': refresh_token,
        }

        self.cache.store(self._NETRC_MACHINE, cache_key, {cache_name: refresh_token})

    def _fetch_paged_channel_video_list(self, path, query, channel, item_id, page):
        response = self._call_api(
            path, item_id, query={
                **query,
                'page': (page + 1),
                'per_page': self._LIST_PAGE_SIZE,
            },
            headers={'fc_use_device': 'null'},
            note=f'Fetching channel info (page {page + 1})',
            errnote=f'Unable to fetch channel info (page {page + 1})')

        for content_code in traverse_obj(
                response, ('data', 'video_pages', 'list', ..., 'content_code', {str})):
            yield self.url_result('/'.join(filter(
                None, [f'https://{self._DOMAIN}', channel, 'video', content_code])), SheetaEmbedIE)

    def _extract_video_list_page(self, url):
        """
        API parameters:
            sort:
                -display_date         公開日が新しい順 (newest to oldest)
                 display_date         公開日が古い順 (oldest to newest)
                -number_of_vod_views 再生数が多い順 (most play count)
                 number_of_vod_views コメントが多い順 (most comments)
            vod_type (is "vodType" in "url"):
                0 すべて (all)
                1 会員限定 (members only)
                2 一部無料 (partially free)
                3 レンタル (rental)
                4 生放送アーカイブ (live archives)
                5 アップロード動画 (uploaded videos)
                7 無料 (free)
        """

        self._DOMAIN, channel_id = re.match(
            r'https?://(?P<domain>[\w.-]+)(/(?P<channel>[\w.-]+))?/videos', url,
        ).group('domain', 'channel')
        self._extract_base_info(channel_id)

        channel_info = self._extract_channel_info(channel_id)
        full_channel_id = channel_info['channel_id']
        channel_name = channel_info['channel']
        qs = parse_qs(url)

        return self.playlist_result(
            OnDemandPagedList(
                functools.partial(
                    self._fetch_paged_channel_video_list, f'fanclub_sites/{self._FANCLUB_SITE_ID_INFO}/video_pages',
                    filter_dict({
                        'tag': traverse_obj(qs, ('tag', 0)),
                        'sort': traverse_obj(qs, ('sort', 0), default='-display_date'),
                        'vod_type': traverse_obj(qs, ('vodType', 0), default='0'),
                    }),
                    channel_id, f'{full_channel_id}/videos'),
                self._LIST_PAGE_SIZE),
            playlist_id=f'{full_channel_id}/videos', playlist_title=f'{channel_name}-videos')

    def _extract_live_list_page(self, url):
        """
        API parameters:
            live_type:
                1 放送中 (on air)
                2 放送予定 (scheduled live streams, oldest to newest)
                3 過去の放送 - すべて (all ended live streams, newest to oldest)
                4 過去の放送 - 生放送アーカイブ (all archives for live streams, oldest to newest)
            We use "4" instead of "3" because some recently ended live streams could not be downloaded.
        """

        self._DOMAIN, channel_id = re.match(
            r'https?://(?P<domain>[\w.-]+)(/(?P<channel>[\w.-]+))?/lives', url,
        ).group('domain', 'channel')
        self._extract_base_info(channel_id)

        channel_info = self._extract_channel_info(channel_id)
        full_channel_id = channel_info['channel_id']
        channel_name = channel_info['channel']

        return self.playlist_result(
            OnDemandPagedList(
                functools.partial(
                    self._fetch_paged_channel_video_list, f'fanclub_sites/{self._FANCLUB_SITE_ID_INFO}/live_pages',
                    {'live_type': 4}, channel_id, f'{full_channel_id}/lives'),
                self._LIST_PAGE_SIZE),
            playlist_id=f'{full_channel_id}/lives', playlist_title=f'{channel_name}-lives')
