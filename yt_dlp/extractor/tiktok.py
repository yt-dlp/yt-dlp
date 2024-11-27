import functools
import itertools
import json
import random
import re
import string
import time
import urllib.parse
import uuid

from .common import InfoExtractor
from ..networking import HEADRequest
from ..utils import (
    ExtractorError,
    UnsupportedError,
    UserNotLive,
    determine_ext,
    filter_dict,
    format_field,
    int_or_none,
    join_nonempty,
    merge_dicts,
    mimetype2ext,
    parse_qs,
    qualities,
    srt_subtitles_timecode,
    str_or_none,
    traverse_obj,
    try_call,
    try_get,
    url_or_none,
    urlencode_postdata,
)


class TikTokBaseIE(InfoExtractor):
    _UPLOADER_URL_FORMAT = 'https://www.tiktok.com/@%s'
    _WEBPAGE_HOST = 'https://www.tiktok.com/'
    QUALITIES = ('360p', '540p', '720p', '1080p')

    _APP_INFO_DEFAULTS = {
        # unique "install id"
        'iid': None,
        # TikTok (KR/PH/TW/TH/VN) = trill, TikTok (rest of world) = musical_ly, Douyin = aweme
        'app_name': 'musical_ly',
        'app_version': '35.1.3',
        'manifest_app_version': '2023501030',
        # "app id": aweme = 1128, trill = 1180, musical_ly = 1233, universal = 0
        'aid': '0',
    }
    _APP_INFO_POOL = None
    _APP_INFO = None
    _APP_USER_AGENT = None

    @functools.cached_property
    def _KNOWN_APP_INFO(self):
        # If we have a genuine device ID, we may not need any IID
        default = [''] if self._KNOWN_DEVICE_ID else []
        return self._configuration_arg('app_info', default, ie_key=TikTokIE)

    @functools.cached_property
    def _KNOWN_DEVICE_ID(self):
        return self._configuration_arg('device_id', [None], ie_key=TikTokIE)[0]

    @functools.cached_property
    def _DEVICE_ID(self):
        return self._KNOWN_DEVICE_ID or str(random.randint(7250000000000000000, 7351147085025500000))

    @functools.cached_property
    def _API_HOSTNAME(self):
        return self._configuration_arg(
            'api_hostname', ['api16-normal-c-useast1a.tiktokv.com'], ie_key=TikTokIE)[0]

    def _get_next_app_info(self):
        if self._APP_INFO_POOL is None:
            defaults = {
                key: self._configuration_arg(key, [default], ie_key=TikTokIE)[0]
                for key, default in self._APP_INFO_DEFAULTS.items()
                if key != 'iid'
            }
            self._APP_INFO_POOL = [
                {**defaults, **dict(
                    (k, v) for k, v in zip(self._APP_INFO_DEFAULTS, app_info.split('/')) if v
                )} for app_info in self._KNOWN_APP_INFO
            ]

        if not self._APP_INFO_POOL:
            return False

        self._APP_INFO = self._APP_INFO_POOL.pop(0)

        app_name = self._APP_INFO['app_name']
        version = self._APP_INFO['manifest_app_version']
        if app_name == 'musical_ly':
            package = f'com.zhiliaoapp.musically/{version}'
        else:  # trill, aweme
            package = f'com.ss.android.ugc.{app_name}/{version}'
        self._APP_USER_AGENT = f'{package} (Linux; U; Android 13; en_US; Pixel 7; Build/TD1A.220804.031; Cronet/58.0.2991.0)'

        return True

    @staticmethod
    def _create_url(user_id, video_id):
        return f'https://www.tiktok.com/@{user_id or "_"}/video/{video_id}'

    def _get_sigi_state(self, webpage, display_id):
        return self._search_json(
            r'<script[^>]+\bid="(?:SIGI_STATE|sigi-persisted-data)"[^>]*>', webpage,
            'sigi state', display_id, end_pattern=r'</script>', default={})

    def _get_universal_data(self, webpage, display_id):
        return traverse_obj(self._search_json(
            r'<script[^>]+\bid="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>', webpage,
            'universal data', display_id, end_pattern=r'</script>', default={}),
            ('__DEFAULT_SCOPE__', {dict})) or {}

    def _call_api_impl(self, ep, video_id, query=None, data=None, headers=None, fatal=True,
                       note='Downloading API JSON', errnote='Unable to download API page'):
        self._set_cookie(self._API_HOSTNAME, 'odin_tt', ''.join(random.choices('0123456789abcdef', k=160)))
        webpage_cookies = self._get_cookies(self._WEBPAGE_HOST)
        if webpage_cookies.get('sid_tt'):
            self._set_cookie(self._API_HOSTNAME, 'sid_tt', webpage_cookies['sid_tt'].value)
        return self._download_json(
            f'https://{self._API_HOSTNAME}/aweme/v1/{ep}/', video_id=video_id,
            fatal=fatal, note=note, errnote=errnote, headers={
                'User-Agent': self._APP_USER_AGENT,
                'Accept': 'application/json',
                **(headers or {}),
            }, query=query, data=data)

    def _build_api_query(self, query):
        return filter_dict({
            **query,
            'device_platform': 'android',
            'os': 'android',
            'ssmix': 'a',
            '_rticket': int(time.time() * 1000),
            'cdid': str(uuid.uuid4()),
            'channel': 'googleplay',
            'aid': self._APP_INFO['aid'],
            'app_name': self._APP_INFO['app_name'],
            'version_code': ''.join(f'{int(v):02d}' for v in self._APP_INFO['app_version'].split('.')),
            'version_name': self._APP_INFO['app_version'],
            'manifest_version_code': self._APP_INFO['manifest_app_version'],
            'update_version_code': self._APP_INFO['manifest_app_version'],
            'ab_version': self._APP_INFO['app_version'],
            'resolution': '1080*2400',
            'dpi': 420,
            'device_type': 'Pixel 7',
            'device_brand': 'Google',
            'language': 'en',
            'os_api': '29',
            'os_version': '13',
            'ac': 'wifi',
            'is_pad': '0',
            'current_region': 'US',
            'app_type': 'normal',
            'sys_region': 'US',
            'last_install_time': int(time.time()) - random.randint(86400, 1123200),
            'timezone_name': 'America/New_York',
            'residence': 'US',
            'app_language': 'en',
            'timezone_offset': '-14400',
            'host_abi': 'armeabi-v7a',
            'locale': 'en',
            'ac2': 'wifi5g',
            'uoo': '1',
            'carrier_region': 'US',
            'op_region': 'US',
            'build_number': self._APP_INFO['app_version'],
            'region': 'US',
            'ts': int(time.time()),
            'iid': self._APP_INFO.get('iid'),
            'device_id': self._DEVICE_ID,
            'openudid': ''.join(random.choices('0123456789abcdef', k=16)),
        })

    def _call_api(self, ep, video_id, query=None, data=None, headers=None, fatal=True,
                  note='Downloading API JSON', errnote='Unable to download API page'):
        if not self._APP_INFO and not self._get_next_app_info():
            message = 'No working app info is available'
            if fatal:
                raise ExtractorError(message, expected=True)
            else:
                self.report_warning(message)
                return

        max_tries = len(self._APP_INFO_POOL) + 1  # _APP_INFO_POOL + _APP_INFO
        for count in itertools.count(1):
            self.write_debug(str(self._APP_INFO))
            real_query = self._build_api_query(query or {})
            try:
                return self._call_api_impl(
                    ep, video_id, query=real_query, data=data, headers=headers,
                    fatal=fatal, note=note, errnote=errnote)
            except ExtractorError as e:
                if isinstance(e.cause, json.JSONDecodeError) and e.cause.pos == 0:
                    message = str(e.cause or e.msg)
                    if not self._get_next_app_info():
                        if fatal:
                            raise
                        else:
                            self.report_warning(message)
                            return
                    self.report_warning(f'{message}. Retrying... (attempt {count} of {max_tries})')
                    continue
                raise

    def _extract_aweme_app(self, aweme_id):
        aweme_detail = traverse_obj(
            self._call_api('multi/aweme/detail', aweme_id, data=urlencode_postdata({
                'aweme_ids': f'[{aweme_id}]',
                'request_source': '0',
            }), headers={'X-Argus': ''}), ('aweme_details', 0, {dict}))
        if not aweme_detail:
            raise ExtractorError('Unable to extract aweme detail info', video_id=aweme_id)
        return self._parse_aweme_video_app(aweme_detail)

    def _extract_web_data_and_status(self, url, video_id, fatal=True):
        video_data, status = {}, -1

        res = self._download_webpage_handle(url, video_id, fatal=fatal, headers={'User-Agent': 'Mozilla/5.0'})
        if res is False:
            return video_data, status

        webpage, urlh = res
        if urllib.parse.urlparse(urlh.url).path == '/login':
            message = 'TikTok is requiring login for access to this content'
            if fatal:
                self.raise_login_required(message)
            self.report_warning(f'{message}. {self._login_hint()}')
            return video_data, status

        if universal_data := self._get_universal_data(webpage, video_id):
            self.write_debug('Found universal data for rehydration')
            status = traverse_obj(universal_data, ('webapp.video-detail', 'statusCode', {int})) or 0
            video_data = traverse_obj(universal_data, ('webapp.video-detail', 'itemInfo', 'itemStruct', {dict}))

        elif sigi_data := self._get_sigi_state(webpage, video_id):
            self.write_debug('Found sigi state data')
            status = traverse_obj(sigi_data, ('VideoPage', 'statusCode', {int})) or 0
            video_data = traverse_obj(sigi_data, ('ItemModule', video_id, {dict}))

        elif next_data := self._search_nextjs_data(webpage, video_id, default={}):
            self.write_debug('Found next.js data')
            status = traverse_obj(next_data, ('props', 'pageProps', 'statusCode', {int})) or 0
            video_data = traverse_obj(next_data, ('props', 'pageProps', 'itemInfo', 'itemStruct', {dict}))

        elif fatal:
            raise ExtractorError('Unable to extract webpage video data')

        return video_data, status

    def _get_subtitles(self, aweme_detail, aweme_id, user_name):
        # TODO: Extract text positioning info

        EXT_MAP = {  # From lowest to highest preference
            'creator_caption': 'json',
            'srt': 'srt',
            'webvtt': 'vtt',
        }
        preference = qualities(tuple(EXT_MAP.values()))

        subtitles = {}

        # aweme/detail endpoint subs
        captions_info = traverse_obj(
            aweme_detail, ('interaction_stickers', ..., 'auto_video_caption_info', 'auto_captions', ...), expected_type=dict)
        for caption in captions_info:
            caption_url = traverse_obj(caption, ('url', 'url_list', ...), expected_type=url_or_none, get_all=False)
            if not caption_url:
                continue
            caption_json = self._download_json(
                caption_url, aweme_id, note='Downloading captions', errnote='Unable to download captions', fatal=False)
            if not caption_json:
                continue
            subtitles.setdefault(caption.get('language', 'en'), []).append({
                'ext': 'srt',
                'data': '\n\n'.join(
                    f'{i + 1}\n{srt_subtitles_timecode(line["start_time"] / 1000)} --> {srt_subtitles_timecode(line["end_time"] / 1000)}\n{line["text"]}'
                    for i, line in enumerate(caption_json['utterances']) if line.get('text')),
            })
        # feed endpoint subs
        if not subtitles:
            for caption in traverse_obj(aweme_detail, ('video', 'cla_info', 'caption_infos', ...), expected_type=dict):
                if not caption.get('url'):
                    continue
                subtitles.setdefault(caption.get('lang') or 'en', []).append({
                    'url': caption['url'],
                    'ext': EXT_MAP.get(caption.get('Format')),
                })
        # webpage subs
        if not subtitles:
            if user_name:  # only _parse_aweme_video_app needs to extract the webpage here
                aweme_detail, _ = self._extract_web_data_and_status(
                    self._create_url(user_name, aweme_id), aweme_id, fatal=False)
            for caption in traverse_obj(aweme_detail, ('video', 'subtitleInfos', lambda _, v: v['Url'])):
                subtitles.setdefault(caption.get('LanguageCodeName') or 'en', []).append({
                    'url': caption['Url'],
                    'ext': EXT_MAP.get(caption.get('Format')),
                })

        # Deprioritize creator_caption json since it can't be embedded or used by media players
        for lang, subs_list in subtitles.items():
            subtitles[lang] = sorted(subs_list, key=lambda x: preference(x['ext']))

        return subtitles

    def _parse_url_key(self, url_key):
        format_id, codec, res, bitrate = self._search_regex(
            r'v[^_]+_(?P<id>(?P<codec>[^_]+)_(?P<res>\d+p)_(?P<bitrate>\d+))', url_key,
            'url key', default=(None, None, None, None), group=('id', 'codec', 'res', 'bitrate'))
        if not format_id:
            return {}, None
        return {
            'format_id': format_id,
            'vcodec': 'h265' if codec == 'bytevc1' else codec,
            'tbr': int_or_none(bitrate, scale=1000) or None,
            'quality': qualities(self.QUALITIES)(res),
        }, res

    def _parse_aweme_video_app(self, aweme_detail):
        aweme_id = aweme_detail['aweme_id']
        video_info = aweme_detail['video']
        known_resolutions = {}

        def audio_meta(url):
            ext = determine_ext(url, default_ext='m4a')
            return {
                'format_note': 'Music track',
                'ext': ext,
                'acodec': 'aac' if ext == 'm4a' else ext,
                'vcodec': 'none',
                'width': None,
                'height': None,
            } if ext == 'mp3' or '-music-' in url else {}

        def extract_addr(addr, add_meta={}):
            parsed_meta, res = self._parse_url_key(addr.get('url_key', ''))
            is_bytevc2 = parsed_meta.get('vcodec') == 'bytevc2'
            if res:
                known_resolutions.setdefault(res, {}).setdefault('height', int_or_none(addr.get('height')))
                known_resolutions[res].setdefault('width', int_or_none(addr.get('width')))
                parsed_meta.update(known_resolutions.get(res, {}))
                add_meta.setdefault('height', int_or_none(res[:-1]))
            return [{
                'url': url,
                'filesize': int_or_none(addr.get('data_size')),
                'ext': 'mp4',
                'acodec': 'aac',
                'source_preference': -2 if 'aweme/v1' in url else -1,  # Downloads from API might get blocked
                **add_meta, **parsed_meta,
                # bytevc2 is bytedance's own custom h266/vvc codec, as-of-yet unplayable
                'preference': -100 if is_bytevc2 else -1,
                'format_note': join_nonempty(
                    add_meta.get('format_note'), '(API)' if 'aweme/v1' in url else None,
                    '(UNPLAYABLE)' if is_bytevc2 else None, delim=' '),
                **audio_meta(url),
            } for url in addr.get('url_list') or []]

        # Hack: Add direct video links first to prioritize them when removing duplicate formats
        formats = []
        width = int_or_none(video_info.get('width'))
        height = int_or_none(video_info.get('height'))
        ratio = try_call(lambda: width / height) or 0.5625
        if video_info.get('play_addr'):
            formats.extend(extract_addr(video_info['play_addr'], {
                'format_id': 'play_addr',
                'format_note': 'Direct video',
                'vcodec': 'h265' if traverse_obj(
                    video_info, 'is_bytevc1', 'is_h265') else 'h264',  # TODO: Check for "direct iOS" videos, like https://www.tiktok.com/@cookierun_dev/video/7039716639834656002
                'width': width,
                'height': height,
            }))
        if video_info.get('download_addr'):
            download_addr = video_info['download_addr']
            dl_width = int_or_none(download_addr.get('width'))
            formats.extend(extract_addr(download_addr, {
                'format_id': 'download_addr',
                'format_note': 'Download video%s' % (', watermarked' if video_info.get('has_watermark') else ''),
                'vcodec': 'h264',
                'width': dl_width,
                'height': try_call(lambda: int(dl_width / ratio)),  # download_addr['height'] is wrong
                'preference': -2 if video_info.get('has_watermark') else -1,
            }))
        if video_info.get('play_addr_h264'):
            formats.extend(extract_addr(video_info['play_addr_h264'], {
                'format_id': 'play_addr_h264',
                'format_note': 'Direct video',
                'vcodec': 'h264',
            }))
        if video_info.get('play_addr_bytevc1'):
            formats.extend(extract_addr(video_info['play_addr_bytevc1'], {
                'format_id': 'play_addr_bytevc1',
                'format_note': 'Direct video',
                'vcodec': 'h265',
            }))

        for bitrate in video_info.get('bit_rate', []):
            if bitrate.get('play_addr'):
                formats.extend(extract_addr(bitrate['play_addr'], {
                    'format_id': bitrate.get('gear_name'),
                    'format_note': 'Playback video',
                    'tbr': try_get(bitrate, lambda x: x['bit_rate'] / 1000),
                    'vcodec': 'h265' if traverse_obj(
                        bitrate, 'is_bytevc1', 'is_h265') else 'h264',
                    'fps': bitrate.get('FPS'),
                }))

        self._remove_duplicate_formats(formats)
        auth_cookie = self._get_cookies(self._WEBPAGE_HOST).get('sid_tt')
        if auth_cookie:
            for f in formats:
                self._set_cookie(urllib.parse.urlparse(f['url']).hostname, 'sid_tt', auth_cookie.value)

        stats_info = aweme_detail.get('statistics') or {}
        music_info = aweme_detail.get('music') or {}
        labels = traverse_obj(aweme_detail, ('hybrid_label', ..., 'text'), expected_type=str)

        contained_music_track = traverse_obj(
            music_info, ('matched_song', 'title'), ('matched_pgc_sound', 'title'), expected_type=str)
        contained_music_author = traverse_obj(
            music_info, ('matched_song', 'author'), ('matched_pgc_sound', 'author'), 'author', expected_type=str)

        is_generic_og_trackname = music_info.get('is_original_sound') and music_info.get('title') == 'original sound - {}'.format(music_info.get('owner_handle'))
        if is_generic_og_trackname:
            music_track, music_author = contained_music_track or 'original sound', contained_music_author
        else:
            music_track, music_author = music_info.get('title'), traverse_obj(music_info, ('author', {str}))

        author_info = traverse_obj(aweme_detail, ('author', {
            'uploader': ('unique_id', {str}),
            'uploader_id': ('uid', {str_or_none}),
            'channel': ('nickname', {str}),
            'channel_id': ('sec_uid', {str}),
        }))

        return {
            'id': aweme_id,
            **traverse_obj(aweme_detail, {
                'title': ('desc', {str}),
                'description': ('desc', {str}),
                'timestamp': ('create_time', {int_or_none}),
            }),
            **traverse_obj(stats_info, {
                'view_count': 'play_count',
                'like_count': 'digg_count',
                'repost_count': 'share_count',
                'comment_count': 'comment_count',
            }, expected_type=int_or_none),
            **author_info,
            'channel_url': format_field(author_info, 'channel_id', self._UPLOADER_URL_FORMAT, default=None),
            'uploader_url': format_field(
                author_info, ['uploader', 'uploader_id'], self._UPLOADER_URL_FORMAT, default=None),
            'track': music_track,
            'album': str_or_none(music_info.get('album')) or None,
            'artists': re.split(r'(?:, | & )', music_author) if music_author else None,
            'formats': formats,
            'subtitles': self.extract_subtitles(
                aweme_detail, aweme_id, traverse_obj(author_info, 'uploader', 'uploader_id', 'channel_id')),
            'thumbnails': [
                {
                    'id': cover_id,
                    'url': cover_url,
                    'preference': -1 if cover_id in ('cover', 'origin_cover') else -2,
                }
                for cover_id in (
                    'cover', 'ai_dynamic_cover', 'animated_cover',
                    'ai_dynamic_cover_bak', 'origin_cover', 'dynamic_cover')
                for cover_url in traverse_obj(video_info, (cover_id, 'url_list', ...))
            ],
            'duration': (traverse_obj(video_info, (
                (None, 'download_addr'), 'duration', {int_or_none(scale=1000)}, any))
                or traverse_obj(music_info, ('duration', {int_or_none}))),
            'availability': self._availability(
                is_private='Private' in labels,
                needs_subscription='Friends only' in labels,
                is_unlisted='Followers only' in labels),
            '_format_sort_fields': ('quality', 'codec', 'size', 'br'),
        }

    def _extract_web_formats(self, aweme_detail):
        COMMON_FORMAT_INFO = {
            'ext': 'mp4',
            'vcodec': 'h264',
            'acodec': 'aac',
        }
        video_info = traverse_obj(aweme_detail, ('video', {dict})) or {}
        play_width = int_or_none(video_info.get('width'))
        play_height = int_or_none(video_info.get('height'))
        ratio = try_call(lambda: play_width / play_height) or 0.5625
        formats = []

        for bitrate_info in traverse_obj(video_info, ('bitrateInfo', lambda _, v: v['PlayAddr']['UrlList'])):
            format_info, res = self._parse_url_key(
                traverse_obj(bitrate_info, ('PlayAddr', 'UrlKey', {str})) or '')
            # bytevc2 is bytedance's own custom h266/vvc codec, as-of-yet unplayable
            is_bytevc2 = format_info.get('vcodec') == 'bytevc2'
            format_info.update({
                'format_note': 'UNPLAYABLE' if is_bytevc2 else None,
                'preference': -100 if is_bytevc2 else -1,
                'filesize': traverse_obj(bitrate_info, ('PlayAddr', 'DataSize', {int_or_none})),
            })

            if dimension := (res and int(res[:-1])):
                if dimension == 540:  # '540p' is actually 576p
                    dimension = 576
                if ratio < 1:  # portrait: res/dimension is width
                    y = int(dimension / ratio)
                    format_info.update({
                        'width': dimension,
                        'height': y - (y % 2),
                    })
                else:  # landscape: res/dimension is height
                    x = int(dimension * ratio)
                    format_info.update({
                        'width': x + (x % 2),
                        'height': dimension,
                    })

            for video_url in traverse_obj(bitrate_info, ('PlayAddr', 'UrlList', ..., {url_or_none})):
                formats.append({
                    **COMMON_FORMAT_INFO,
                    **format_info,
                    'url': self._proto_relative_url(video_url),
                })

        # We don't have res string for play formats, but need quality for sorting & de-duplication
        play_quality = traverse_obj(formats, (lambda _, v: v['width'] == play_width, 'quality', any))

        for play_url in traverse_obj(video_info, ('playAddr', ((..., 'src'), None), {url_or_none})):
            formats.append({
                **COMMON_FORMAT_INFO,
                'format_id': 'play',
                'url': self._proto_relative_url(play_url),
                'width': play_width,
                'height': play_height,
                'quality': play_quality,
            })

        for download_url in traverse_obj(video_info, (('downloadAddr', ('download', 'url')), {url_or_none})):
            formats.append({
                **COMMON_FORMAT_INFO,
                'format_id': 'download',
                'url': self._proto_relative_url(download_url),
                'format_note': 'watermarked',
                'preference': -2,
            })

        self._remove_duplicate_formats(formats)

        # Is it a slideshow with only audio for download?
        if not formats and traverse_obj(aweme_detail, ('music', 'playUrl', {url_or_none})):
            audio_url = aweme_detail['music']['playUrl']
            ext = traverse_obj(parse_qs(audio_url), (
                'mime_type', -1, {lambda x: x.replace('_', '/')}, {mimetype2ext})) or 'm4a'
            formats.append({
                'format_id': 'audio',
                'url': self._proto_relative_url(audio_url),
                'ext': ext,
                'acodec': 'aac' if ext == 'm4a' else ext,
                'vcodec': 'none',
            })

        # Filter out broken formats, see https://github.com/yt-dlp/yt-dlp/issues/11034
        return [f for f in formats if urllib.parse.urlparse(f['url']).hostname != 'www.tiktok.com']

    def _parse_aweme_video_web(self, aweme_detail, webpage_url, video_id, extract_flat=False):
        author_info = traverse_obj(aweme_detail, (('authorInfo', 'author', None), {
            'channel': ('nickname', {str}),
            'channel_id': (('authorSecId', 'secUid'), {str}),
            'uploader': (('uniqueId', 'author'), {str}),
            'uploader_id': (('authorId', 'uid', 'id'), {str_or_none}),
        }), get_all=False)

        return {
            'id': video_id,
            'formats': None if extract_flat else self._extract_web_formats(aweme_detail),
            'subtitles': None if extract_flat else self.extract_subtitles(aweme_detail, video_id, None),
            'http_headers': {'Referer': webpage_url},
            **author_info,
            'channel_url': format_field(author_info, 'channel_id', self._UPLOADER_URL_FORMAT, default=None),
            'uploader_url': format_field(
                author_info, ['uploader', 'uploader_id'], self._UPLOADER_URL_FORMAT, default=None),
            **traverse_obj(aweme_detail, ('music', {
                'track': ('title', {str}),
                'album': ('album', {str}, filter),
                'artists': ('authorName', {str}, {lambda x: re.split(r'(?:, | & )', x) if x else None}),
                'duration': ('duration', {int_or_none}),
            })),
            **traverse_obj(aweme_detail, {
                'title': ('desc', {str}),
                'description': ('desc', {str}),
                # audio-only slideshows have a video duration of 0 and an actual audio duration
                'duration': ('video', 'duration', {int_or_none}, filter),
                'timestamp': ('createTime', {int_or_none}),
            }),
            **traverse_obj(aweme_detail, ('stats', {
                'view_count': 'playCount',
                'like_count': 'diggCount',
                'repost_count': 'shareCount',
                'comment_count': 'commentCount',
            }), expected_type=int_or_none),
            'thumbnails': [
                {
                    'id': cover_id,
                    'url': self._proto_relative_url(cover_url),
                    'preference': -2 if cover_id == 'dynamicCover' else -1,
                }
                for cover_id in ('thumbnail', 'cover', 'dynamicCover', 'originCover')
                for cover_url in traverse_obj(aweme_detail, ((None, 'video'), cover_id, {url_or_none}))
            ],
        }


