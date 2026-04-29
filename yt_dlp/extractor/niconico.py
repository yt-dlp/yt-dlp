import datetime as dt
import functools
import itertools
import json
import re

from .common import InfoExtractor, SearchInfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    clean_html,
    determine_ext,
    extract_attributes,
    float_or_none,
    int_or_none,
    parse_bitrate,
    parse_iso8601,
    parse_qs,
    parse_resolution,
    qualities,
    str_or_none,
    time_seconds,
    truncate_string,
    unified_timestamp,
    update_url_query,
    url_basename,
    url_or_none,
    urlencode_postdata,
    urljoin,
)
from ..utils.traversal import (
    find_element,
    require,
    traverse_obj,
)


class NiconicoBaseIE(InfoExtractor):
    _API_BASE = 'https://nvapi.nicovideo.jp'
    _BASE_URL = 'https://www.nicovideo.jp'
    _GEO_BYPASS = False
    _GEO_COUNTRIES = ['JP']
    _HEADERS = {
        'X-Frontend-ID': '6',
        'X-Frontend-Version': '0',
    }
    _LOGIN_BASE = 'https://account.nicovideo.jp'
    _NETRC_MACHINE = 'niconico'

    @property
    def is_logged_in(self):
        return bool(self._get_cookies('https://www.nicovideo.jp').get('user_session'))

    def _raise_login_error(self, message, expected=True):
        raise ExtractorError(f'Unable to login: {message}', expected=expected)

    def _perform_login(self, username, password):
        if self.is_logged_in:
            return

        self._request_webpage(
            f'{self._LOGIN_BASE}/login', None, 'Requesting session cookies')
        webpage = self._download_webpage(
            f'{self._LOGIN_BASE}/login/redirector', None,
            'Logging in', 'Unable to log in', headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': f'{self._LOGIN_BASE}/login',
            }, data=urlencode_postdata({
                'mail_tel': username,
                'password': password,
            }))

        if self.is_logged_in:
            return
        elif err_msg := traverse_obj(webpage, (
            {find_element(cls='notice error')}, {find_element(cls='notice__text')}, {clean_html},
        )):
            self._raise_login_error(err_msg or 'Invalid username or password')
        elif 'oneTimePw' in webpage:
            post_url = self._search_regex(
                r'<form[^>]+action=(["\'])(?P<url>.+?)\1', webpage, 'post url', group='url')
            mfa, urlh = self._download_webpage_handle(
                urljoin(self._LOGIN_BASE, post_url), None,
                'Performing MFA', 'Unable to complete MFA', headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                }, data=urlencode_postdata({
                    'otp': self._get_tfa_info('6 digit number shown on app'),
                }))
            if self.is_logged_in:
                return
            elif 'error-code' in parse_qs(urlh.url):
                err_msg = traverse_obj(mfa, ({find_element(cls='pageMainMsg')}, {clean_html}))
                self._raise_login_error(err_msg or 'MFA session expired')
            elif 'formError' in mfa:
                err_msg = traverse_obj(mfa, (
                    {find_element(cls='formError')}, {find_element(tag='div')}, {clean_html}))
                self._raise_login_error(err_msg or 'MFA challenge failed')

        self._raise_login_error('Unexpected login error', expected=False)


