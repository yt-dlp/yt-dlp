import datetime as dt
import functools
import itertools
import json
import re
import time
import urllib.parse

from .common import InfoExtractor, SearchInfoExtractor
from ..networking import Request
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    clean_html,
    determine_ext,
    float_or_none,
    int_or_none,
    join_nonempty,
    parse_duration,
    parse_iso8601,
    parse_qs,
    parse_resolution,
    qualities,
    remove_start,
    str_or_none,
    traverse_obj,
    try_get,
    unescapeHTML,
    unified_timestamp,
    update_url_query,
    url_basename,
    url_or_none,
    urlencode_postdata,
    urljoin,
)


class NiconicoIE(InfoExtractor):
    IE_NAME = 'niconico'
    IE_DESC = 'ニコニコ動画'
    _GEO_COUNTRIES = ['JP']
    _GEO_BYPASS = False

    _TESTS = [{
        'url': 'http://www.nicovideo.jp/watch/sm22312215',
        'info_dict': {
            'id': 'sm22312215',
            'ext': 'mp4',
            'title': 'Big Buck Bunny',
            'thumbnail': r're:https?://.*',
            'uploader': 'takuya0301',
            'uploader_id': '2698420',
            'upload_date': '20131123',
            'timestamp': int,  # timestamp is unstable
            'description': '(c) copyright 2008, Blender Foundation / www.bigbuckbunny.org',
            'duration': 33,
            'view_count': int,
            'comment_count': int,
            'genres': ['未設定'],
            'tags': [],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # File downloaded with and without credentials are different, so omit
        # the md5 field
        'url': 'http://www.nicovideo.jp/watch/nm14296458',
        'info_dict': {
            'id': 'nm14296458',
            'ext': 'mp4',
            'title': '【Kagamine Rin】Dance on media【Original】take2!',
            'description': 'md5:9368f2b1f4178de64f2602c2f3d6cbf5',
            'thumbnail': r're:https?://.*',
            'uploader': 'りょうた',
            'uploader_id': '18822557',
            'upload_date': '20110429',
            'timestamp': 1304065916,
            'duration': 208.0,
            'comment_count': int,
            'view_count': int,
            'genres': ['音楽・サウンド'],
            'tags': ['Translation_Request', 'Kagamine_Rin', 'Rin_Original'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # 'video exists but is marked as "deleted"
        # md5 is unstable
        'url': 'http://www.nicovideo.jp/watch/sm10000',
        'info_dict': {
            'id': 'sm10000',
            'ext': 'unknown_video',
            'description': 'deleted',
            'title': 'ドラえもんエターナル第3話「決戦第3新東京市」＜前編＞',
            'thumbnail': r're:https?://.*',
            'upload_date': '20071224',
            'timestamp': int,  # timestamp field has different value if logged in
            'duration': 304,
            'view_count': int,
        },
        'skip': 'Requires an account',
    }, {
        'url': 'http://www.nicovideo.jp/watch/so22543406',
        'info_dict': {
            'id': '1388129933',
            'ext': 'mp4',
            'title': '【第1回】RADIOアニメロミックス ラブライブ！～のぞえりRadio Garden～',
            'description': 'md5:b27d224bb0ff53d3c8269e9f8b561cf1',
            'thumbnail': r're:https?://.*',
            'timestamp': 1388851200,
            'upload_date': '20140104',
            'uploader': 'アニメロチャンネル',
            'uploader_id': '312',
        },
        'skip': 'The viewing period of the video you were searching for has expired.',
    }, {
        # video not available via `getflv`; "old" HTML5 video
        'url': 'http://www.nicovideo.jp/watch/sm1151009',
        'info_dict': {
            'id': 'sm1151009',
            'ext': 'mp4',
            'title': 'マスターシステム本体内蔵のスペハリのメインテーマ（ＰＳＧ版）',
            'description': 'md5:f95a3d259172667b293530cc2e41ebda',
            'thumbnail': r're:https?://.*',
            'duration': 184,
            'timestamp': 1190835883,
            'upload_date': '20070926',
            'uploader': 'denden2',
            'uploader_id': '1392194',
            'view_count': int,
            'comment_count': int,
            'genres': ['ゲーム'],
            'tags': [],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # "New" HTML5 video
        'url': 'http://www.nicovideo.jp/watch/sm31464864',
        'info_dict': {
            'id': 'sm31464864',
            'ext': 'mp4',
            'title': '新作TVアニメ「戦姫絶唱シンフォギアAXZ」PV 最高画質',
            'description': 'md5:e52974af9a96e739196b2c1ca72b5feb',
            'timestamp': 1498481660,
            'upload_date': '20170626',
            'uploader': 'no-namamae',
            'uploader_id': '40826363',
            'thumbnail': r're:https?://.*',
            'duration': 198,
            'view_count': int,
            'comment_count': int,
            'genres': ['アニメ'],
            'tags': [],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # Video without owner
        'url': 'http://www.nicovideo.jp/watch/sm18238488',
        'info_dict': {
            'id': 'sm18238488',
            'ext': 'mp4',
            'title': '【実写版】ミュータントタートルズ',
            'description': 'md5:15df8988e47a86f9e978af2064bf6d8e',
            'timestamp': 1341128008,
            'upload_date': '20120701',
            'thumbnail': r're:https?://.*',
            'duration': 5271,
            'view_count': int,
            'comment_count': int,
            'genres': ['エンターテイメント'],
            'tags': [],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'http://sp.nicovideo.jp/watch/sm28964488?ss_pos=1&cp_in=wt_tg',
        'only_matching': True,
    }, {
        'note': 'a video that is only served as an ENCRYPTED HLS.',
        'url': 'https://www.nicovideo.jp/watch/so38016254',
        'only_matching': True,
    }]

    _VALID_URL = r'https?://(?:(?:www\.|secure\.|sp\.)?nicovideo\.jp/watch|nico\.ms)/(?P<id>(?:[a-z]{2})?[0-9]+)'
    _NETRC_MACHINE = 'niconico'
    _API_HEADERS = {
        'X-Frontend-ID': '6',
        'X-Frontend-Version': '0',
        'X-Niconico-Language': 'en-us',
        'Referer': 'https://www.nicovideo.jp/',
        'Origin': 'https://www.nicovideo.jp',
    }

    def _perform_login(self, username, password):
        login_ok = True
        login_form_strs = {
            'mail_tel': username,
            'password': password,
        }
        self._request_webpage(
            'https://account.nicovideo.jp/login', None,
            note='Acquiring Login session')
        page = self._download_webpage(
            'https://account.nicovideo.jp/login/redirector?show_button_twitter=1&site=niconico&show_button_facebook=1', None,
            note='Logging in', errnote='Unable to log in',
            data=urlencode_postdata(login_form_strs),
            headers={
                'Referer': 'https://account.nicovideo.jp/login',
                'Content-Type': 'application/x-www-form-urlencoded',
            })
        if 'oneTimePw' in page:
            post_url = self._search_regex(
                r'<form[^>]+action=(["\'])(?P<url>.+?)\1', page, 'post url', group='url')
            page = self._download_webpage(
                urljoin('https://account.nicovideo.jp', post_url), None,
                note='Performing MFA', errnote='Unable to complete MFA',
                data=urlencode_postdata({
                    'otp': self._get_tfa_info('6 digits code'),
                }), headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                })
            if 'oneTimePw' in page or 'formError' in page:
                err_msg = self._html_search_regex(
                    r'formError["\']+>(.*?)</div>', page, 'form_error',
                    default='There\'s an error but the message can\'t be parsed.',
                    flags=re.DOTALL)
                self.report_warning(f'Unable to log in: MFA challenge failed, "{err_msg}"')
                return False
        login_ok = 'class="notice error"' not in page
        if not login_ok:
            self.report_warning('Unable to log in: bad username or password')
        return login_ok

    def _get_heartbeat_info(self, info_dict):
        video_id, video_src_id, audio_src_id = info_dict['url'].split(':')[1].split('/')
        dmc_protocol = info_dict['expected_protocol']

        api_data = (
            info_dict.get('_api_data')
            or self._parse_json(
                self._html_search_regex(
                    'data-api-data="([^"]+)"',
                    self._download_webpage('https://www.nicovideo.jp/watch/' + video_id, video_id),
                    'API data', default='{}'),
                video_id))

        session_api_data = try_get(api_data, lambda x: x['media']['delivery']['movie']['session'])
        session_api_endpoint = try_get(session_api_data, lambda x: x['urls'][0])

        def ping():
            tracking_id = traverse_obj(api_data, ('media', 'delivery', 'trackingId'))
            if tracking_id:
                tracking_url = update_url_query('https://nvapi.nicovideo.jp/v1/2ab0cbaa/watch', {'t': tracking_id})
                watch_request_response = self._download_json(
                    tracking_url, video_id,
                    note='Acquiring permission for downloading video', fatal=False,
                    headers=self._API_HEADERS)
                if traverse_obj(watch_request_response, ('meta', 'status')) != 200:
                    self.report_warning('Failed to acquire permission for playing video. Video download may fail.')

        yesno = lambda x: 'yes' if x else 'no'

        if dmc_protocol == 'http':
            protocol = 'http'
            protocol_parameters = {
                'http_output_download_parameters': {
                    'use_ssl': yesno(session_api_data['urls'][0]['isSsl']),
                    'use_well_known_port': yesno(session_api_data['urls'][0]['isWellKnownPort']),
                },
            }
        elif dmc_protocol == 'hls':
            protocol = 'm3u8'
            segment_duration = try_get(self._configuration_arg('segment_duration'), lambda x: int(x[0])) or 6000
            parsed_token = self._parse_json(session_api_data['token'], video_id)
            encryption = traverse_obj(api_data, ('media', 'delivery', 'encryption'))
            protocol_parameters = {
                'hls_parameters': {
                    'segment_duration': segment_duration,
                    'transfer_preset': '',
                    'use_ssl': yesno(session_api_data['urls'][0]['isSsl']),
                    'use_well_known_port': yesno(session_api_data['urls'][0]['isWellKnownPort']),
                },
            }
            if 'hls_encryption' in parsed_token and encryption:
                protocol_parameters['hls_parameters']['encryption'] = {
                    parsed_token['hls_encryption']: {
                        'encrypted_key': encryption['encryptedKey'],
                        'key_uri': encryption['keyUri'],
                    },
                }
            else:
                protocol = 'm3u8_native'
        else:
            raise ExtractorError(f'Unsupported DMC protocol: {dmc_protocol}')

        session_response = self._download_json(
            session_api_endpoint['url'], video_id,
            query={'_format': 'json'},
            headers={'Content-Type': 'application/json'},
            note='Downloading JSON metadata for {}'.format(info_dict['format_id']),
            data=json.dumps({
                'session': {
                    'client_info': {
                        'player_id': session_api_data.get('playerId'),
                    },
                    'content_auth': {
                        'auth_type': try_get(session_api_data, lambda x: x['authTypes'][session_api_data['protocols'][0]]),
                        'content_key_timeout': session_api_data.get('contentKeyTimeout'),
                        'service_id': 'nicovideo',
                        'service_user_id': session_api_data.get('serviceUserId'),
                    },
                    'content_id': session_api_data.get('contentId'),
                    'content_src_id_sets': [{
                        'content_src_ids': [{
                            'src_id_to_mux': {
                                'audio_src_ids': [audio_src_id],
                                'video_src_ids': [video_src_id],
                            },
                        }],
                    }],
                    'content_type': 'movie',
                    'content_uri': '',
                    'keep_method': {
                        'heartbeat': {
                            'lifetime': session_api_data.get('heartbeatLifetime'),
                        },
                    },
                    'priority': session_api_data['priority'],
                    'protocol': {
                        'name': 'http',
                        'parameters': {
                            'http_parameters': {
                                'parameters': protocol_parameters,
                            },
                        },
                    },
                    'recipe_id': session_api_data.get('recipeId'),
                    'session_operation_auth': {
                        'session_operation_auth_by_signature': {
                            'signature': session_api_data.get('signature'),
                            'token': session_api_data.get('token'),
                        },
                    },
                    'timing_constraint': 'unlimited',
                },
            }).encode())

        info_dict['url'] = session_response['data']['session']['content_uri']
        info_dict['protocol'] = protocol

        # get heartbeat info
        heartbeat_info_dict = {
            'url': session_api_endpoint['url'] + '/' + session_response['data']['session']['id'] + '?_format=json&_method=PUT',
            'data': json.dumps(session_response['data']),
            # interval, convert milliseconds to seconds, then halve to make a buffer.
            'interval': float_or_none(session_api_data.get('heartbeatLifetime'), scale=3000),
            'ping': ping,
        }

        return info_dict, heartbeat_info_dict

    def _extract_format_for_quality(self, video_id, audio_quality, video_quality, dmc_protocol):

        if not audio_quality.get('isAvailable') or not video_quality.get('isAvailable'):
            return None

        format_id = '-'.join(
            [remove_start(s['id'], 'archive_') for s in (video_quality, audio_quality)] + [dmc_protocol])

        vid_qual_label = traverse_obj(video_quality, ('metadata', 'label'))

        return {
            'url': 'niconico_dmc:{}/{}/{}'.format(video_id, video_quality['id'], audio_quality['id']),
            'format_id': format_id,
            'format_note': join_nonempty('DMC', vid_qual_label, dmc_protocol.upper(), delim=' '),
            'ext': 'mp4',  # Session API are used in HTML5, which always serves mp4
            'acodec': 'aac',
            'vcodec': 'h264',
            **traverse_obj(audio_quality, ('metadata', {
                'abr': ('bitrate', {float_or_none(scale=1000)}),
                'asr': ('samplingRate', {int_or_none}),
            })),
            **traverse_obj(video_quality, ('metadata', {
                'vbr': ('bitrate', {float_or_none(scale=1000)}),
                'height': ('resolution', 'height', {int_or_none}),
                'width': ('resolution', 'width', {int_or_none}),
            })),
            'quality': -2 if 'low' in video_quality['id'] else None,
            'protocol': 'niconico_dmc',
            'expected_protocol': dmc_protocol,  # XXX: This is not a documented field
            'http_headers': {
                'Origin': 'https://www.nicovideo.jp',
                'Referer': 'https://www.nicovideo.jp/watch/' + video_id,
            },
        }

    def _yield_dmc_formats(self, api_data, video_id):
        dmc_data = traverse_obj(api_data, ('media', 'delivery', 'movie'))
        audios = traverse_obj(dmc_data, ('audios', ..., {dict}))
        videos = traverse_obj(dmc_data, ('videos', ..., {dict}))
        protocols = traverse_obj(dmc_data, ('session', 'protocols', ..., {str}))
        if not all((audios, videos, protocols)):
            return

        for audio_quality, video_quality, protocol in itertools.product(audios, videos, protocols):
            if fmt := self._extract_format_for_quality(video_id, audio_quality, video_quality, protocol):
                yield fmt

    def _yield_dms_formats(self, api_data, video_id):
        fmt_filter = lambda _, v: v['isAvailable'] and v['id']
        videos = traverse_obj(api_data, ('media', 'domand', 'videos', fmt_filter))
        audios = traverse_obj(api_data, ('media', 'domand', 'audios', fmt_filter))
        access_key = traverse_obj(api_data, ('media', 'domand', 'accessRightKey', {str}))
        track_id = traverse_obj(api_data, ('client', 'watchTrackId', {str}))
        if not all((videos, audios, access_key, track_id)):
            return

        dms_m3u8_url = self._download_json(
            f'https://nvapi.nicovideo.jp/v1/watch/{video_id}/access-rights/hls', video_id,
            data=json.dumps({
                'outputs': list(itertools.product((v['id'] for v in videos), (a['id'] for a in audios))),
            }).encode(), query={'actionTrackId': track_id}, headers={
                'x-access-right-key': access_key,
                'x-frontend-id': 6,
                'x-frontend-version': 0,
                'x-request-with': 'https://www.nicovideo.jp',
            })['data']['contentUrl']
        # Getting all audio formats results in duplicate video formats which we filter out later
        dms_fmts = self._extract_m3u8_formats(dms_m3u8_url, video_id, 'mp4')

        # m3u8 extraction does not provide audio bitrates, so extract from the API data and fix
        for audio_fmt in traverse_obj(dms_fmts, lambda _, v: v['vcodec'] == 'none'):
            yield {
                **audio_fmt,
                **traverse_obj(audios, (lambda _, v: audio_fmt['format_id'].startswith(v['id']), {
                    'format_id': ('id', {str}),
                    'abr': ('bitRate', {float_or_none(scale=1000)}),
                    'asr': ('samplingRate', {int_or_none}),
                    'quality': ('qualityLevel', {int_or_none}),
                }), get_all=False),
                'acodec': 'aac',
            }

        # Sort before removing dupes to keep the format dicts with the lowest tbr
        video_fmts = sorted((fmt for fmt in dms_fmts if fmt['vcodec'] != 'none'), key=lambda f: f['tbr'])
        self._remove_duplicate_formats(video_fmts)
        # Calculate the true vbr/tbr by subtracting the lowest abr
        min_abr = min(traverse_obj(audios, (..., 'bitRate', {float_or_none})), default=0) / 1000
        for video_fmt in video_fmts:
            video_fmt['tbr'] -= min_abr
            video_fmt['format_id'] = url_basename(video_fmt['url']).rpartition('.')[0]
            video_fmt['quality'] = traverse_obj(videos, (
                lambda _, v: v['id'] == video_fmt['format_id'], 'qualityLevel', {int_or_none}, any)) or -1
            yield video_fmt

    def _real_extract(self, url):
        video_id = self._match_id(url)

        try:
            webpage, handle = self._download_webpage_handle(
                'https://www.nicovideo.jp/watch/' + video_id, video_id)
            if video_id.startswith('so'):
                video_id = self._match_id(handle.url)

            api_data = traverse_obj(
                self._parse_json(self._html_search_meta('server-response', webpage) or '', video_id),
                ('data', 'response', {dict}))
            if not api_data:
                raise ExtractorError('Server response data not found')
        except ExtractorError as e:
            try:
                api_data = self._download_json(
                    f'https://www.nicovideo.jp/api/watch/v3/{video_id}?_frontendId=6&_frontendVersion=0&actionTrackId=AAAAAAAAAA_{round(time.time() * 1000)}', video_id,
                    note='Downloading API JSON', errnote='Unable to fetch data')['data']
            except ExtractorError:
                if not isinstance(e.cause, HTTPError):
                    raise
                webpage = e.cause.response.read().decode('utf-8', 'replace')
                error_msg = self._html_search_regex(
                    r'(?s)<section\s+class="(?:(?:ErrorMessage|WatchExceptionPage-message)\s*)+">(.+?)</section>',
                    webpage, 'error reason', default=None)
                if not error_msg:
                    raise
                raise ExtractorError(clean_html(error_msg), expected=True)

        availability = self._availability(**(traverse_obj(api_data, ('payment', 'video', {
            'needs_premium': ('isPremium', {bool}),
            'needs_subscription': ('isAdmission', {bool}),
        })) or {'needs_auth': True}))
        formats = [*self._yield_dmc_formats(api_data, video_id),
                   *self._yield_dms_formats(api_data, video_id)]
        if not formats:
            fail_msg = clean_html(self._html_search_regex(
                r'<p[^>]+\bclass="fail-message"[^>]*>(?P<msg>.+?)</p>',
                webpage, 'fail message', default=None, group='msg'))
            if fail_msg:
                self.to_screen(f'Niconico said: {fail_msg}')
            if fail_msg and 'された地域と同じ地域からのみ視聴できます。' in fail_msg:
                availability = None
                self.raise_geo_restricted(countries=self._GEO_COUNTRIES, metadata_available=True)
            elif availability == 'premium_only':
                self.raise_login_required('This video requires premium', metadata_available=True)
            elif availability == 'subscriber_only':
                self.raise_login_required('This video is for members only', metadata_available=True)
            elif availability == 'needs_auth':
                self.raise_login_required(metadata_available=False)

        # Start extracting information
        tags = None
        if webpage:
            # use og:video:tag (not logged in)
            og_video_tags = re.finditer(r'<meta\s+property="og:video:tag"\s*content="(.*?)">', webpage)
            tags = list(filter(None, (clean_html(x.group(1)) for x in og_video_tags)))
            if not tags:
                # use keywords and split with comma (not logged in)
                kwds = self._html_search_meta('keywords', webpage, default=None)
                if kwds:
                    tags = [x for x in kwds.split(',') if x]
        if not tags:
            # find in json (logged in)
            tags = traverse_obj(api_data, ('tag', 'items', ..., 'name'))

        thumb_prefs = qualities(['url', 'middleUrl', 'largeUrl', 'player', 'ogp'])

        def get_video_info(*items, get_first=True, **kwargs):
            return traverse_obj(api_data, ('video', *items), get_all=not get_first, **kwargs)

        return {
            'id': video_id,
            '_api_data': api_data,
            'title': get_video_info(('originalTitle', 'title')) or self._og_search_title(webpage, default=None),
            'formats': formats,
            'availability': availability,
            'thumbnails': [{
                'id': key,
                'url': url,
                'ext': 'jpg',
                'preference': thumb_prefs(key),
                **parse_resolution(url, lenient=True),
            } for key, url in (get_video_info('thumbnail') or {}).items() if url],
            'description': clean_html(get_video_info('description')),
            'uploader': traverse_obj(api_data, ('owner', 'nickname'), ('channel', 'name'), ('community', 'name')),
            'uploader_id': str_or_none(traverse_obj(api_data, ('owner', 'id'), ('channel', 'id'), ('community', 'id'))),
            'timestamp': parse_iso8601(get_video_info('registeredAt')) or parse_iso8601(
                self._html_search_meta('video:release_date', webpage, 'date published', default=None)),
            'channel': traverse_obj(api_data, ('channel', 'name'), ('community', 'name')),
            'channel_id': traverse_obj(api_data, ('channel', 'id'), ('community', 'id')),
            'view_count': int_or_none(get_video_info('count', 'view')),
            'tags': tags,
            'genre': traverse_obj(api_data, ('genre', 'label'), ('genre', 'key')),
            'comment_count': get_video_info('count', 'comment', expected_type=int),
            'duration': (
                parse_duration(self._html_search_meta('video:duration', webpage, 'video duration', default=None))
                or get_video_info('duration')),
            'webpage_url': url_or_none(url) or f'https://www.nicovideo.jp/watch/{video_id}',
            'subtitles': self.extract_subtitles(video_id, api_data),
        }

    def _get_subtitles(self, video_id, api_data):
        comments_info = traverse_obj(api_data, ('comment', 'nvComment', {dict})) or {}
        if not comments_info.get('server'):
            return

        danmaku = traverse_obj(self._download_json(
            f'{comments_info["server"]}/v1/threads', video_id, data=json.dumps({
                'additionals': {},
                'params': comments_info.get('params'),
                'threadKey': comments_info.get('threadKey'),
            }).encode(), fatal=False,
            headers={
                'Referer': 'https://www.nicovideo.jp/',
                'Origin': 'https://www.nicovideo.jp',
                'Content-Type': 'text/plain;charset=UTF-8',
                'x-client-os-type': 'others',
                'x-frontend-id': '6',
                'x-frontend-version': '0',
            },
            note='Downloading comments', errnote='Failed to download comments'),
            ('data', 'threads', ..., 'comments', ...))

        return {
            'comments': [{
                'ext': 'json',
                'data': json.dumps(danmaku),
            }],
        }


class NiconicoPlaylistBaseIE(InfoExtractor):
    _PAGE_SIZE = 100

    _API_HEADERS = {
        'X-Frontend-ID': '6',
        'X-Frontend-Version': '0',
        'X-Niconico-Language': 'en-us',
    }

    def _call_api(self, list_id, resource, query):
        raise NotImplementedError('Must be implemented in subclasses')

    @staticmethod
    def _parse_owner(item):
        return {
            'uploader': traverse_obj(item, ('owner', ('name', ('user', 'nickname')), {str}, any)),
            'uploader_id': traverse_obj(item, ('owner', 'id', {str})),
        }

    def _fetch_page(self, list_id, page):
        page += 1
        resp = self._call_api(list_id, f'page {page}', {
            'page': page,
            'pageSize': self._PAGE_SIZE,
        })
        # this is needed to support both mylist and user
        for video in traverse_obj(resp, ('items', ..., ('video', None))) or []:
            video_id = video.get('id')
            if not video_id:
                # skip {"video": {"id": "blablabla", ...}}
                continue
            count = video.get('count') or {}
            get_count = lambda x: int_or_none(count.get(x))
            yield {
                '_type': 'url',
                'id': video_id,
                'title': video.get('title'),
                'url': f'https://www.nicovideo.jp/watch/{video_id}',
                'description': video.get('shortDescription'),
                'duration': int_or_none(video.get('duration')),
                'view_count': get_count('view'),
                'comment_count': get_count('comment'),
                'thumbnail': traverse_obj(video, ('thumbnail', ('nHdUrl', 'largeUrl', 'listingUrl', 'url'))),
                'ie_key': NiconicoIE.ie_key(),
                **self._parse_owner(video),
            }

    def _entries(self, list_id):
        return OnDemandPagedList(functools.partial(self._fetch_page, list_id), self._PAGE_SIZE)


class NiconicoPlaylistIE(NiconicoPlaylistBaseIE):
    IE_NAME = 'niconico:playlist'
    _VALID_URL = r'https?://(?:(?:www\.|sp\.)?nicovideo\.jp|nico\.ms)/(?:user/\d+/)?(?:my/)?mylist/(?:#/)?(?P<id>\d+)'

    _TESTS = [{
        'url': 'http://www.nicovideo.jp/mylist/27411728',
        'info_dict': {
            'id': '27411728',
            'title': 'AKB48のオールナイトニッポン',
            'description': 'md5:d89694c5ded4b6c693dea2db6e41aa08',
            'uploader': 'のっく',
            'uploader_id': '805442',
        },
        'playlist_mincount': 291,
    }, {
        'url': 'https://www.nicovideo.jp/user/805442/mylist/27411728',
        'only_matching': True,
    }, {
        'url': 'https://www.nicovideo.jp/my/mylist/#/68048635',
        'only_matching': True,
    }]

    def _call_api(self, list_id, resource, query):
        return self._download_json(
            f'https://nvapi.nicovideo.jp/v2/mylists/{list_id}', list_id,
            f'Downloading {resource}', query=query,
            headers=self._API_HEADERS)['data']['mylist']

    def _real_extract(self, url):
        list_id = self._match_id(url)
        mylist = self._call_api(list_id, 'list', {
            'pageSize': 1,
        })
        return self.playlist_result(
            self._entries(list_id), list_id,
            mylist.get('name'), mylist.get('description'), **self._parse_owner(mylist))


class NiconicoSeriesIE(NiconicoPlaylistBaseIE):
    IE_NAME = 'niconico:series'
    _VALID_URL = r'https?://(?:(?:www\.|sp\.)?nicovideo\.jp(?:/user/\d+)?|nico\.ms)/series/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://www.nicovideo.jp/user/44113208/series/110226',
        'info_dict': {
            'id': '110226',
            'title': 'ご立派ァ！のシリーズ',
            'description': '楽しそうな外人の吹き替えをさせたら終身名誉ホモガキの右に出る人はいませんね…',
            'uploader': 'アルファるふぁ',
            'uploader_id': '44113208',
        },
        'playlist_mincount': 10,
    }, {
        'url': 'https://www.nicovideo.jp/series/12312/',
        'info_dict': {
            'id': '12312',
            'title': 'バトルスピリッツ　お勧めカード紹介(調整中)',
            'description': '',
            'uploader': '野鳥',
            'uploader_id': '2275360',
        },
        'playlist_mincount': 103,
    }, {
        'url': 'https://nico.ms/series/203559',
        'only_matching': True,
    }]

    def _call_api(self, list_id, resource, query):
        return self._download_json(
            f'https://nvapi.nicovideo.jp/v2/series/{list_id}', list_id,
            f'Downloading {resource}', query=query,
            headers=self._API_HEADERS)['data']

    def _real_extract(self, url):
        list_id = self._match_id(url)
        series = self._call_api(list_id, 'list', {
            'pageSize': 1,
        })['detail']

        return self.playlist_result(
            self._entries(list_id), list_id,
            series.get('title'), series.get('description'), **self._parse_owner(series))


class NiconicoHistoryIE(NiconicoPlaylistBaseIE):
    IE_NAME = 'niconico:history'
    IE_DESC = 'NicoNico user history or likes. Requires cookies.'
    _VALID_URL = r'https?://(?:www\.|sp\.)?nicovideo\.jp/my/(?P<id>history(?:/like)?)'

    _TESTS = [{
        'note': 'PC page, with /video',
        'url': 'https://www.nicovideo.jp/my/history/video',
        'only_matching': True,
    }, {
        'note': 'PC page, without /video',
        'url': 'https://www.nicovideo.jp/my/history',
        'only_matching': True,
    }, {
        'note': 'mobile page, with /video',
        'url': 'https://sp.nicovideo.jp/my/history/video',
        'only_matching': True,
    }, {
        'note': 'mobile page, without /video',
        'url': 'https://sp.nicovideo.jp/my/history',
        'only_matching': True,
    }, {
        'note': 'PC page',
        'url': 'https://www.nicovideo.jp/my/history/like',
        'only_matching': True,
    }, {
        'note': 'Mobile page',
        'url': 'https://sp.nicovideo.jp/my/history/like',
        'only_matching': True,
    }]

    def _call_api(self, list_id, resource, query):
        path = 'likes' if list_id == 'history/like' else 'watch/history'
        return self._download_json(
            f'https://nvapi.nicovideo.jp/v1/users/me/{path}', list_id,
            f'Downloading {resource}', query=query, headers=self._API_HEADERS)['data']

    def _real_extract(self, url):
        list_id = self._match_id(url)
        try:
            mylist = self._call_api(list_id, 'list', {'pageSize': 1})
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 401:
                self.raise_login_required('You have to be logged in to get your history')
            raise
        return self.playlist_result(self._entries(list_id), list_id, **self._parse_owner(mylist))


class NicovideoSearchBaseIE(InfoExtractor):
    _SEARCH_TYPE = 'search'

    def _entries(self, url, item_id, query=None, note='Downloading page %(page)s'):
        query = query or {}
        pages = [query['page']] if 'page' in query else itertools.count(1)
        for page_num in pages:
            query['page'] = str(page_num)
            webpage = self._download_webpage(url, item_id, query=query, note=note % {'page': page_num})
            results = re.findall(r'(?<=data-video-id=)["\']?(?P<videoid>.*?)(?=["\'])', webpage)
            for item in results:
                yield self.url_result(f'https://www.nicovideo.jp/watch/{item}', 'Niconico', item)
            if not results:
                break

    def _search_results(self, query):
        return self._entries(
            self._proto_relative_url(f'//www.nicovideo.jp/{self._SEARCH_TYPE}/{query}'), query)


class NicovideoSearchIE(NicovideoSearchBaseIE, SearchInfoExtractor):
    IE_DESC = 'Nico video search'
    IE_NAME = 'nicovideo:search'
    _SEARCH_KEY = 'nicosearch'


class NicovideoSearchURLIE(NicovideoSearchBaseIE):
    IE_NAME = f'{NicovideoSearchIE.IE_NAME}_url'
    IE_DESC = 'Nico video search URLs'
    _VALID_URL = r'https?://(?:www\.)?nicovideo\.jp/search/(?P<id>[^?#&]+)?'
    _TESTS = [{
        'url': 'http://www.nicovideo.jp/search/sm9',
        'info_dict': {
            'id': 'sm9',
            'title': 'sm9',
        },
        'playlist_mincount': 40,
    }, {
        'url': 'https://www.nicovideo.jp/search/sm9?sort=h&order=d&end=2020-12-31&start=2020-01-01',
        'info_dict': {
            'id': 'sm9',
            'title': 'sm9',
        },
        'playlist_count': 31,
    }]

    def _real_extract(self, url):
        query = self._match_id(url)
        return self.playlist_result(self._entries(url, query), query, query)


class NicovideoSearchDateIE(NicovideoSearchBaseIE, SearchInfoExtractor):
    IE_DESC = 'Nico video search, newest first'
    IE_NAME = f'{NicovideoSearchIE.IE_NAME}:date'
    _SEARCH_KEY = 'nicosearchdate'
    _TESTS = [{
        'url': 'nicosearchdateall:a',
        'info_dict': {
            'id': 'a',
            'title': 'a',
        },
        'playlist_mincount': 1610,
    }]

    _START_DATE = dt.date(2007, 1, 1)
    _RESULTS_PER_PAGE = 32
    _MAX_PAGES = 50

    def _entries(self, url, item_id, start_date=None, end_date=None):
        start_date, end_date = start_date or self._START_DATE, end_date or dt.datetime.now().date()

        # If the last page has a full page of videos, we need to break down the query interval further
        last_page_len = len(list(self._get_entries_for_date(
            url, item_id, start_date, end_date, self._MAX_PAGES,
            note=f'Checking number of videos from {start_date} to {end_date}')))
        if (last_page_len == self._RESULTS_PER_PAGE and start_date != end_date):
            midpoint = start_date + ((end_date - start_date) // 2)
            yield from self._entries(url, item_id, midpoint, end_date)
            yield from self._entries(url, item_id, start_date, midpoint)
        else:
            self.to_screen(f'{item_id}: Downloading results from {start_date} to {end_date}')
            yield from self._get_entries_for_date(
                url, item_id, start_date, end_date, note='    Downloading page %(page)s')

    def _get_entries_for_date(self, url, item_id, start_date, end_date=None, page_num=None, note=None):
        query = {
            'start': str(start_date),
            'end': str(end_date or start_date),
            'sort': 'f',
            'order': 'd',
        }
        if page_num:
            query['page'] = str(page_num)

        yield from super()._entries(url, item_id, query=query, note=note)


class NicovideoTagURLIE(NicovideoSearchBaseIE):
    IE_NAME = 'niconico:tag'
    IE_DESC = 'NicoNico video tag URLs'
    _SEARCH_TYPE = 'tag'
    _VALID_URL = r'https?://(?:www\.)?nicovideo\.jp/tag/(?P<id>[^?#&]+)?'
    _TESTS = [{
        'url': 'https://www.nicovideo.jp/tag/ドキュメンタリー淫夢',
        'info_dict': {
            'id': 'ドキュメンタリー淫夢',
            'title': 'ドキュメンタリー淫夢',
        },
        'playlist_mincount': 400,
    }]

    def _real_extract(self, url):
        query = self._match_id(url)
        return self.playlist_result(self._entries(url, query), query, query)


class NiconicoUserIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?nicovideo\.jp/user/(?P<id>\d+)(?:/video)?/?(?:$|[#?])'
    _TEST = {
        'url': 'https://www.nicovideo.jp/user/419948',
        'info_dict': {
            'id': '419948',
        },
        'playlist_mincount': 101,
    }
    _API_URL = 'https://nvapi.nicovideo.jp/v2/users/%s/videos?sortKey=registeredAt&sortOrder=desc&pageSize=%s&page=%s'
    _PAGE_SIZE = 100

    _API_HEADERS = {
        'X-Frontend-ID': '6',
        'X-Frontend-Version': '0',
    }

    def _entries(self, list_id):
        total_count = 1
        count = page_num = 0
        while count < total_count:
            json_parsed = self._download_json(
                self._API_URL % (list_id, self._PAGE_SIZE, page_num + 1), list_id,
                headers=self._API_HEADERS,
                note='Downloading JSON metadata%s' % (f' page {page_num}' if page_num else ''))
            if not page_num:
                total_count = int_or_none(json_parsed['data'].get('totalCount'))
            for entry in json_parsed['data']['items']:
                count += 1
                yield self.url_result(
                    f'https://www.nicovideo.jp/watch/{entry["essential"]["id"]}', ie=NiconicoIE)
            page_num += 1

    def _real_extract(self, url):
        list_id = self._match_id(url)
        return self.playlist_result(self._entries(list_id), list_id)


class NiconicoLiveIE(InfoExtractor):
    IE_NAME = 'niconico:live'
    IE_DESC = 'ニコニコ生放送'
    _VALID_URL = r'https?://(?:sp\.)?live2?\.nicovideo\.jp/(?:watch|gate)/(?P<id>lv\d+)'
    _TESTS = [{
        'note': 'this test case includes invisible characters for title, pasting them as-is',
        'url': 'https://live.nicovideo.jp/watch/lv339533123',
        'info_dict': {
            'id': 'lv339533123',
            'title': '激辛ペヤング食べます\u202a( ;ᯅ; )\u202c（歌枠オーディション参加中）',
            'view_count': 1526,
            'comment_count': 1772,
            'description': '初めましてもかって言います❕\nのんびり自由に適当に暮らしてます',
            'uploader': 'もか',
            'channel': 'ゲストさんのコミュニティ',
            'channel_id': 'co5776900',
            'channel_url': 'https://com.nicovideo.jp/community/co5776900',
            'timestamp': 1670677328,
            'is_live': True,
        },
        'skip': 'livestream',
    }, {
        'url': 'https://live2.nicovideo.jp/watch/lv339533123',
        'only_matching': True,
    }, {
        'url': 'https://sp.live.nicovideo.jp/watch/lv339533123',
        'only_matching': True,
    }, {
        'url': 'https://sp.live2.nicovideo.jp/watch/lv339533123',
        'only_matching': True,
    }]

    _KNOWN_LATENCY = ('high', 'low')

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage, urlh = self._download_webpage_handle(f'https://live.nicovideo.jp/watch/{video_id}', video_id)

        embedded_data = self._parse_json(unescapeHTML(self._search_regex(
            r'<script\s+id="embedded-data"\s*data-props="(.+?)"', webpage, 'embedded data')), video_id)

        ws_url = traverse_obj(embedded_data, ('site', 'relive', 'webSocketUrl'))
        if not ws_url:
            raise ExtractorError('The live hasn\'t started yet or already ended.', expected=True)
        ws_url = update_url_query(ws_url, {
            'frontend_id': traverse_obj(embedded_data, ('site', 'frontendId')) or '9',
        })

        hostname = remove_start(urllib.parse.urlparse(urlh.url).hostname, 'sp.')
        latency = try_get(self._configuration_arg('latency'), lambda x: x[0])
        if latency not in self._KNOWN_LATENCY:
            latency = 'high'

        ws = self._request_webpage(
            Request(ws_url, headers={'Origin': f'https://{hostname}'}),
            video_id=video_id, note='Connecting to WebSocket server')

        self.write_debug('[debug] Sending HLS server request')
        ws.send(json.dumps({
            'type': 'startWatching',
            'data': {
                'stream': {
                    'quality': 'abr',
                    'protocol': 'hls+fmp4',
                    'latency': latency,
                    'accessRightMethod': 'single_cookie',
                    'chasePlay': False,
                },
                'room': {
                    'protocol': 'webSocket',
                    'commentable': True,
                },
                'reconnect': False,
            },
        }))

        while True:
            recv = ws.recv()
            if not recv:
                continue
            data = json.loads(recv)
            if not isinstance(data, dict):
                continue
            if data.get('type') == 'stream':
                m3u8_url = data['data']['uri']
                qualities = data['data']['availableQualities']
                cookies = data['data']['cookies']
                break
            elif data.get('type') == 'disconnect':
                self.write_debug(recv)
                raise ExtractorError('Disconnected at middle of extraction')
            elif data.get('type') == 'error':
                self.write_debug(recv)
                message = traverse_obj(data, ('body', 'code')) or recv
                raise ExtractorError(message)
            elif self.get_param('verbose', False):
                if len(recv) > 100:
                    recv = recv[:100] + '...'
                self.write_debug(f'Server said: {recv}')

        title = traverse_obj(embedded_data, ('program', 'title')) or self._html_search_meta(
            ('og:title', 'twitter:title'), webpage, 'live title', fatal=False)

        raw_thumbs = traverse_obj(embedded_data, ('program', 'thumbnail')) or {}
        thumbnails = []
        for name, value in raw_thumbs.items():
            if not isinstance(value, dict):
                thumbnails.append({
                    'id': name,
                    'url': value,
                    **parse_resolution(value, lenient=True),
                })
                continue

            for k, img_url in value.items():
                res = parse_resolution(k, lenient=True) or parse_resolution(img_url, lenient=True)
                width, height = res.get('width'), res.get('height')

                thumbnails.append({
                    'id': f'{name}_{width}x{height}',
                    'url': img_url,
                    'ext': traverse_obj(parse_qs(img_url), ('image', 0, {determine_ext(default_ext='jpg')})),
                    **res,
                })

        for cookie in cookies:
            self._set_cookie(
                cookie['domain'], cookie['name'], cookie['value'],
                expire_time=unified_timestamp(cookie['expires']), path=cookie['path'], secure=cookie['secure'])

        formats = self._extract_m3u8_formats(m3u8_url, video_id, ext='mp4', live=True)
        for fmt, q in zip(formats, reversed(qualities[1:])):
            fmt.update({
                'format_id': q,
                'protocol': 'niconico_live',
                'ws': ws,
                'video_id': video_id,
                'live_latency': latency,
                'origin': hostname,
            })

        return {
            'id': video_id,
            'title': title,
            **traverse_obj(embedded_data, {
                'view_count': ('program', 'statistics', 'watchCount'),
                'comment_count': ('program', 'statistics', 'commentCount'),
                'uploader': ('program', 'supplier', 'name'),
                'channel': ('socialGroup', 'name'),
                'channel_id': ('socialGroup', 'id'),
                'channel_url': ('socialGroup', 'socialGroupPageUrl'),
            }),
            'description': clean_html(traverse_obj(embedded_data, ('program', 'description'))),
            'timestamp': int_or_none(traverse_obj(embedded_data, ('program', 'openTime'))),
            'is_live': True,
            'thumbnails': thumbnails,
            'formats': formats,
        }