class TikTokIE(TikTokBaseIE):
    _VALID_URL = r'https?://www\.tiktok\.com/(?:embed|@(?P<user_id>[\w\.-]+)?/video)/(?P<id>\d+)'
    _EMBED_REGEX = [rf'<(?:script|iframe)[^>]+\bsrc=(["\'])(?P<url>{_VALID_URL})']

    _TESTS = [{
        'url': 'https://www.tiktok.com/@leenabhushan/video/6748451240264420610',
        'md5': '736bb7a466c6f0a6afeb597da1e6f5b7',
        'info_dict': {
            'id': '6748451240264420610',
            'ext': 'mp4',
            'title': '#jassmanak #lehanga #leenabhushan',
            'description': '#jassmanak #lehanga #leenabhushan',
            'duration': 13,
            'height': 1024,
            'width': 576,
            'uploader': 'leenabhushan',
            'uploader_id': '6691488002098119685',
            'uploader_url': 'https://www.tiktok.com/@MS4wLjABAAAA_Eb4t1vodM1IuTy_cvp9CY22RAb59xqrO0Xtz9CYQJvgXaDvZxYnZYRzDWhhgJmy',
            'creator': 'facestoriesbyleenabh',
            'thumbnail': r're:^https?://[\w\/\.\-]+(~[\w\-]+\.image)?',
            'upload_date': '20191016',
            'timestamp': 1571246252,
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'artist': 'Ysrbeats',
            'album': 'Lehanga',
            'track': 'Lehanga',
        },
        'skip': '404 Not Found',
    }, {
        'url': 'https://www.tiktok.com/@patroxofficial/video/6742501081818877190?langCountry=en',
        'md5': 'f21112672ee4ce05ca390fb6522e1b6f',
        'info_dict': {
            'id': '6742501081818877190',
            'ext': 'mp4',
            'title': 'md5:5e2a23877420bb85ce6521dbee39ba94',
            'description': 'md5:5e2a23877420bb85ce6521dbee39ba94',
            'duration': 27,
            'height': 1024,
            'width': 576,
            'uploader': 'patrox',
            'uploader_id': '18702747',
            'uploader_url': 'https://www.tiktok.com/@patrox',
            'channel_url': 'https://www.tiktok.com/@MS4wLjABAAAAiFnldaILebi5heDoVU6bn4jBWWycX6-9U3xuNPqZ8Ws',
            'channel_id': 'MS4wLjABAAAAiFnldaILebi5heDoVU6bn4jBWWycX6-9U3xuNPqZ8Ws',
            'channel': 'patroX',
            'thumbnail': r're:^https?://[\w\/\.\-]+(~[\w\-]+\.image)?',
            'upload_date': '20190930',
            'timestamp': 1569860870,
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'artists': ['Evan Todd', 'Jessica Keenan Wynn', 'Alice Lee', 'Barrett Wilbert Weed', 'Jon Eidson'],
            'track': 'Big Fun',
        },
    }, {
        # Banned audio, was available on the app, now works with web too
        'url': 'https://www.tiktok.com/@barudakhb_/video/6984138651336838402',
        'info_dict': {
            'id': '6984138651336838402',
            'ext': 'mp4',
            'title': 'Balas @yolaaftwsr hayu yu ? #SquadRandom_ 🔥',
            'description': 'Balas @yolaaftwsr hayu yu ? #SquadRandom_ 🔥',
            'uploader': 'barudakhb_',
            'channel': 'md5:29f238c49bc0c176cb3cef1a9cea9fa6',
            'uploader_id': '6974687867511718913',
            'uploader_url': 'https://www.tiktok.com/@barudakhb_',
            'channel_url': 'https://www.tiktok.com/@MS4wLjABAAAAbhBwQC-R1iKoix6jDFsF-vBdfx2ABoDjaZrM9fX6arU3w71q3cOWgWuTXn1soZ7d',
            'channel_id': 'MS4wLjABAAAAbhBwQC-R1iKoix6jDFsF-vBdfx2ABoDjaZrM9fX6arU3w71q3cOWgWuTXn1soZ7d',
            'track': 'Boka Dance',
            'artists': ['md5:29f238c49bc0c176cb3cef1a9cea9fa6'],
            'timestamp': 1626121503,
            'duration': 18,
            'thumbnail': r're:^https?://[\w\/\.\-]+(~[\w\-]+\.image)?',
            'upload_date': '20210712',
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
        },
    }, {
        # Sponsored video, only available with feed workaround
        'url': 'https://www.tiktok.com/@MS4wLjABAAAATh8Vewkn0LYM7Fo03iec3qKdeCUOcBIouRk1mkiag6h3o_pQu_dUXvZ2EZlGST7_/video/7042692929109986561',
        'info_dict': {
            'id': '7042692929109986561',
            'ext': 'mp4',
            'title': 'Slap and Run!',
            'description': 'Slap and Run!',
            'uploader': 'user440922249',
            'channel': 'Slap And Run',
            'uploader_id': '7036055384943690754',
            'uploader_url': 'https://www.tiktok.com/@MS4wLjABAAAATh8Vewkn0LYM7Fo03iec3qKdeCUOcBIouRk1mkiag6h3o_pQu_dUXvZ2EZlGST7_',
            'channel_id': 'MS4wLjABAAAATh8Vewkn0LYM7Fo03iec3qKdeCUOcBIouRk1mkiag6h3o_pQu_dUXvZ2EZlGST7_',
            'track': 'Promoted Music',
            'timestamp': 1639754738,
            'duration': 30,
            'thumbnail': r're:^https?://[\w\/\.\-]+(~[\w\-]+\.image)?',
            'upload_date': '20211217',
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
        },
        'skip': 'This video is unavailable',
    }, {
        # Video without title and description
        'url': 'https://www.tiktok.com/@pokemonlife22/video/7059698374567611694',
        'info_dict': {
            'id': '7059698374567611694',
            'ext': 'mp4',
            'title': 'TikTok video #7059698374567611694',
            'description': '',
            'uploader': 'pokemonlife22',
            'channel': 'Pokemon',
            'uploader_id': '6820838815978423302',
            'uploader_url': 'https://www.tiktok.com/@pokemonlife22',
            'channel_url': 'https://www.tiktok.com/@MS4wLjABAAAA0tF1nBwQVVMyrGu3CqttkNgM68Do1OXUFuCY0CRQk8fEtSVDj89HqoqvbSTmUP2W',
            'channel_id': 'MS4wLjABAAAA0tF1nBwQVVMyrGu3CqttkNgM68Do1OXUFuCY0CRQk8fEtSVDj89HqoqvbSTmUP2W',
            'track': 'original sound',
            'timestamp': 1643714123,
            'duration': 6,
            'thumbnail': r're:^https?://[\w\/\.\-]+(~[\w\-]+\.image)?',
            'upload_date': '20220201',
            'artists': ['Pokemon'],
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
        },
    }, {
        # hydration JSON is sent in a <script> element
        'url': 'https://www.tiktok.com/@denidil6/video/7065799023130643713',
        'info_dict': {
            'id': '7065799023130643713',
            'ext': 'mp4',
            'title': '#denidil#денидил',
            'description': '#denidil#денидил',
            'uploader': 'denidil6',
            'uploader_id': '7046664115636405250',
            'uploader_url': 'https://www.tiktok.com/@MS4wLjABAAAAsvMSzFdQ4ikl3uR2TEJwMBbB2yZh2Zxwhx-WCo3rbDpAharE3GQCrFuJArI3C8QJ',
            'artist': 'Holocron Music',
            'album': 'Wolf Sounds (1 Hour) Enjoy the Company of the Animal That Is the Majestic King of the Night',
            'track': 'Wolf Sounds (1 Hour) Enjoy the Company of the Animal That Is the Majestic King of the Night',
            'timestamp': 1645134536,
            'duration': 26,
            'upload_date': '20220217',
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
        },
        'skip': 'This video is unavailable',
    }, {
        # slideshow audio-only mp3 format
        'url': 'https://www.tiktok.com/@_le_cannibale_/video/7139980461132074283',
        'info_dict': {
            'id': '7139980461132074283',
            'ext': 'mp3',
            'title': 'TikTok video #7139980461132074283',
            'description': '',
            'channel': 'Antaura',
            'uploader': '_le_cannibale_',
            'uploader_id': '6604511138619654149',
            'uploader_url': 'https://www.tiktok.com/@_le_cannibale_',
            'channel_url': 'https://www.tiktok.com/@MS4wLjABAAAAoShJqaw_5gvy48y3azFeFcT4jeyKWbB0VVYasOCt2tTLwjNFIaDcHAM4D-QGXFOP',
            'channel_id': 'MS4wLjABAAAAoShJqaw_5gvy48y3azFeFcT4jeyKWbB0VVYasOCt2tTLwjNFIaDcHAM4D-QGXFOP',
            'artists': ['nathan !'],
            'track': 'grahamscott canon',
            'duration': 10,
            'upload_date': '20220905',
            'timestamp': 1662406249,
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'thumbnail': r're:^https://.+\.(?:webp|jpe?g)',
        },
    }, {
        # only available via web
        'url': 'https://www.tiktok.com/@moxypatch/video/7206382937372134662',
        'md5': '4cdefa501ac8ac20bf04986e10916fea',
        'info_dict': {
            'id': '7206382937372134662',
            'ext': 'mp4',
            'title': 'md5:1d95c0b96560ca0e8a231af4172b2c0a',
            'description': 'md5:1d95c0b96560ca0e8a231af4172b2c0a',
            'channel': 'MoxyPatch',
            'uploader': 'moxypatch',
            'uploader_id': '7039142049363379205',
            'uploader_url': 'https://www.tiktok.com/@moxypatch',
            'channel_url': 'https://www.tiktok.com/@MS4wLjABAAAAFhqKnngMHJSsifL0w1vFOP5kn3Ndo1ODp0XuIBkNMBCkALTvwILdpu12g3pTtL4V',
            'channel_id': 'MS4wLjABAAAAFhqKnngMHJSsifL0w1vFOP5kn3Ndo1ODp0XuIBkNMBCkALTvwILdpu12g3pTtL4V',
            'artists': ['your worst nightmare'],
            'track': 'original sound',
            'upload_date': '20230303',
            'timestamp': 1677866781,
            'duration': 10,
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'thumbnail': r're:^https://.+',
            'thumbnails': 'count:3',
        },
        'expected_warnings': ['Unable to find video in feed'],
    }, {
        # 1080p format
        'url': 'https://www.tiktok.com/@tatemcrae/video/7107337212743830830',  # FIXME: Web can only get audio
        'md5': '982512017a8a917124d5a08c8ae79621',
        'info_dict': {
            'id': '7107337212743830830',
            'ext': 'mp4',
            'title': 'new music video 4 don’t come backkkk🧸🖤 i hope u enjoy !! @musicontiktok',
            'description': 'new music video 4 don’t come backkkk🧸🖤 i hope u enjoy !! @musicontiktok',
            'uploader': 'tatemcrae',
            'uploader_id': '86328792343818240',
            'uploader_url': 'https://www.tiktok.com/@MS4wLjABAAAA-0bQT0CqebTRr6I4IkYvMDMKSRSJHLNPBo5HrSklJwyA2psXLSZG5FP-LMNpHnJd',
            'channel_id': 'MS4wLjABAAAA-0bQT0CqebTRr6I4IkYvMDMKSRSJHLNPBo5HrSklJwyA2psXLSZG5FP-LMNpHnJd',
            'channel': 'tate mcrae',
            'artists': ['tate mcrae'],
            'track': 'original sound',
            'upload_date': '20220609',
            'timestamp': 1654805899,
            'duration': 150,
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'thumbnail': r're:^https://.+\.webp',
        },
        'skip': 'Unavailable via feed API, only audio available via web',
    }, {
        # Slideshow, audio-only m4a format
        'url': 'https://www.tiktok.com/@hara_yoimiya/video/7253412088251534594',
        'md5': '2ff8fe0174db2dbf49c597a7bef4e47d',
        'info_dict': {
            'id': '7253412088251534594',
            'ext': 'm4a',
            'title': 'я ред флаг простите #переписка #щитпост #тревожныйтиппривязанности #рекомендации ',
            'description': 'я ред флаг простите #переписка #щитпост #тревожныйтиппривязанности #рекомендации ',
            'uploader': 'hara_yoimiya',
            'uploader_id': '6582536342634676230',
            'uploader_url': 'https://www.tiktok.com/@hara_yoimiya',
            'channel_url': 'https://www.tiktok.com/@MS4wLjABAAAAIAlDxriiPWLE-p8p1R_0Bx8qWKfi-7zwmGhzU8Mv25W8sNxjfIKrol31qTczzuLB',
            'channel_id': 'MS4wLjABAAAAIAlDxriiPWLE-p8p1R_0Bx8qWKfi-7zwmGhzU8Mv25W8sNxjfIKrol31qTczzuLB',
            'channel': 'лампочка(!)',
            'artists': ['Øneheart'],
            'album': 'watching the stars',
            'track': 'watching the stars',
            'duration': 60,
            'upload_date': '20230708',
            'timestamp': 1688816612,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'repost_count': int,
            'thumbnail': r're:^https://.+\.(?:webp|jpe?g)',
        },
    }, {
        # Auto-captions available
        'url': 'https://www.tiktok.com/@hankgreen1/video/7047596209028074758',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id, user_id = self._match_valid_url(url).group('id', 'user_id')

        if self._KNOWN_APP_INFO:
            try:
                return self._extract_aweme_app(video_id)
            except ExtractorError as e:
                e.expected = True
                self.report_warning(f'{e}; trying with webpage')

        url = self._create_url(user_id, video_id)
        video_data, status = self._extract_web_data_and_status(url, video_id)

        if video_data and status == 0:
            return self._parse_aweme_video_web(video_data, url, video_id)
        elif status == 10216:
            raise ExtractorError('This video is private', expected=True)
        raise ExtractorError(f'Video not available, status code {status}', video_id=video_id)


class TikTokUserIE(TikTokBaseIE):
    IE_NAME = 'tiktok:user'
    _VALID_URL = r'(?:tiktokuser:|https?://(?:www\.)?tiktok\.com/@)(?P<id>[\w.-]+)/?(?:$|[#?])'
    _TESTS = [{
        'url': 'https://tiktok.com/@corgibobaa?lang=en',
        'playlist_mincount': 45,
        'info_dict': {
            'id': 'MS4wLjABAAAAepiJKgwWhulvCpSuUVsp7sgVVsFJbbNaLeQ6OQ0oAJERGDUIXhb2yxxHZedsItgT',
            'title': 'corgibobaa',
        },
    }, {
        'url': 'https://www.tiktok.com/@6820838815978423302',
        'playlist_mincount': 5,
        'info_dict': {
            'id': 'MS4wLjABAAAA0tF1nBwQVVMyrGu3CqttkNgM68Do1OXUFuCY0CRQk8fEtSVDj89HqoqvbSTmUP2W',
            'title': '6820838815978423302',
        },
    }, {
        'url': 'https://www.tiktok.com/@meme',
        'playlist_mincount': 593,
        'info_dict': {
            'id': 'MS4wLjABAAAAiKfaDWeCsT3IHwY77zqWGtVRIy9v4ws1HbVi7auP1Vx7dJysU_hc5yRiGywojRD6',
            'title': 'meme',
        },
    }, {
        'url': 'tiktokuser:MS4wLjABAAAAM3R2BtjzVT-uAtstkl2iugMzC6AtnpkojJbjiOdDDrdsTiTR75-8lyWJCY5VvDrZ',
        'playlist_mincount': 31,
        'info_dict': {
            'id': 'MS4wLjABAAAAM3R2BtjzVT-uAtstkl2iugMzC6AtnpkojJbjiOdDDrdsTiTR75-8lyWJCY5VvDrZ',
        },
    }]
    _USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0'
    _API_BASE_URL = 'https://www.tiktok.com/api/creator/item_list/'

    def _build_web_query(self, sec_uid, cursor):
        return {
            'aid': '1988',
            'app_language': 'en',
            'app_name': 'tiktok_web',
            'browser_language': 'en-US',
            'browser_name': 'Mozilla',
            'browser_online': 'true',
            'browser_platform': 'Win32',
            'browser_version': '5.0 (Windows)',
            'channel': 'tiktok_web',
            'cookie_enabled': 'true',
            'count': '15',
            'cursor': cursor,
            'device_id': self._DEVICE_ID,
            'device_platform': 'web_pc',
            'focus_state': 'true',
            'from_page': 'user',
            'history_len': '2',
            'is_fullscreen': 'false',
            'is_page_visible': 'true',
            'language': 'en',
            'os': 'windows',
            'priority_region': '',
            'referer': '',
            'region': 'US',
            'screen_height': '1080',
            'screen_width': '1920',
            'secUid': sec_uid,
            'type': '1',  # pagination type: 0 == oldest-to-newest, 1 == newest-to-oldest
            'tz_name': 'UTC',
            'verifyFp': f'verify_{"".join(random.choices(string.hexdigits, k=7))}',
            'webcast_language': 'en',
        }

    def _entries(self, sec_uid, user_name):
        display_id = user_name or sec_uid
        seen_ids = set()

        cursor = int(time.time() * 1E3)
        for page in itertools.count(1):
            response = self._download_json(
                self._API_BASE_URL, display_id, f'Downloading page {page}',
                query=self._build_web_query(sec_uid, cursor), headers={'User-Agent': self._USER_AGENT})

            for video in traverse_obj(response, ('itemList', lambda _, v: v['id'])):
                video_id = video['id']
                if video_id in seen_ids:
                    continue
                seen_ids.add(video_id)
                webpage_url = self._create_url(display_id, video_id)
                yield self.url_result(
                    webpage_url, TikTokIE,
                    **self._parse_aweme_video_web(video, webpage_url, video_id, extract_flat=True))

            old_cursor = cursor
            cursor = traverse_obj(
                response, ('itemList', -1, 'createTime', {lambda x: int(x * 1E3)}))
            if not cursor or old_cursor == cursor:
                # User may not have posted within this ~1 week lookback, so manually adjust cursor
                cursor = old_cursor - 7 * 86_400_000
            # In case 'hasMorePrevious' is wrong, break if we have gone back before TikTok existed
            if cursor < 1472706000000 or not traverse_obj(response, 'hasMorePrevious'):
                break

    def _get_sec_uid(self, user_url, user_name, msg):
        webpage = self._download_webpage(
            user_url, user_name, fatal=False, headers={'User-Agent': 'Mozilla/5.0'},
            note=f'Downloading {msg} webpage', errnote=f'Unable to download {msg} webpage') or ''
        return (traverse_obj(self._get_universal_data(webpage, user_name),
                             ('webapp.user-detail', 'userInfo', 'user', 'secUid', {str}))
                or traverse_obj(self._get_sigi_state(webpage, user_name),
                                ('LiveRoom', 'liveRoomUserInfo', 'user', 'secUid', {str}),
                                ('UserModule', 'users', ..., 'secUid', {str}, any)))

    def _real_extract(self, url):
        user_name, sec_uid = self._match_id(url), None
        if mobj := re.fullmatch(r'MS4wLjABAAAA[\w-]{64}', user_name):
            user_name, sec_uid = None, mobj.group(0)
        else:
            sec_uid = (self._get_sec_uid(self._UPLOADER_URL_FORMAT % user_name, user_name, 'user')
                       or self._get_sec_uid(self._UPLOADER_URL_FORMAT % f'{user_name}/live', user_name, 'live'))

        if not sec_uid:
            webpage = self._download_webpage(
                f'https://www.tiktok.com/embed/@{user_name}', user_name,
                note='Downloading user embed page', fatal=False) or ''
            data = traverse_obj(self._search_json(
                r'<script[^>]+\bid=[\'"]__FRONTITY_CONNECT_STATE__[\'"][^>]*>',
                webpage, 'data', user_name, default={}),
                ('source', 'data', f'/embed/@{user_name}', {dict}))

            for aweme_id in traverse_obj(data, ('videoList', ..., 'id', {str})):
                webpage_url = self._create_url(user_name, aweme_id)
                video_data, _ = self._extract_web_data_and_status(webpage_url, aweme_id, fatal=False)
                sec_uid = self._parse_aweme_video_web(
                    video_data, webpage_url, aweme_id, extract_flat=True).get('channel_id')
                if sec_uid:
                    break

        if not sec_uid:
            raise ExtractorError(
                'Unable to extract secondary user ID. If you are able to get the channel_id '
                'from a video posted by this user, try using "tiktokuser:channel_id" as the '
                'input URL (replacing `channel_id` with its actual value)', expected=True)

        return self.playlist_result(self._entries(sec_uid, user_name), sec_uid, user_name)


class TikTokBaseListIE(TikTokBaseIE):  # XXX: Conventionally, base classes should end with BaseIE/InfoExtractor
    def _entries(self, list_id, display_id):
        query = {
            self._QUERY_NAME: list_id,
            'cursor': 0,
            'count': 20,
            'type': 5,
            'device_id': self._DEVICE_ID,
        }

        for page in itertools.count(1):
            for retry in self.RetryManager():
                try:
                    post_list = self._call_api(
                        self._API_ENDPOINT, display_id, query=query,
                        note=f'Downloading video list page {page}',
                        errnote='Unable to download video list')
                except ExtractorError as e:
                    if isinstance(e.cause, json.JSONDecodeError) and e.cause.pos == 0:
                        retry.error = e
                        continue
                    raise
            for video in post_list.get('aweme_list', []):
                yield {
                    **self._parse_aweme_video_app(video),
                    'extractor_key': TikTokIE.ie_key(),
                    'extractor': 'TikTok',
                    'webpage_url': f'https://tiktok.com/@_/video/{video["aweme_id"]}',
                }
            if not post_list.get('has_more'):
                break
            query['cursor'] = post_list['cursor']

    def _real_extract(self, url):
        list_id = self._match_id(url)
        return self.playlist_result(self._entries(list_id, list_id), list_id)


class TikTokSoundIE(TikTokBaseListIE):
    IE_NAME = 'tiktok:sound'
    _VALID_URL = r'https?://(?:www\.)?tiktok\.com/music/[\w\.-]+-(?P<id>[\d]+)[/?#&]?'
    _WORKING = False
    _QUERY_NAME = 'music_id'
    _API_ENDPOINT = 'music/aweme'
    _TESTS = [{
        'url': 'https://www.tiktok.com/music/Build-a-Btch-6956990112127585029?lang=en',
        'playlist_mincount': 100,
        'info_dict': {
            'id': '6956990112127585029',
        },
        'expected_warnings': ['Retrying'],
    }, {
        # Actual entries are less than listed video count
        'url': 'https://www.tiktok.com/music/jiefei-soap-remix-7036843036118469381',
        'playlist_mincount': 2182,
        'info_dict': {
            'id': '7036843036118469381',
        },
        'expected_warnings': ['Retrying'],
    }]


class TikTokEffectIE(TikTokBaseListIE):
    IE_NAME = 'tiktok:effect'
    _VALID_URL = r'https?://(?:www\.)?tiktok\.com/sticker/[\w\.-]+-(?P<id>[\d]+)[/?#&]?'
    _WORKING = False
    _QUERY_NAME = 'sticker_id'
    _API_ENDPOINT = 'sticker/aweme'
    _TESTS = [{
        'url': 'https://www.tiktok.com/sticker/MATERIAL-GWOOORL-1258156',
        'playlist_mincount': 100,
        'info_dict': {
            'id': '1258156',
        },
        'expected_warnings': ['Retrying'],
    }, {
        # Different entries between mobile and web, depending on region
        'url': 'https://www.tiktok.com/sticker/Elf-Friend-479565',
        'only_matching': True,
    }]


class TikTokTagIE(TikTokBaseListIE):
    IE_NAME = 'tiktok:tag'
    _VALID_URL = r'https?://(?:www\.)?tiktok\.com/tag/(?P<id>[^/?#&]+)'
    _WORKING = False
    _QUERY_NAME = 'ch_id'
    _API_ENDPOINT = 'challenge/aweme'
    _TESTS = [{
        'url': 'https://tiktok.com/tag/hello2018',
        'playlist_mincount': 39,
        'info_dict': {
            'id': '46294678',
            'title': 'hello2018',
        },
        'expected_warnings': ['Retrying'],
    }, {
        'url': 'https://tiktok.com/tag/fypシ?is_copy_url=0&is_from_webapp=v1',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id, headers={
            'User-Agent': 'facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)',
        })
        tag_id = self._html_search_regex(r'snssdk\d*://challenge/detail/(\d+)', webpage, 'tag ID')
        return self.playlist_result(self._entries(tag_id, display_id), tag_id, display_id)


class TikTokCollectionIE(TikTokBaseIE):
    IE_NAME = 'tiktok:collection'
    _VALID_URL = r'https?://www\.tiktok\.com/@(?P<user_id>[\w.-]+)/collection/(?P<title>[^/?#]+)-(?P<id>\d+)/?(?:[?#]|$)'
    _TESTS = [{
        # playlist should have exactly 9 videos
        'url': 'https://www.tiktok.com/@imanoreotwe/collection/count-test-7371330159376370462',
        'info_dict': {
            'id': '7371330159376370462',
            'title': 'imanoreotwe-count-test',
        },
        'playlist_count': 9,
    }, {
        # tests returning multiple pages of a large collection
        'url': 'https://www.tiktok.com/@imanoreotwe/collection/%F0%9F%98%82-7111887189571160875',
        'info_dict': {
            'id': '7111887189571160875',
            'title': 'imanoreotwe-%F0%9F%98%82',
        },
        'playlist_mincount': 100,
    }]
    _API_BASE_URL = 'https://www.tiktok.com/api/collection/item_list/'
    _PAGE_COUNT = 30

    def _build_web_query(self, collection_id, cursor):
        return {
            'aid': '1988',
            'collectionId': collection_id,
            'count': self._PAGE_COUNT,
            'cursor': cursor,
            'sourceType': '113',
        }

    def _entries(self, collection_id):
        cursor = 0
        for page in itertools.count(1):
            response = self._download_json(
                self._API_BASE_URL, collection_id, f'Downloading page {page}',
                query=self._build_web_query(collection_id, cursor))

            for video in traverse_obj(response, ('itemList', lambda _, v: v['id'])):
                video_id = video['id']
                author = traverse_obj(video, ('author', ('uniqueId', 'secUid', 'id'), {str}, any)) or '_'
                webpage_url = self._create_url(author, video_id)
                yield self.url_result(
                    webpage_url, TikTokIE,
                    **self._parse_aweme_video_web(video, webpage_url, video_id, extract_flat=True))

            if not traverse_obj(response, 'hasMore'):
                break
            cursor += self._PAGE_COUNT

    def _real_extract(self, url):
        collection_id, title, user_name = self._match_valid_url(url).group('id', 'title', 'user_id')

        return self.playlist_result(
            self._entries(collection_id), collection_id, '-'.join((user_name, title)))


class DouyinIE(TikTokBaseIE):
    _VALID_URL = r'https?://(?:www\.)?douyin\.com/video/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.douyin.com/video/6961737553342991651',
        'md5': '9ecce7bc5b302601018ecb2871c63a75',
        'info_dict': {
            'id': '6961737553342991651',
            'ext': 'mp4',
            'title': '#杨超越  小小水手带你去远航❤️',
            'description': '#杨超越  小小水手带你去远航❤️',
            'uploader': '6897520xka',
            'uploader_id': '110403406559',
            'uploader_url': 'https://www.douyin.com/user/MS4wLjABAAAAEKnfa654JAJ_N5lgZDQluwsxmY0lhfmEYNQBBkwGG98',
            'channel_id': 'MS4wLjABAAAAEKnfa654JAJ_N5lgZDQluwsxmY0lhfmEYNQBBkwGG98',
            'channel': '杨超越',
            'duration': 19,
            'timestamp': 1620905839,
            'upload_date': '20210513',
            'track': '@杨超越创作的原声',
            'artists': ['杨超越'],
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'thumbnail': r're:https?://.+\.jpe?g',
        },
    }, {
        'url': 'https://www.douyin.com/video/6982497745948921092',
        'md5': '15c5e660b7048af3707304e3cc02bbb5',
        'info_dict': {
            'id': '6982497745948921092',
            'ext': 'mp4',
            'title': '这个夏日和小羊@杨超越 一起遇见白色幻想',
            'description': '这个夏日和小羊@杨超越 一起遇见白色幻想',
            'uploader': '0731chaoyue',
            'uploader_id': '408654318141572',
            'uploader_url': 'https://www.douyin.com/user/MS4wLjABAAAAZJpnglcjW2f_CMVcnqA_6oVBXKWMpH0F8LIHuUu8-lA',
            'channel_id': 'MS4wLjABAAAAZJpnglcjW2f_CMVcnqA_6oVBXKWMpH0F8LIHuUu8-lA',
            'channel': '杨超越工作室',
            'duration': 42,
            'timestamp': 1625739481,
            'upload_date': '20210708',
            'track': '@杨超越工作室创作的原声',
            'artists': ['杨超越工作室'],
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'thumbnail': r're:https?://.+\.jpe?g',
        },
    }, {
        'url': 'https://www.douyin.com/video/6953975910773099811',
        'md5': '0e6443758b8355db9a3c34864a4276be',
        'info_dict': {
            'id': '6953975910773099811',
            'ext': 'mp4',
            'title': '#一起看海  出现在你的夏日里',
            'description': '#一起看海  出现在你的夏日里',
            'uploader': '6897520xka',
            'uploader_id': '110403406559',
            'uploader_url': 'https://www.douyin.com/user/MS4wLjABAAAAEKnfa654JAJ_N5lgZDQluwsxmY0lhfmEYNQBBkwGG98',
            'channel_id': 'MS4wLjABAAAAEKnfa654JAJ_N5lgZDQluwsxmY0lhfmEYNQBBkwGG98',
            'channel': '杨超越',
            'duration': 17,
            'timestamp': 1619098692,
            'upload_date': '20210422',
            'track': '@杨超越创作的原声',
            'artists': ['杨超越'],
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'thumbnail': r're:https?://.+\.jpe?g',
        },
    }, {
        'url': 'https://www.douyin.com/video/6950251282489675042',
        'md5': 'b4db86aec367ef810ddd38b1737d2fed',
        'info_dict': {
            'id': '6950251282489675042',
            'ext': 'mp4',
            'title': '哈哈哈，成功了哈哈哈哈哈哈',
            'uploader': '杨超越',
            'upload_date': '20210412',
            'timestamp': 1618231483,
            'uploader_id': '110403406559',
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
        },
        'skip': 'No longer available',
    }, {
        'url': 'https://www.douyin.com/video/6963263655114722595',
        'md5': '1440bcf59d8700f8e014da073a4dfea8',
        'info_dict': {
            'id': '6963263655114722595',
            'ext': 'mp4',
            'title': '#哪个爱豆的105度最甜 换个角度看看我哈哈',
            'description': '#哪个爱豆的105度最甜 换个角度看看我哈哈',
            'uploader': '6897520xka',
            'uploader_id': '110403406559',
            'uploader_url': 'https://www.douyin.com/user/MS4wLjABAAAAEKnfa654JAJ_N5lgZDQluwsxmY0lhfmEYNQBBkwGG98',
            'channel_id': 'MS4wLjABAAAAEKnfa654JAJ_N5lgZDQluwsxmY0lhfmEYNQBBkwGG98',
            'channel': '杨超越',
            'duration': 15,
            'timestamp': 1621261163,
            'upload_date': '20210517',
            'track': '@杨超越创作的原声',
            'artists': ['杨超越'],
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'thumbnail': r're:https?://.+\.jpe?g',
        },
    }]
    _UPLOADER_URL_FORMAT = 'https://www.douyin.com/user/%s'
    _WEBPAGE_HOST = 'https://www.douyin.com/'

    def _real_extract(self, url):
        video_id = self._match_id(url)

        detail = traverse_obj(self._download_json(
            'https://www.douyin.com/aweme/v1/web/aweme/detail/', video_id,
            'Downloading web detail JSON', 'Failed to download web detail JSON',
            query={'aweme_id': video_id}, fatal=False), ('aweme_detail', {dict}))
        if not detail:
            # TODO: Run verification challenge code to generate signature cookies
            raise ExtractorError(
                'Fresh cookies (not necessarily logged in) are needed',
                expected=not self._get_cookies(self._WEBPAGE_HOST).get('s_v_web_id'))

        return self._parse_aweme_video_app(detail)


class TikTokVMIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:vm|vt)\.tiktok\.com|(?:www\.)tiktok\.com/t)/(?P<id>\w+)'
    IE_NAME = 'vm.tiktok'

    _TESTS = [{
        'url': 'https://www.tiktok.com/t/ZTRC5xgJp',
        'info_dict': {
            'id': '7170520270497680683',
            'ext': 'mp4',
            'title': 'md5:c64f6152330c2efe98093ccc8597871c',
            'uploader_id': '6687535061741700102',
            'upload_date': '20221127',
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'uploader_url': 'https://www.tiktok.com/@MS4wLjABAAAAObqu3WCTXxmw2xwZ3iLEHnEecEIw7ks6rxWqOqOhaPja9BI7gqUQnjw8_5FSoDXX',
            'album': 'Wave of Mutilation: Best of Pixies',
            'thumbnail': r're:https://.+\.webp.*',
            'duration': 5,
            'timestamp': 1669516858,
            'repost_count': int,
            'artist': 'Pixies',
            'track': 'Where Is My Mind?',
            'description': 'md5:c64f6152330c2efe98093ccc8597871c',
            'uploader': 'sigmachaddeus',
            'creator': 'SigmaChad',
        },
    }, {
        'url': 'https://vm.tiktok.com/ZTR45GpSF/',
        'info_dict': {
            'id': '7106798200794926362',
            'ext': 'mp4',
            'title': 'md5:edc3e7ea587847f8537468f2fe51d074',
            'uploader_id': '6997695878846268418',
            'upload_date': '20220608',
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'thumbnail': r're:https://.+\.webp.*',
            'uploader_url': 'https://www.tiktok.com/@MS4wLjABAAAAdZ_NcPPgMneaGrW0hN8O_J_bwLshwNNERRF5DxOw2HKIzk0kdlLrR8RkVl1ksrMO',
            'duration': 29,
            'timestamp': 1654680400,
            'repost_count': int,
            'artist': 'Akihitoko',
            'track': 'original sound',
            'description': 'md5:edc3e7ea587847f8537468f2fe51d074',
            'uploader': 'akihitoko1',
            'creator': 'Akihitoko',
        },
    }, {
        'url': 'https://vt.tiktok.com/ZSe4FqkKd',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        new_url = self._request_webpage(
            HEADRequest(url), self._match_id(url), headers={'User-Agent': 'facebookexternalhit/1.1'}).url
        if self.suitable(new_url):  # Prevent infinite loop in case redirect fails
            raise UnsupportedError(new_url)
        return self.url_result(new_url)


class TikTokLiveIE(TikTokBaseIE):
    _VALID_URL = r'''(?x)https?://(?:
        (?:www\.)?tiktok\.com/@(?P<uploader>[\w.-]+)/live|
        m\.tiktok\.com/share/live/(?P<id>\d+)
    )'''
    IE_NAME = 'tiktok:live'

    _TESTS = [{
        'url': 'https://www.tiktok.com/@weathernewslive/live',
        'info_dict': {
            'id': '7210809319192726273',
            'ext': 'mp4',
            'title': r're:ウェザーニュースLiVE[\d\s:-]*',
            'creator': 'ウェザーニュースLiVE',
            'uploader': 'weathernewslive',
            'uploader_id': '6621496731283095554',
            'uploader_url': 'https://www.tiktok.com/@weathernewslive',
            'live_status': 'is_live',
            'concurrent_view_count': int,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.tiktok.com/@pilarmagenta/live',
        'info_dict': {
            'id': '7209423610325322522',
            'ext': 'mp4',
            'title': str,
            'creator': 'Pilarmagenta',
            'uploader': 'pilarmagenta',
            'uploader_id': '6624846890674683909',
            'uploader_url': 'https://www.tiktok.com/@pilarmagenta',
            'live_status': 'is_live',
            'concurrent_view_count': int,
        },
        'skip': 'Livestream',
    }, {
        'url': 'https://m.tiktok.com/share/live/7209423610325322522/?language=en',
        'only_matching': True,
    }, {
        'url': 'https://www.tiktok.com/@iris04201/live',
        'only_matching': True,
    }]

    def _call_api(self, url, param, room_id, uploader, key=None):
        response = traverse_obj(self._download_json(
            url, room_id, fatal=False, query={
                'aid': '1988',
                param: room_id,
            }), (key, {dict}), default={})

        # status == 2 if live else 4
        if int_or_none(response.get('status')) == 2:
            return response
        # If room_id is obtained via mobile share URL and cannot be refreshed, do not wait for live
        elif not uploader:
            raise ExtractorError('This livestream has ended', expected=True)
        raise UserNotLive(video_id=uploader)

    def _real_extract(self, url):
        uploader, room_id = self._match_valid_url(url).group('uploader', 'id')
        webpage = self._download_webpage(
            url, uploader or room_id, headers={'User-Agent': 'Mozilla/5.0'}, fatal=not room_id)

        if webpage:
            data = self._get_sigi_state(webpage, uploader or room_id)
            room_id = (
                traverse_obj(data, ((
                    ('LiveRoom', 'liveRoomUserInfo', 'user'),
                    ('UserModule', 'users', ...)), 'roomId', {str}, any))
                or self._search_regex(r'snssdk\d*://live\?room_id=(\d+)', webpage, 'room ID', default=room_id))
            uploader = uploader or traverse_obj(
                data, ('LiveRoom', 'liveRoomUserInfo', 'user', 'uniqueId'),
                ('UserModule', 'users', ..., 'uniqueId'), get_all=False, expected_type=str)

        if not room_id:
            raise UserNotLive(video_id=uploader)

        formats = []
        live_info = self._call_api(
            'https://webcast.tiktok.com/webcast/room/info', 'room_id', room_id, uploader, key='data')

        get_quality = qualities(('SD1', 'ld', 'SD2', 'sd', 'HD1', 'hd', 'FULL_HD1', 'uhd', 'ORIGION', 'origin'))
        parse_inner = lambda x: self._parse_json(x, None)

        for quality, stream in traverse_obj(live_info, (
                'stream_url', 'live_core_sdk_data', 'pull_data', 'stream_data',
                {parse_inner}, 'data', {dict}), default={}).items():

            sdk_params = traverse_obj(stream, ('main', 'sdk_params', {parse_inner}, {
                'vcodec': ('VCodec', {str}),
                'tbr': ('vbitrate', {int_or_none(scale=1000)}),
                'resolution': ('resolution', {lambda x: re.match(r'(?i)\d+x\d+|\d+p', x).group().lower()}),
            }))

            flv_url = traverse_obj(stream, ('main', 'flv', {url_or_none}))
            if flv_url:
                formats.append({
                    'url': flv_url,
                    'ext': 'flv',
                    'format_id': f'flv-{quality}',
                    'quality': get_quality(quality),
                    **sdk_params,
                })

            hls_url = traverse_obj(stream, ('main', 'hls', {url_or_none}))
            if hls_url:
                formats.append({
                    'url': hls_url,
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'format_id': f'hls-{quality}',
                    'quality': get_quality(quality),
                    **sdk_params,
                })

        def get_vcodec(*keys):
            return traverse_obj(live_info, (
                'stream_url', *keys, {parse_inner}, 'VCodec', {str}))

        for stream in ('hls', 'rtmp'):
            stream_url = traverse_obj(live_info, ('stream_url', f'{stream}_pull_url', {url_or_none}))
            if stream_url:
                formats.append({
                    'url': stream_url,
                    'ext': 'mp4' if stream == 'hls' else 'flv',
                    'protocol': 'm3u8_native' if stream == 'hls' else 'https',
                    'format_id': f'{stream}-pull',
                    'vcodec': get_vcodec(f'{stream}_pull_url_params'),
                    'quality': get_quality('ORIGION'),
                })

        for f_id, f_url in traverse_obj(live_info, ('stream_url', 'flv_pull_url', {dict}), default={}).items():
            if not url_or_none(f_url):
                continue
            formats.append({
                'url': f_url,
                'ext': 'flv',
                'format_id': f'flv-{f_id}'.lower(),
                'vcodec': get_vcodec('flv_pull_url_params', f_id),
                'quality': get_quality(f_id),
            })

        # If uploader is a guest on another's livestream, primary endpoint will not have m3u8 URLs
        if not traverse_obj(formats, lambda _, v: v['ext'] == 'mp4'):
            live_info = merge_dicts(live_info, self._call_api(
                'https://www.tiktok.com/api/live/detail/', 'roomID', room_id, uploader, key='LiveRoomInfo'))
            if url_or_none(live_info.get('liveUrl')):
                formats.append({
                    'url': live_info['liveUrl'],
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'format_id': 'hls-fallback',
                    'vcodec': 'h264',
                    'quality': get_quality('origin'),
                })

        uploader = uploader or traverse_obj(live_info, ('ownerInfo', 'uniqueId'), ('owner', 'display_id'))

        return {
            'id': room_id,
            'uploader': uploader,
            'uploader_url': format_field(uploader, None, self._UPLOADER_URL_FORMAT) or None,
            'is_live': True,
            'formats': formats,
            '_format_sort_fields': ('quality', 'ext'),
            **traverse_obj(live_info, {
                'title': 'title',
                'uploader_id': (('ownerInfo', 'owner'), 'id', {str_or_none}),
                'creator': (('ownerInfo', 'owner'), 'nickname'),
                'concurrent_view_count': (('user_count', ('liveRoomStats', 'userCount')), {int_or_none}),
            }, get_all=False),
        }