class NiconicoIE(NiconicoBaseIE):
    IE_NAME = 'niconico'
    IE_DESC = 'ニコニコ動画'

    _VALID_URL = r'https?://(?:(?:embed|sp|www)\.)?nicovideo\.jp/watch/(?P<id>(?:[a-z]{2})?\d+)'
    _ERROR_MAP = {
        'FORBIDDEN': {
            'ADMINISTRATOR_DELETE_VIDEO': 'Video unavailable, possibly removed by admins',
            'CHANNEL_MEMBER_ONLY': 'Channel members only',
            'DELETED_CHANNEL_VIDEO': 'Video unavailable, channel was closed',
            'DELETED_COMMUNITY_VIDEO': 'Video unavailable, community deleted or missing',
            'DEFAULT': 'Page unavailable, check the URL',
            'HARMFUL_VIDEO': 'Sensitive content, login required',
            'HIDDEN_VIDEO': 'Video unavailable, set to private',
            'NOT_ALLOWED': 'No permission',
            'PPV_VIDEO': 'PPV video, payment information required',
            'PREMIUM_ONLY': 'Premium members only',
        },
        'INVALID_PARAMETER': {
            'DEFAULT': 'Video unavailable, may not exist or was deleted',
        },
        'MAINTENANCE': {
            'DEFAULT': 'Maintenance is in progress',
        },
        'NOT_FOUND': {
            'DEFAULT': 'Video unavailable, may not exist or was deleted',
            'RIGHT_HOLDER_DELETE_VIDEO': 'Removed by rights-holder request',
        },
        'UNAUTHORIZED': {
            'DEFAULT': 'Invalid session, re-login required',
        },
        'UNKNOWN': {
            'DEFAULT': 'Failed to fetch content',
        },
    }
    _STATUS_MAP = {
        'needs_auth': 'PPV video, payment information required',
        'premium_only': 'Premium members only',
        'subscriber_only': 'Channel members only',
    }
    _TESTS = [{
        'url': 'https://www.nicovideo.jp/watch/1173108780',
        'info_dict': {
            'id': 'sm9',
            'ext': 'mp4',
            'title': '新・豪血寺一族 -煩悩解放 - レッツゴー！陰陽師',
            'availability': 'public',
            'channel': '中の',
            'channel_id': '4',
            'comment_count': int,
            'description': 'md5:b7f6d3e6c29552cc19fdea6a4b7dc194',
            'display_id': '1173108780',
            'duration': 320,
            'genres': ['未設定'],
            'like_count': int,
            'tags': 'mincount:5',
            'thumbnail': r're:https?://img\.cdn\.nimg\.jp/s/nicovideo/thumbnails/.+',
            'timestamp': 1173108780,
            'upload_date': '20070305',
            'uploader': '中の',
            'uploader_id': '4',
            'view_count': int,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.nicovideo.jp/watch/sm8628149',
        'info_dict': {
            'id': 'sm8628149',
            'ext': 'mp4',
            'title': '【東方】Bad Apple!!\u3000ＰＶ【影絵】',
            'availability': 'public',
            'channel': 'あにら',
            'channel_id': '10731211',
            'comment_count': int,
            'description': 'md5:1999669158cb77a45bab123c4fafe1d7',
            'display_id': 'sm8628149',
            'duration': 219,
            'genres': ['ゲーム'],
            'like_count': int,
            'tags': 'mincount:3',
            'thumbnail': r're:https?://img\.cdn\.nimg\.jp/s/nicovideo/thumbnails/.+',
            'timestamp': 1256580802,
            'upload_date': '20091026',
            'uploader': 'あにら',
            'uploader_id': '10731211',
            'view_count': int,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.nicovideo.jp/watch/nm14296458',
        'info_dict': {
            'id': 'nm14296458',
            'ext': 'mp4',
            'title': '【鏡音リン】Dance on media【オリジナル】take2!',
            'availability': 'public',
            'channel': 'りょうた',
            'channel_id': '18822557',
            'comment_count': int,
            'description': 'md5:9368f2b1f4178de64f2602c2f3d6cbf5',
            'display_id': 'nm14296458',
            'duration': 208,
            'genres': ['音楽・サウンド'],
            'like_count': int,
            'tags': 'mincount:1',
            'thumbnail': r're:https?://img\.cdn\.nimg\.jp/s/nicovideo/thumbnails/.+',
            'timestamp': 1304065916,
            'upload_date': '20110429',
            'uploader': 'りょうた',
            'uploader_id': '18822557',
            'view_count': int,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.nicovideo.jp/watch/nl1872567',
        'info_dict': {
            'id': 'nl1872567',
            'ext': 'mp4',
            'title': '【12/25放送分】『生対談!!ひろゆきと戀塚のニコニコを作った人 』前半',
            'availability': 'public',
            'channel': 'nicolive',
            'channel_id': '394',
            'comment_count': int,
            'description': 'md5:79fc3a54cfdc93ecc2b883285149e548',
            'display_id': 'nl1872567',
            'duration': 586,
            'genres': ['エンターテイメント'],
            'like_count': int,
            'tags': 'mincount:3',
            'thumbnail': r're:https?://img\.cdn\.nimg\.jp/s/nicovideo/thumbnails/.+',
            'timestamp': 1198637246,
            'upload_date': '20071226',
            'uploader': 'nicolive',
            'uploader_id': '394',
            'view_count': int,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.nicovideo.jp/watch/so38016254',
        'info_dict': {
            'id': 'so38016254',
            'ext': 'mp4',
            'title': '「のんのんびより のんすとっぷ」 PV',
            'availability': 'public',
            'channel': 'のんのんびより のんすとっぷ',
            'channel_id': 'ch2647028',
            'comment_count': int,
            'description': 'md5:6e2ff55b33e3645d59ef010869cde6a2',
            'display_id': 'so38016254',
            'duration': 114,
            'genres': ['アニメ'],
            'like_count': int,
            'tags': 'mincount:4',
            'thumbnail': r're:https?://img\.cdn\.nimg\.jp/s/nicovideo/thumbnails/.+',
            'timestamp': 1609146000,
            'upload_date': '20201228',
            'uploader': 'のんのんびより のんすとっぷ',
            'uploader_id': 'ch2647028',
            'view_count': int,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # smile official, but marked as user video
        'url': 'https://www.nicovideo.jp/watch/so37602536',
        'info_dict': {
            'id': 'so37602536',
            'ext': 'mp4',
            'title': '田中有紀とゆきだるまと！ 限定放送アーカイブ（第12回）',
            'availability': 'subscriber_only',
            'channel': 'あみあみ16',
            'channel_id': '91072761',
            'comment_count': int,
            'description': 'md5:2ee357ec4e76d7804fb59af77107ab67',
            'display_id': 'so37602536',
            'duration': 980,
            'genres': ['エンターテイメント'],
            'like_count': int,
            'tags': 'count:4',
            'thumbnail': r're:https?://img\.cdn\.nimg\.jp/s/nicovideo/thumbnails/.+',
            'timestamp': 1601377200,
            'upload_date': '20200929',
            'uploader': 'あみあみ16',
            'uploader_id': '91072761',
            'view_count': int,
        },
        'params': {'skip_download': 'm3u8'},
        'skip': 'Channel members only',
    }, {
        'url': 'https://www.nicovideo.jp/watch/so41370536',
        'info_dict': {
            'id': 'so41370536',
            'ext': 'mp4',
            'title': 'ZUN【出演者別】超パーティー2022',
            'availability': 'premium_only',
            'channel': 'ニコニコ超会議チャンネル',
            'channel_id': 'ch2607134',
            'comment_count': int,
            'description': 'md5:5692db5ac40d3a374fc5ec182d0249c3',
            'display_id': 'so41370536',
            'duration': 63,
            'genres': ['音楽・サウンド'],
            'like_count': int,
            'tags': 'mincount:5',
            'thumbnail': r're:https?://img\.cdn\.nimg\.jp/s/nicovideo/thumbnails/.+',
            'timestamp': 1668394800,
            'upload_date': '20221114',
            'uploader': 'ニコニコ超会議チャンネル',
            'uploader_id': 'ch2607134',
            'view_count': int,
        },
        'params': {'skip_download': 'm3u8'},
        'skip': 'Premium members only',
    }, {
        'url': 'https://www.nicovideo.jp/watch/so37574174',
        'info_dict': {
            'id': 'so37574174',
            'ext': 'mp4',
            'title': 'ひぐらしのなく頃に 廿回し編\u3000第1回',
            'availability': 'subscriber_only',
            'channel': '「ひぐらしのなく頃に」オフィシャルチャンネル',
            'channel_id': 'ch2646036',
            'comment_count': int,
            'description': 'md5:5296196d51d9c0b7272b73f9a99c236a',
            'display_id': 'so37574174',
            'duration': 1931,
            'genres': ['ラジオ'],
            'like_count': int,
            'tags': 'mincount:5',
            'thumbnail': r're:https?://img\.cdn\.nimg\.jp/s/nicovideo/thumbnails/.+',
            'timestamp': 1601028000,
            'upload_date': '20200925',
            'uploader': '「ひぐらしのなく頃に」オフィシャルチャンネル',
            'uploader_id': 'ch2646036',
            'view_count': int,
        },
        'params': {'skip_download': 'm3u8'},
        'skip': 'Channel members only',
    }, {
        'url': 'https://www.nicovideo.jp/watch/so44060088',
        'info_dict': {
            'id': 'so44060088',
            'ext': 'mp4',
            'title': '松田的超英雄電波。《仮面ライダーガッチャード 放送終了記念特別番組》',
            'availability': 'subscriber_only',
            'channel': 'あみあみチャンネル',
            'channel_id': 'ch2638921',
            'comment_count': int,
            'description': 'md5:9dec5bb9a172b6d20a255ecb64fbd03e',
            'display_id': 'so44060088',
            'duration': 1881,
            'genres': ['ラジオ'],
            'like_count': int,
            'tags': 'mincount:7',
            'thumbnail': r're:https?://img\.cdn\.nimg\.jp/s/nicovideo/thumbnails/.+',
            'timestamp': 1725361200,
            'upload_date': '20240903',
            'uploader': 'あみあみチャンネル',
            'uploader_id': 'ch2638921',
            'view_count': int,
        },
        'params': {'skip_download': 'm3u8'},
        'skip': 'Channel members only; specified continuous membership period required',
    }]

    def _extract_formats(self, api_data, video_id):
        fmt_filter = lambda _, v: v['isAvailable'] and v['id']
        videos = traverse_obj(api_data, ('media', 'domand', 'videos', fmt_filter))
        audios = traverse_obj(api_data, ('media', 'domand', 'audios', fmt_filter))
        access_key = traverse_obj(api_data, ('media', 'domand', 'accessRightKey', {str}))
        track_id = traverse_obj(api_data, ('client', 'watchTrackId', {str}))
        if not all((videos, audios, access_key, track_id)):
            return

        m3u8_url = self._download_json(
            f'{self._API_BASE}/v1/watch/{video_id}/access-rights/hls',
            video_id, headers={
                'Accept': 'application/json;charset=utf-8',
                'Content-Type': 'application/json',
                'X-Access-Right-Key': access_key,
                'X-Request-With': self._BASE_URL,
                **self._HEADERS,
            }, query={
                'actionTrackId': track_id,
            }, data=json.dumps({
                'outputs': list(itertools.product((v['id'] for v in videos), (a['id'] for a in audios))),
            }).encode(),
        )['data']['contentUrl']
        raw_fmts = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4')

        formats = []
        for a_fmt in traverse_obj(raw_fmts, lambda _, v: v['vcodec'] == 'none'):
            formats.append({
                **a_fmt,
                **traverse_obj(audios, (lambda _, v: a_fmt['format_id'].startswith(v['id']), {
                    'abr': ('bitRate', {float_or_none(scale=1000)}),
                    'asr': ('samplingRate', {int_or_none}),
                    'format_id': ('id', {str}),
                    'quality': ('qualityLevel', {int_or_none}),
                }, any)),
                'acodec': 'aac',
            })

        # Sort first, keeping the lowest-tbr formats
        v_fmts = sorted((fmt for fmt in raw_fmts if fmt['vcodec'] != 'none'), key=lambda f: f['tbr'])
        self._remove_duplicate_formats(v_fmts)
        # Calculate the true vbr/tbr by subtracting the lowest abr
        min_abr = traverse_obj(audios, (..., 'bitRate', {float_or_none(scale=1000)}, all, {min})) or 0
        for v_fmt in v_fmts:
            v_fmt['format_id'] = url_basename(v_fmt['url']).rpartition('.')[0]
            v_fmt['quality'] = traverse_obj(videos, (
                lambda _, v: v['id'] == v_fmt['format_id'], 'qualityLevel', {int_or_none}, any)) or -1
            v_fmt['tbr'] -= min_abr
        formats.extend(v_fmts)

        return formats

    def _real_extract(self, url):
        video_id = self._match_id(url)

        path = 'v3' if self.is_logged_in else 'v3_guest'
        api_resp = self._download_json(
            f'{self._BASE_URL}/api/watch/{path}/{video_id}', video_id,
            'Downloading API JSON', 'Unable to fetch data', headers={
                **self._HEADERS,
                **self.geo_verification_headers(),
            }, query={
                'actionTrackId': f'AAAAAAAAAA_{round(time_seconds() * 1000)}',
            }, expected_status=[400, 404])

        api_data = api_resp['data']
        scheduled_time = traverse_obj(api_data, ('publishScheduledAt', {str}))
        status = traverse_obj(api_resp, ('meta', 'status', {int}))

        if status != 200:
            err_code = traverse_obj(api_resp, ('meta', 'errorCode', {str.upper}))
            reason_code = traverse_obj(api_data, ('reasonCode', {str_or_none}))
            err_msg = traverse_obj(self._ERROR_MAP, (err_code, (reason_code, 'DEFAULT'), {str}, any))

            if reason_code in ('DOMESTIC_VIDEO', 'HIGH_RISK_COUNTRY_VIDEO'):
                self.raise_geo_restricted(countries=self._GEO_COUNTRIES)
            elif reason_code == 'HARMFUL_VIDEO' and traverse_obj(api_data, (
                'viewer', 'allowSensitiveContents', {bool},
            )) is False:
                err_msg = 'Sensitive content, adjust display settings to watch'
            elif reason_code == 'HIDDEN_VIDEO' and scheduled_time:
                err_msg = f'This content is scheduled to be released at {scheduled_time}'
            elif reason_code in ('CHANNEL_MEMBER_ONLY', 'HARMFUL_VIDEO', 'HIDDEN_VIDEO', 'PPV_VIDEO', 'PREMIUM_ONLY'):
                self.raise_login_required(err_msg)

            if err_msg:
                raise ExtractorError(err_msg, expected=True)
            if status and status >= 500:
                raise ExtractorError('Service temporarily unavailable', expected=True)
            raise ExtractorError(f'API returned error status {status}')

        availability = self._availability(**traverse_obj(api_data, ('payment', 'video', {
            'needs_auth': (('isContinuationBenefit', 'isPpv'), {bool}, any),
            'needs_subscription': ('isAdmission', {bool}),
            'needs_premium': ('isPremium', {bool}),
        }))) or 'public'

        formats = self._extract_formats(api_data, video_id)
        err_msg = self._STATUS_MAP.get(availability)
        if not formats and err_msg:
            self.raise_login_required(err_msg, metadata_available=True)

        thumb_prefs = qualities(['url', 'middleUrl', 'largeUrl', 'player', 'ogp'])

        return {
            'availability': availability,
            'display_id': video_id,
            'formats': formats,
            'genres': traverse_obj(api_data, ('genre', 'label', {str}, filter, all, filter)),
            'release_timestamp': parse_iso8601(scheduled_time),
            'subtitles': self.extract_subtitles(video_id, api_data),
            'tags': traverse_obj(api_data, ('tag', 'items', ..., 'name', {str}, filter, all, filter)),
            'thumbnails': [{
                'ext': 'jpg',
                'id': key,
                'preference': thumb_prefs(key),
                'url': url,
                **parse_resolution(url, lenient=True),
            } for key, url in traverse_obj(api_data, (
                'video', 'thumbnail', {dict}), default={}).items()],
            **traverse_obj(api_data, (('channel', 'owner'), any, {
                'channel': (('name', 'nickname'), {str}, any),
                'channel_id': ('id', {str_or_none}),
                'uploader': (('name', 'nickname'), {str}, any),
                'uploader_id': ('id', {str_or_none}),
            })),
            **traverse_obj(api_data, ('video', {
                'id': ('id', {str_or_none}),
                'title': ('title', {str}),
                'description': ('description', {clean_html}, filter),
                'duration': ('duration', {int_or_none}),
                'timestamp': ('registeredAt', {parse_iso8601}),
            })),
            **traverse_obj(api_data, ('video', 'count', {
                'comment_count': ('comment', {int_or_none}),
                'like_count': ('like', {int_or_none}),
                'view_count': ('view', {int_or_none}),
            })),
        }

    def _get_subtitles(self, video_id, api_data):
        comments_info = traverse_obj(api_data, ('comment', 'nvComment', {dict})) or {}
        if not comments_info.get('server'):
            return

        danmaku = traverse_obj(self._download_json(
            f'{comments_info["server"]}/v1/threads', video_id,
            'Downloading comments', 'Failed to download comments', headers={
                'Content-Type': 'text/plain;charset=UTF-8',
                'Origin': self._BASE_URL,
                'Referer': f'{self._BASE_URL}/',
                'X-Client-Os-Type': 'others',
                **self._HEADERS,
            }, data=json.dumps({
                'additionals': {},
                'params': comments_info.get('params'),
                'threadKey': comments_info.get('threadKey'),
            }).encode(), fatal=False,
        ), ('data', 'threads', ..., 'comments', ...))

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


class NiconicoLiveIE(NiconicoBaseIE):
    IE_NAME = 'niconico:live'
    IE_DESC = 'ニコニコ生放送'
    _VALID_URL = r'https?://(?:sp\.)?live2?\.nicovideo\.jp/(?:watch|gate)/(?P<id>lv\d+)'
    _TESTS = [{
        'url': 'https://live.nicovideo.jp/watch/lv329299587',
        'info_dict': {
            'id': 'lv329299587',
            'ext': 'mp4',
            'title': str,
            'channel': 'ニコニコエンタメチャンネル',
            'channel_id': 'ch2640322',
            'channel_url': 'https://ch.nicovideo.jp/channel/ch2640322',
            'comment_count': int,
            'description': 'md5:281edd7f00309e99ec46a87fb16d7033',
            'live_status': 'is_live',
            'thumbnail': r're:https?://.+',
            'timestamp': 1608803400,
            'upload_date': '20201224',
            'uploader': '株式会社ドワンゴ',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://live.nicovideo.jp/watch/lv331050399',
        'info_dict': {
            'id': 'lv331050399',
            'ext': 'mp4',
            'title': str,
            'age_limit': 18,
            'channel': 'みんなのおもちゃ REBOOT',
            'channel_id': 'ch2642088',
            'channel_url': 'https://ch.nicovideo.jp/channel/ch2642088',
            'comment_count': int,
            'description': 'md5:8d0bb5beaca73b911725478a1e7c7b91',
            'live_status': 'is_live',
            'thumbnail': r're:https?://.+',
            'timestamp': 1617029400,
            'upload_date': '20210329',
            'uploader': '株式会社ドワンゴ',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage, urlh = self._download_webpage_handle(url, video_id, expected_status=404)
        if err_msg := traverse_obj(webpage, ({find_element(cls='message')}, {clean_html})):
            raise ExtractorError(err_msg, expected=True)

        age_limit = 18 if 'age_auth' in urlh.url else None
        if age_limit:
            if not self.is_logged_in:
                self.raise_login_required('Login is required to access age-restricted content')

            my = self._download_webpage('https://www.nicovideo.jp/my', None, 'Checking age verification')
            if traverse_obj(my, (
                {find_element(id='js-initial-userpage-data', html=True)}, {extract_attributes},
                'data-environment', {json.loads}, 'allowSensitiveContents', {bool},
            )):
                self._set_cookie('.nicovideo.jp', 'age_auth', '1')
                webpage = self._download_webpage(url, video_id)
            else:
                raise ExtractorError('Sensitive content setting must be enabled', expected=True)

        embedded_data = traverse_obj(webpage, (
            {find_element(tag='script', id='embedded-data', html=True)},
            {extract_attributes}, 'data-props', {json.loads}))
        frontend_id = traverse_obj(embedded_data, ('site', 'frontendId', {str_or_none}), default='9')

        ws_url = traverse_obj(embedded_data, (
            'site', 'relive', 'webSocketUrl', {url_or_none}, {require('websocket URL')}))
        ws_url = update_url_query(ws_url, {'frontend_id': frontend_id})
        ws = self._request_webpage(
            ws_url, video_id, 'Connecting to WebSocket server',
            headers={'Origin': 'https://live.nicovideo.jp'})

        self.write_debug('Sending HLS server request')
        ws.send(json.dumps({
            'data': {
                'reconnect': False,
                'room': {
                    'commentable': True,
                    'protocol': 'webSocket',
                },
                'stream': {
                    'accessRightMethod': 'single_cookie',
                    'chasePlay': False,
                    'latency': 'high',
                    'protocol': 'hls',
                    'quality': 'abr',
                },
            },
            'type': 'startWatching',
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
                message = traverse_obj(data, ('body', 'code', {str_or_none}), default=recv)
                raise ExtractorError(message)
            elif self.get_param('verbose', False):
                self.write_debug(f'Server response: {truncate_string(recv, 100)}')

        title = traverse_obj(embedded_data, ('program', 'title')) or self._html_search_meta(
            ('og:title', 'twitter:title'), webpage, 'live title', fatal=False)

        raw_thumbs = traverse_obj(embedded_data, ('program', 'thumbnail', {dict})) or {}
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
                expire_time=unified_timestamp(cookie.get('expires')), path=cookie['path'], secure=cookie['secure'])

        q_iter = (q for q in qualities[1:] if not q.startswith('audio_'))  # ignore initial 'abr'
        a_map = {96: 'audio_low', 192: 'audio_high'}

        formats = self._extract_m3u8_formats(m3u8_url, video_id, ext='mp4', live=True)
        for fmt in formats:
            fmt['protocol'] = 'niconico_live'
            if fmt.get('acodec') == 'none':
                fmt['format_id'] = next(q_iter, fmt['format_id'])
            elif fmt.get('vcodec') == 'none':
                abr = parse_bitrate(fmt['url'].lower())
                fmt.update({
                    'abr': abr,
                    'acodec': 'mp4a.40.2',
                    'format_id': a_map.get(abr, fmt['format_id']),
                })

        return {
            'id': video_id,
            'title': title,
            'age_limit': age_limit,
            'downloader_options': {
                'max_quality': traverse_obj(embedded_data, ('program', 'stream', 'maxQuality', {str})) or 'normal',
                'ws': ws,
                'ws_url': ws_url,
            },
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
