import datetime as dt
import functools

from .common import InfoExtractor
from ..networking import Request
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    UserNotLive,
    determine_ext,
    filter_dict,
    int_or_none,
    orderedSet,
    parse_iso8601,
    url_or_none,
    urlencode_postdata,
    urljoin,
)
from ..utils.traversal import traverse_obj


class AfreecaTVBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'afreecatv'

    def _perform_login(self, username, password):
        login_form = {
            'szWork': 'login',
            'szType': 'json',
            'szUid': username,
            'szPassword': password,
            'isSaveId': 'false',
            'szScriptVar': 'oLoginRet',
            'szAction': '',
        }

        response = self._download_json(
            'https://login.sooplive.co.kr/app/LoginAction.php', None,
            'Logging in', data=urlencode_postdata(login_form))

        _ERRORS = {
            -4: 'Your account has been suspended due to a violation of our terms and policies.',
            -5: 'https://member.sooplive.co.kr/app/user_delete_progress.php',
            -6: 'https://login.sooplive.co.kr/membership/changeMember.php',
            -8: "Hello! Soop here.\nThe username you have entered belongs to \n an account that requires a legal guardian's consent. \nIf you wish to use our services without restriction, \nplease make sure to go through the necessary verification process.",
            -9: 'https://member.sooplive.co.kr/app/pop_login_block.php',
            -11: 'https://login.sooplive.co.kr/afreeca/second_login.php',
            -12: 'https://member.sooplive.co.kr/app/user_security.php',
            0: 'The username does not exist or you have entered the wrong password.',
            -1: 'The username does not exist or you have entered the wrong password.',
            -3: 'You have entered your username/password incorrectly.',
            -7: 'You cannot use your Global Soop account to access Korean Soop.',
            -10: 'Sorry for the inconvenience. \nYour account has been blocked due to an unauthorized access. \nPlease contact our Help Center for assistance.',
            -32008: 'You have failed to log in. Please contact our Help Center.',
        }

        result = int_or_none(response.get('RESULT'))
        if result != 1:
            error = _ERRORS.get(result, 'You have failed to log in.')
            raise ExtractorError(
                f'Unable to login: {self.IE_NAME} said: {error}',
                expected=True)

    def _call_api(self, endpoint, display_id, data=None, headers=None, query=None):
        return self._download_json(Request(
            f'https://api.m.sooplive.co.kr/{endpoint}',
            data=data, headers=headers, query=query,
            extensions={'legacy_ssl': True}), display_id,
            'Downloading API JSON', 'Unable to download API JSON')

    @staticmethod
    def _fixup_thumb(thumb_url):
        if not url_or_none(thumb_url):
            return None
        # Core would determine_ext as 'php' from the url, so we need to provide the real ext
        # See: https://github.com/yt-dlp/yt-dlp/issues/11537
        return [{'url': thumb_url, 'ext': 'jpg'}]


class AfreecaTVIE(AfreecaTVBaseIE):
    IE_NAME = 'soop'
    IE_DESC = 'sooplive.co.kr'
    _VALID_URL = r'https?://vod\.(?:sooplive\.co\.kr|afreecatv\.com)/(?:PLAYER/STATION|player)/(?P<id>\d+)/?(?:$|[?#&])'
    _TESTS = [{
        'url': 'https://vod.sooplive.co.kr/player/96753363',
        'info_dict': {
            'id': '20230108_9FF5BEE1_244432674_1',
            'ext': 'mp4',
            'uploader_id': 'rlantnghks',
            'uploader': '페이즈으',
            'duration': 10840,
            'thumbnail': r're:https?://videoimg\.(?:sooplive\.co\.kr|afreecatv\.com)/.+',
            'upload_date': '20230108',
            'timestamp': 1673186405,
            'title': '젠지 페이즈',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # non standard key
        'url': 'http://vod.sooplive.co.kr/PLAYER/STATION/20515605',
        'info_dict': {
            'id': '20170411_BE689A0E_190960999_1_2_h',
            'ext': 'mp4',
            'title': '혼자사는여자집',
            'thumbnail': r're:https?://(?:video|st)img\.(?:sooplive\.co\.kr|afreecatv\.com)/.+',
            'uploader': '♥이슬이',
            'uploader_id': 'dasl8121',
            'upload_date': '20170411',
            'timestamp': 1491929865,
            'duration': 213,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # adult content
        'url': 'https://vod.sooplive.co.kr/player/97267690',
        'info_dict': {
            'id': '20180327_27901457_202289533_1',
            'ext': 'mp4',
            'title': '[생]빨개요♥ (part 1)',
            'thumbnail': r're:https?://(?:video|st)img\.(?:sooplive\.co\.kr|afreecatv\.com)/.+',
            'uploader': '[SA]서아',
            'uploader_id': 'bjdyrksu',
            'upload_date': '20180327',
            'duration': 3601,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'The VOD does not exist',
    }, {
        # adult content
        'url': 'https://vod.sooplive.co.kr/player/70395877',
        'only_matching': True,
    }, {
        # subscribers only
        'url': 'https://vod.sooplive.co.kr/player/104647403',
        'only_matching': True,
    }, {
        # private
        'url': 'https://vod.sooplive.co.kr/player/81669846',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._call_api(
            'station/video/a/view', video_id, headers={'Referer': url},
            data=urlencode_postdata({
                'nTitleNo': video_id,
                'nApiLevel': 10,
            }))['data']

        error_code = traverse_obj(data, ('code', {int}))
        if error_code == -6221:
            raise ExtractorError('The VOD does not exist', expected=True)
        elif error_code == -6205:
            raise ExtractorError('This VOD is private', expected=True)

        common_info = traverse_obj(data, {
            'title': ('title', {str}),
            'uploader': ('writer_nick', {str}),
            'uploader_id': ('bj_id', {str}),
            'duration': ('total_file_duration', {int_or_none(scale=1000)}),
            'thumbnails': ('thumb', {self._fixup_thumb}),
        })

        entries = []
        for file_num, file_element in enumerate(
                traverse_obj(data, ('files', lambda _, v: url_or_none(v['file']))), start=1):
            file_url = file_element['file']
            if determine_ext(file_url) == 'm3u8':
                formats = self._extract_m3u8_formats(
                    file_url, video_id, 'mp4', m3u8_id='hls',
                    note=f'Downloading part {file_num} m3u8 information')
            else:
                formats = [{
                    'url': file_url,
                    'format_id': 'http',
                }]

            entries.append({
                **common_info,
                'id': file_element.get('file_info_key') or f'{video_id}_{file_num}',
                'title': f'{common_info.get("title") or "Untitled"} (part {file_num})',
                'formats': formats,
                **traverse_obj(file_element, {
                    'duration': ('duration', {int_or_none(scale=1000)}),
                    'timestamp': ('file_start', {parse_iso8601(delimiter=' ', timezone=dt.timedelta(hours=9))}),
                }),
            })

        if traverse_obj(data, ('adult_status', {str})) == 'notLogin':
            if not entries:
                self.raise_login_required(
                    'Only users older than 19 are able to watch this video', method='password')
            self.report_warning(
                'In accordance with local laws and regulations, underage users are '
                'restricted from watching adult content. Only content suitable for all '
                f'ages will be downloaded. {self._login_hint("password")}')

        if not entries and traverse_obj(data, ('sub_upload_type', {str})):
            self.raise_login_required('This VOD is for subscribers only', method='password')

        if len(entries) == 1:
            return {
                **entries[0],
                'title': common_info.get('title'),
            }

        common_info['timestamp'] = traverse_obj(entries, (..., 'timestamp'), get_all=False)

        return self.playlist_result(entries, video_id, multi_video=True, **common_info)


class AfreecaTVCatchStoryIE(AfreecaTVBaseIE):
    IE_NAME = 'soop:catchstory'
    IE_DESC = 'sooplive.co.kr catch story'
    _VALID_URL = r'https?://vod\.(?:sooplive\.co\.kr|afreecatv\.com)/player/(?P<id>\d+)/catchstory'
    _TESTS = [{
        'url': 'https://vod.sooplive.co.kr/player/103247/catchstory',
        'info_dict': {
            'id': '103247',
        },
        'playlist_count': 2,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._call_api(
            'catchstory/a/view', video_id, headers={'Referer': url},
            query={'aStoryListIdx': '', 'nStoryIdx': video_id})

        return self.playlist_result(self._entries(data), video_id)

    def _entries(self, data):
        # 'files' is always a list with 1 element
        yield from traverse_obj(data, (
            'data', lambda _, v: v['story_type'] == 'catch',
            'catch_list', lambda _, v: v['files'][0]['file'], {
                'id': ('files', 0, 'file_info_key', {str}),
                'url': ('files', 0, 'file', {url_or_none}),
                'duration': ('files', 0, 'duration', {int_or_none(scale=1000)}),
                'title': ('title', {str}),
                'uploader': ('writer_nick', {str}),
                'uploader_id': ('writer_id', {str}),
                'thumbnails': ('thumb', {self._fixup_thumb}),
                'timestamp': ('write_timestamp', {int_or_none}),
            }))


class AfreecaTVLiveIE(AfreecaTVBaseIE):
    IE_NAME = 'soop:live'
    IE_DESC = 'sooplive.co.kr livestreams'
    _VALID_URL = r'https?://play\.(?:sooplive\.co\.kr|afreecatv\.com)/(?P<id>[^/?#]+)(?:/(?P<bno>\d+))?'
    _TESTS = [{
        'url': 'https://play.sooplive.co.kr/pyh3646/237852185',
        'info_dict': {
            'id': '237852185',
            'ext': 'mp4',
            'title': '【 우루과이 오늘은 무슨일이? 】',
            'uploader': '박진우[JINU]',
            'uploader_id': 'pyh3646',
            'timestamp': 1640661495,
            'is_live': True,
        },
        'skip': 'Livestream has ended',
    }, {
        'url': 'https://play.sooplive.co.kr/pyh3646/237852185',
        'only_matching': True,
    }, {
        'url': 'https://play.sooplive.co.kr/pyh3646',
        'only_matching': True,
    }]

    _LIVE_API_URL = 'https://live.sooplive.co.kr/afreeca/player_live_api.php'
    _WORKING_CDNS = [
        'gcp_cdn',  # live-global-cdn-v02.sooplive.co.kr
        'gs_cdn_pc_app',  # pc-app.stream.sooplive.co.kr
        'gs_cdn_mobile_web',  # mobile-web.stream.sooplive.co.kr
        'gs_cdn_pc_web',  # pc-web.stream.sooplive.co.kr
    ]
    _BAD_CDNS = [
        'gs_cdn',  # chromecast.afreeca.gscdn.com (cannot resolve)
        'gs_cdn_chromecast',  # chromecast.stream.sooplive.co.kr (HTTP Error 400)
        'azure_cdn',  # live-global-cdn-v01.sooplive.co.kr (cannot resolve)
        'aws_cf',  # live-global-cdn-v03.sooplive.co.kr (cannot resolve)
        'kt_cdn',  # kt.stream.sooplive.co.kr (HTTP Error 400)
    ]

    def _extract_formats(self, channel_info, broadcast_no, aid):
        stream_base_url = channel_info.get('RMD') or 'https://livestream-manager.sooplive.co.kr'

        # If user has not passed CDN IDs, try API-provided CDN ID followed by other working CDN IDs
        default_cdn_ids = orderedSet([
            *traverse_obj(channel_info, ('CDN', {str}, all, lambda _, v: v not in self._BAD_CDNS)),
            *self._WORKING_CDNS,
        ])
        cdn_ids = self._configuration_arg('cdn', default_cdn_ids)

        for attempt, cdn_id in enumerate(cdn_ids, start=1):
            m3u8_url = traverse_obj(self._download_json(
                urljoin(stream_base_url, 'broad_stream_assign.html'), broadcast_no,
                f'Downloading {cdn_id} stream info', f'Unable to download {cdn_id} stream info',
                fatal=False, query={
                    'return_type': cdn_id,
                    'broad_key': f'{broadcast_no}-common-master-hls',
                }), ('view_url', {url_or_none}))
            try:
                return self._extract_m3u8_formats(
                    m3u8_url, broadcast_no, 'mp4', m3u8_id='hls', query={'aid': aid},
                    headers={'Referer': 'https://play.sooplive.co.kr/'})
            except ExtractorError as e:
                if attempt == len(cdn_ids):
                    raise
                self.report_warning(
                    f'{e.cause or e.msg}. Retrying... (attempt {attempt} of {len(cdn_ids)})')

    def _real_extract(self, url):
        broadcaster_id, broadcast_no = self._match_valid_url(url).group('id', 'bno')
        channel_info = traverse_obj(self._download_json(
            self._LIVE_API_URL, broadcaster_id, data=urlencode_postdata({'bid': broadcaster_id})),
            ('CHANNEL', {dict})) or {}

        broadcaster_id = channel_info.get('BJID') or broadcaster_id
        broadcast_no = channel_info.get('BNO') or broadcast_no
        if not broadcast_no:
            result = channel_info.get('RESULT')
            if result == 0:
                raise UserNotLive(video_id=broadcaster_id)
            elif result == -6:
                self.raise_login_required(
                    'This channel is streaming for subscribers only', method='password')
            raise ExtractorError('Unable to extract broadcast number')

        password = self.get_param('videopassword')
        if channel_info.get('BPWD') == 'Y' and password is None:
            raise ExtractorError(
                'This livestream is protected by a password, use the --video-password option',
                expected=True)

        token_info = traverse_obj(self._download_json(
            self._LIVE_API_URL, broadcast_no, 'Downloading access token for stream',
            'Unable to download access token for stream', data=urlencode_postdata(filter_dict({
                'bno': broadcast_no,
                'stream_type': 'common',
                'type': 'aid',
                'quality': 'master',
                'pwd': password,
            }))), ('CHANNEL', {dict})) or {}
        aid = token_info.get('AID')
        if not aid:
            result = token_info.get('RESULT')
            if result == 0:
                raise ExtractorError('This livestream has ended', expected=True)
            elif result == -6:
                self.raise_login_required('This livestream is for subscribers only', method='password')
            raise ExtractorError('Unable to extract access token')

        formats = self._extract_formats(channel_info, broadcast_no, aid)

        station_info = traverse_obj(self._download_json(
            'https://st.sooplive.co.kr/api/get_station_status.php', broadcast_no,
            'Downloading channel metadata', 'Unable to download channel metadata',
            query={'szBjId': broadcaster_id}, fatal=False), {dict}) or {}

        return {
            'id': broadcast_no,
            'title': channel_info.get('TITLE') or station_info.get('station_title'),
            'uploader': channel_info.get('BJNICK') or station_info.get('station_name'),
            'uploader_id': broadcaster_id,
            'timestamp': parse_iso8601(station_info.get('broad_start'), delimiter=' ', timezone=dt.timedelta(hours=9)),
            'formats': formats,
            'is_live': True,
            'http_headers': {'Referer': url},
        }


class AfreecaTVUserIE(AfreecaTVBaseIE):
    IE_NAME = 'soop:user'
    _VALID_URL = r'https?://ch\.(?:sooplive\.co\.kr|afreecatv\.com)/(?P<id>[^/?#]+)/vods/?(?P<slug_type>[^/?#]+)?'
    _TESTS = [{
        'url': 'https://ch.sooplive.co.kr/ryuryu24/vods/review',
        'info_dict': {
            '_type': 'playlist',
            'id': 'ryuryu24',
            'title': 'ryuryu24 - review',
        },
        'playlist_count': 218,
    }, {
        'url': 'https://ch.sooplive.co.kr/parang1995/vods/highlight',
        'info_dict': {
            '_type': 'playlist',
            'id': 'parang1995',
            'title': 'parang1995 - highlight',
        },
        'playlist_count': 997,
    }, {
        'url': 'https://ch.sooplive.co.kr/ryuryu24/vods',
        'info_dict': {
            '_type': 'playlist',
            'id': 'ryuryu24',
            'title': 'ryuryu24 - all',
        },
        'playlist_count': 221,
    }, {
        'url': 'https://ch.sooplive.co.kr/ryuryu24/vods/balloonclip',
        'info_dict': {
            '_type': 'playlist',
            'id': 'ryuryu24',
            'title': 'ryuryu24 - balloonclip',
        },
        'playlist_count': 0,
    }]
    _PER_PAGE = 60

    def _fetch_page(self, user_id, user_type, page):
        page += 1
        info = self._download_json(f'https://chapi.sooplive.co.kr/api/{user_id}/vods/{user_type}', user_id,
                                   query={'page': page, 'per_page': self._PER_PAGE, 'orderby': 'reg_date'},
                                   note=f'Downloading {user_type} video page {page}')
        for item in info['data']:
            yield self.url_result(
                f'https://vod.sooplive.co.kr/player/{item["title_no"]}/', AfreecaTVIE, item['title_no'])

    def _real_extract(self, url):
        user_id, user_type = self._match_valid_url(url).group('id', 'slug_type')
        user_type = user_type or 'all'
        entries = OnDemandPagedList(functools.partial(self._fetch_page, user_id, user_type), self._PER_PAGE)
        return self.playlist_result(entries, user_id, f'{user_id} - {user_type}')
