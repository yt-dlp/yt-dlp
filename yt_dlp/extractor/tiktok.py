import itertools
import json
import random
import re
import string
import time

from .common import InfoExtractor
from ..compat import compat_urllib_parse_unquote, compat_urllib_parse_urlparse
from ..utils import (
    ExtractorError,
    HEADRequest,
    LazyList,
    UnsupportedError,
    UserNotLive,
    determine_ext,
    format_field,
    get_element_by_id,
    get_first,
    int_or_none,
    join_nonempty,
    merge_dicts,
    qualities,
    remove_start,
    srt_subtitles_timecode,
    str_or_none,
    traverse_obj,
    try_call,
    try_get,
    url_or_none,
)


class TikTokBaseIE(InfoExtractor):
    _APP_VERSIONS = [('26.1.3', '260103'), ('26.1.2', '260102'), ('26.1.1', '260101'), ('25.6.2', '250602')]
    _WORKING_APP_VERSION = None
    _APP_NAME = 'trill'
    _AID = 1180
    _UPLOADER_URL_FORMAT = 'https://www.tiktok.com/@%s'
    _WEBPAGE_HOST = 'https://www.tiktok.com/'
    QUALITIES = ('360p', '540p', '720p', '1080p')

    @property
    def _API_HOSTNAME(self):
        return self._configuration_arg(
            'api_hostname', ['api16-normal-c-useast1a.tiktokv.com'], ie_key=TikTokIE)[0]

    @staticmethod
    def _create_url(user_id, video_id):
        return f'https://www.tiktok.com/@{user_id or "_"}/video/{video_id}'

    def _get_sigi_state(self, webpage, display_id):
        return self._parse_json(get_element_by_id(
            'SIGI_STATE|sigi-persisted-data', webpage, escape_value=False), display_id)

    def _call_api_impl(self, ep, query, manifest_app_version, video_id, fatal=True,
                       note='Downloading API JSON', errnote='Unable to download API page'):
        self._set_cookie(self._API_HOSTNAME, 'odin_tt', ''.join(random.choices('0123456789abcdef', k=160)))
        webpage_cookies = self._get_cookies(self._WEBPAGE_HOST)
        if webpage_cookies.get('sid_tt'):
            self._set_cookie(self._API_HOSTNAME, 'sid_tt', webpage_cookies['sid_tt'].value)
        return self._download_json(
            'https://%s/aweme/v1/%s/' % (self._API_HOSTNAME, ep), video_id=video_id,
            fatal=fatal, note=note, errnote=errnote, headers={
                'User-Agent': f'com.ss.android.ugc.{self._APP_NAME}/{manifest_app_version} (Linux; U; Android 13; en_US; Pixel 7; Build/TD1A.220804.031; Cronet/58.0.2991.0)',
                'Accept': 'application/json',
            }, query=query)

    def _build_api_query(self, query, app_version, manifest_app_version):
        return {
            **query,
            'version_name': app_version,
            'version_code': manifest_app_version,
            'build_number': app_version,
            'manifest_version_code': manifest_app_version,
            'update_version_code': manifest_app_version,
            'openudid': ''.join(random.choices('0123456789abcdef', k=16)),
            'uuid': ''.join(random.choices(string.digits, k=16)),
            '_rticket': int(time.time() * 1000),
            'ts': int(time.time()),
            'device_brand': 'Google',
            'device_type': 'Pixel 7',
            'device_platform': 'android',
            'resolution': '1080*2400',
            'dpi': 420,
            'os_version': '13',
            'os_api': '29',
            'carrier_region': 'US',
            'sys_region': 'US',
            'region': 'US',
            'app_name': self._APP_NAME,
            'app_language': 'en',
            'language': 'en',
            'timezone_name': 'America/New_York',
            'timezone_offset': '-14400',
            'channel': 'googleplay',
            'ac': 'wifi',
            'mcc_mnc': '310260',
            'is_my_cn': 0,
            'aid': self._AID,
            'ssmix': 'a',
            'as': 'a1qwert123',
            'cp': 'cbfhckdckkde1',
        }

    def _call_api(self, ep, query, video_id, fatal=True,
                  note='Downloading API JSON', errnote='Unable to download API page'):
        if not self._WORKING_APP_VERSION:
            app_version = self._configuration_arg('app_version', [''], ie_key=TikTokIE.ie_key())[0]
            manifest_app_version = self._configuration_arg('manifest_app_version', [''], ie_key=TikTokIE.ie_key())[0]
            if app_version and manifest_app_version:
                self._WORKING_APP_VERSION = (app_version, manifest_app_version)
                self.write_debug('Imported app version combo from extractor arguments')
            elif app_version or manifest_app_version:
                self.report_warning('Only one of the two required version params are passed as extractor arguments', only_once=True)

        if self._WORKING_APP_VERSION:
            app_version, manifest_app_version = self._WORKING_APP_VERSION
            real_query = self._build_api_query(query, app_version, manifest_app_version)
            return self._call_api_impl(ep, real_query, manifest_app_version, video_id, fatal, note, errnote)

        for count, (app_version, manifest_app_version) in enumerate(self._APP_VERSIONS, start=1):
            real_query = self._build_api_query(query, app_version, manifest_app_version)
            try:
                res = self._call_api_impl(ep, real_query, manifest_app_version, video_id, fatal, note, errnote)
                self._WORKING_APP_VERSION = (app_version, manifest_app_version)
                return res
            except ExtractorError as e:
                if isinstance(e.cause, json.JSONDecodeError) and e.cause.pos == 0:
                    if count == len(self._APP_VERSIONS):
                        if fatal:
                            raise e
                        else:
                            self.report_warning(str(e.cause or e.msg))
                            return
                    self.report_warning('%s. Retrying... (attempt %s of %s)' % (str(e.cause or e.msg), count, len(self._APP_VERSIONS)))
                    continue
                raise e

    def _extract_aweme_app(self, aweme_id):
        feed_list = self._call_api(
            'feed', {'aweme_id': aweme_id}, aweme_id, note='Downloading video feed',
            errnote='Unable to download video feed').get('aweme_list') or []
        aweme_detail = next((aweme for aweme in feed_list if str(aweme.get('aweme_id')) == aweme_id), None)
        if not aweme_detail:
            raise ExtractorError('Unable to find video in feed', video_id=aweme_id)
        return self._parse_aweme_video_app(aweme_detail)

    def _get_subtitles(self, aweme_detail, aweme_id):
        # TODO: Extract text positioning info
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
                    for i, line in enumerate(caption_json['utterances']) if line.get('text'))
            })
        # feed endpoint subs
        if not subtitles:
            for caption in traverse_obj(aweme_detail, ('video', 'cla_info', 'caption_infos', ...), expected_type=dict):
                if not caption.get('url'):
                    continue
                subtitles.setdefault(caption.get('lang') or 'en', []).append({
                    'ext': remove_start(caption.get('caption_format'), 'web'),
                    'url': caption['url'],
                })
        # webpage subs
        if not subtitles:
            for caption in traverse_obj(aweme_detail, ('video', 'subtitleInfos', ...), expected_type=dict):
                if not caption.get('Url'):
                    continue
                subtitles.setdefault(caption.get('LanguageCodeName') or 'en', []).append({
                    'ext': remove_start(caption.get('Format'), 'web'),
                    'url': caption['Url'],
                })
        return subtitles

    def _parse_aweme_video_app(self, aweme_detail):
        aweme_id = aweme_detail['aweme_id']
        video_info = aweme_detail['video']

        def parse_url_key(url_key):
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

        known_resolutions = {}

        def mp3_meta(url):
            return {
                'format_note': 'Music track',
                'ext': 'mp3',
                'acodec': 'mp3',
                'vcodec': 'none',
                'width': None,
                'height': None,
            } if determine_ext(url) == 'mp3' else {}

        def extract_addr(addr, add_meta={}):
            parsed_meta, res = parse_url_key(addr.get('url_key', ''))
            if res:
                known_resolutions.setdefault(res, {}).setdefault('height', add_meta.get('height') or addr.get('height'))
                known_resolutions[res].setdefault('width', add_meta.get('width') or addr.get('width'))
                parsed_meta.update(known_resolutions.get(res, {}))
                add_meta.setdefault('height', int_or_none(res[:-1]))
            return [{
                'url': url,
                'filesize': int_or_none(addr.get('data_size')),
                'ext': 'mp4',
                'acodec': 'aac',
                'source_preference': -2 if 'aweme/v1' in url else -1,  # Downloads from API might get blocked
                **add_meta, **parsed_meta,
                'format_note': join_nonempty(
                    add_meta.get('format_note'), '(API)' if 'aweme/v1' in url else None, delim=' '),
                **mp3_meta(url),
            } for url in addr.get('url_list') or []]

        # Hack: Add direct video links first to prioritize them when removing duplicate formats
        formats = []
        if video_info.get('play_addr'):
            formats.extend(extract_addr(video_info['play_addr'], {
                'format_id': 'play_addr',
                'format_note': 'Direct video',
                'vcodec': 'h265' if traverse_obj(
                    video_info, 'is_bytevc1', 'is_h265') else 'h264',  # TODO: Check for "direct iOS" videos, like https://www.tiktok.com/@cookierun_dev/video/7039716639834656002
                'width': video_info.get('width'),
                'height': video_info.get('height'),
            }))
        if video_info.get('download_addr'):
            formats.extend(extract_addr(video_info['download_addr'], {
                'format_id': 'download_addr',
                'format_note': 'Download video%s' % (', watermarked' if video_info.get('has_watermark') else ''),
                'vcodec': 'h264',
                'width': video_info.get('width'),
                'height': video_info.get('height'),
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
                self._set_cookie(compat_urllib_parse_urlparse(f['url']).hostname, 'sid_tt', auth_cookie.value)

        thumbnails = []
        for cover_id in ('cover', 'ai_dynamic_cover', 'animated_cover', 'ai_dynamic_cover_bak',
                         'origin_cover', 'dynamic_cover'):
            for cover_url in traverse_obj(video_info, (cover_id, 'url_list', ...)):
                thumbnails.append({
                    'id': cover_id,
                    'url': cover_url,
                })

        stats_info = aweme_detail.get('statistics') or {}
        author_info = aweme_detail.get('author') or {}
        music_info = aweme_detail.get('music') or {}
        user_url = self._UPLOADER_URL_FORMAT % (traverse_obj(author_info,
                                                             'sec_uid', 'id', 'uid', 'unique_id',
                                                             expected_type=str_or_none, get_all=False))
        labels = traverse_obj(aweme_detail, ('hybrid_label', ..., 'text'), expected_type=str)

        contained_music_track = traverse_obj(
            music_info, ('matched_song', 'title'), ('matched_pgc_sound', 'title'), expected_type=str)
        contained_music_author = traverse_obj(
            music_info, ('matched_song', 'author'), ('matched_pgc_sound', 'author'), 'author', expected_type=str)

        is_generic_og_trackname = music_info.get('is_original_sound') and music_info.get('title') == 'original sound - %s' % music_info.get('owner_handle')
        if is_generic_og_trackname:
            music_track, music_author = contained_music_track or 'original sound', contained_music_author
        else:
            music_track, music_author = music_info.get('title'), music_info.get('author')

        return {
            'id': aweme_id,
            'extractor_key': TikTokIE.ie_key(),
            'extractor': TikTokIE.IE_NAME,
            'webpage_url': self._create_url(author_info.get('uid'), aweme_id),
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
            **traverse_obj(author_info, {
                'uploader': 'unique_id',
                'uploader_id': 'uid',
                'creator': 'nickname',
                'channel_id': 'sec_uid',
            }, expected_type=str_or_none),
            'uploader_url': user_url,
            'track': music_track,
            'album': str_or_none(music_info.get('album')) or None,
            'artist': music_author or None,
            'formats': formats,
            'subtitles': self.extract_subtitles(aweme_detail, aweme_id),
            'thumbnails': thumbnails,
            'duration': int_or_none(traverse_obj(video_info, 'duration', ('download_addr', 'duration')), scale=1000),
            'availability': self._availability(
                is_private='Private' in labels,
                needs_subscription='Friends only' in labels,
                is_unlisted='Followers only' in labels),
            '_format_sort_fields': ('quality', 'codec', 'size', 'br'),
        }

    def _parse_aweme_video_web(self, aweme_detail, webpage_url, video_id):
        video_info = aweme_detail['video']
        author_info = traverse_obj(aweme_detail, 'authorInfo', 'author', expected_type=dict, default={})
        music_info = aweme_detail.get('music') or {}
        stats_info = aweme_detail.get('stats') or {}
        channel_id = traverse_obj(author_info or aweme_detail, (('authorSecId', 'secUid'), {str}), get_all=False)
        user_url = self._UPLOADER_URL_FORMAT % channel_id if channel_id else None

        formats = []
        width = int_or_none(video_info.get('width'))
        height = int_or_none(video_info.get('height'))

        for play_url in traverse_obj(video_info, ('playAddr', ((..., 'src'), None), {url_or_none})):
            formats.append({
                'url': self._proto_relative_url(play_url),
                'ext': 'mp4',
                'width': width,
                'height': height,
            })

        for download_url in traverse_obj(video_info, (('downloadAddr', ('download', 'url')), {url_or_none})):
            formats.append({
                'format_id': 'download',
                'url': self._proto_relative_url(download_url),
                'ext': 'mp4',
                'width': width,
                'height': height,
            })

        self._remove_duplicate_formats(formats)

        thumbnails = []
        for thumb_url in traverse_obj(aweme_detail, (
                (None, 'video'), ('thumbnail', 'cover', 'dynamicCover', 'originCover'), {url_or_none})):
            thumbnails.append({
                'url': self._proto_relative_url(thumb_url),
                'width': width,
                'height': height,
            })

        return {
            'id': video_id,
            **traverse_obj(aweme_detail, {
                'title': ('desc', {str}),
                'description': ('desc', {str}),
                'duration': ('video', 'duration', {int_or_none}),
                'timestamp': ('createTime', {int_or_none}),
            }),
            **traverse_obj(author_info or aweme_detail, {
                'creator': ('nickname', {str}),
                'uploader': (('uniqueId', 'author'), {str}),
                'uploader_id': (('authorId', 'uid', 'id'), {str_or_none}),
            }, get_all=False),
            **traverse_obj(stats_info, {
                'view_count': 'playCount',
                'like_count': 'diggCount',
                'repost_count': 'shareCount',
                'comment_count': 'commentCount',
            }, expected_type=int_or_none),
            **traverse_obj(music_info, {
                'track': 'title',
                'album': ('album', {lambda x: x or None}),
                'artist': 'authorName',
            }, expected_type=str),
            'channel_id': channel_id,
            'uploader_url': user_url,
            'formats': formats,
            'thumbnails': thumbnails,
            'http_headers': {
                'Referer': webpage_url,
            }
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
        'md5': '6f3cf8cdd9b28cb8363fe0a9a160695b',
        'info_dict': {
            'id': '6742501081818877190',
            'ext': 'mp4',
            'title': 'md5:5e2a23877420bb85ce6521dbee39ba94',
            'description': 'md5:5e2a23877420bb85ce6521dbee39ba94',
            'duration': 27,
            'height': 960,
            'width': 540,
            'uploader': 'patrox',
            'uploader_id': '18702747',
            'uploader_url': 'https://www.tiktok.com/@MS4wLjABAAAAiFnldaILebi5heDoVU6bn4jBWWycX6-9U3xuNPqZ8Ws',
            'channel_id': 'MS4wLjABAAAAiFnldaILebi5heDoVU6bn4jBWWycX6-9U3xuNPqZ8Ws',
            'creator': 'patroX',
            'thumbnail': r're:^https?://[\w\/\.\-]+(~[\w\-]+\.image)?',
            'upload_date': '20190930',
            'timestamp': 1569860870,
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'artist': 'Evan Todd, Jessica Keenan Wynn, Alice Lee, Barrett Wilbert Weed & Jon Eidson',
            'track': 'Big Fun',
        },
    }, {
        # Banned audio, only available on the app
        'url': 'https://www.tiktok.com/@barudakhb_/video/6984138651336838402',
        'info_dict': {
            'id': '6984138651336838402',
            'ext': 'mp4',
            'title': 'Balas @yolaaftwsr hayu yu ? #SquadRandom_ 🔥',
            'description': 'Balas @yolaaftwsr hayu yu ? #SquadRandom_ 🔥',
            'uploader': 'barudakhb_',
            'creator': 'md5:29f238c49bc0c176cb3cef1a9cea9fa6',
            'uploader_id': '6974687867511718913',
            'uploader_url': 'https://www.tiktok.com/@MS4wLjABAAAAbhBwQC-R1iKoix6jDFsF-vBdfx2ABoDjaZrM9fX6arU3w71q3cOWgWuTXn1soZ7d',
            'channel_id': 'MS4wLjABAAAAbhBwQC-R1iKoix6jDFsF-vBdfx2ABoDjaZrM9fX6arU3w71q3cOWgWuTXn1soZ7d',
            'track': 'Boka Dance',
            'artist': 'md5:29f238c49bc0c176cb3cef1a9cea9fa6',
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
            'creator': 'Slap And Run',
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
    }, {
        # Video without title and description
        'url': 'https://www.tiktok.com/@pokemonlife22/video/7059698374567611694',
        'info_dict': {
            'id': '7059698374567611694',
            'ext': 'mp4',
            'title': 'TikTok video #7059698374567611694',
            'description': '',
            'uploader': 'pokemonlife22',
            'creator': 'Pokemon',
            'uploader_id': '6820838815978423302',
            'uploader_url': 'https://www.tiktok.com/@MS4wLjABAAAA0tF1nBwQVVMyrGu3CqttkNgM68Do1OXUFuCY0CRQk8fEtSVDj89HqoqvbSTmUP2W',
            'channel_id': 'MS4wLjABAAAA0tF1nBwQVVMyrGu3CqttkNgM68Do1OXUFuCY0CRQk8fEtSVDj89HqoqvbSTmUP2W',
            'track': 'original sound',
            'timestamp': 1643714123,
            'duration': 6,
            'thumbnail': r're:^https?://[\w\/\.\-]+(~[\w\-]+\.image)?',
            'upload_date': '20220201',
            'artist': 'Pokemon',
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
            'creator': 'Antaura',
            'uploader': '_le_cannibale_',
            'uploader_id': '6604511138619654149',
            'uploader_url': 'https://www.tiktok.com/@MS4wLjABAAAAoShJqaw_5gvy48y3azFeFcT4jeyKWbB0VVYasOCt2tTLwjNFIaDcHAM4D-QGXFOP',
            'channel_id': 'MS4wLjABAAAAoShJqaw_5gvy48y3azFeFcT4jeyKWbB0VVYasOCt2tTLwjNFIaDcHAM4D-QGXFOP',
            'artist': 'nathan !',
            'track': 'grahamscott canon',
            'upload_date': '20220905',
            'timestamp': 1662406249,
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'thumbnail': r're:^https://.+\.webp',
        },
    }, {
        # only available via web
        'url': 'https://www.tiktok.com/@moxypatch/video/7206382937372134662',
        'md5': '8d8c0be14127020cd9f5def4a2e6b411',
        'info_dict': {
            'id': '7206382937372134662',
            'ext': 'mp4',
            'title': 'md5:1d95c0b96560ca0e8a231af4172b2c0a',
            'description': 'md5:1d95c0b96560ca0e8a231af4172b2c0a',
            'creator': 'MoxyPatch',
            'uploader': 'moxypatch',
            'uploader_id': '7039142049363379205',
            'uploader_url': 'https://www.tiktok.com/@MS4wLjABAAAAFhqKnngMHJSsifL0w1vFOP5kn3Ndo1ODp0XuIBkNMBCkALTvwILdpu12g3pTtL4V',
            'channel_id': 'MS4wLjABAAAAFhqKnngMHJSsifL0w1vFOP5kn3Ndo1ODp0XuIBkNMBCkALTvwILdpu12g3pTtL4V',
            'artist': 'your worst nightmare',
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
        'url': 'https://www.tiktok.com/@tatemcrae/video/7107337212743830830',
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
            'creator': 't8',
            'artist': 't8',
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
        'params': {'format': 'bytevc1_1080p_808907-0'},
    }, {
        # Auto-captions available
        'url': 'https://www.tiktok.com/@hankgreen1/video/7047596209028074758',
        'only_matching': True
    }]

    def _real_extract(self, url):
        video_id, user_id = self._match_valid_url(url).group('id', 'user_id')
        try:
            return self._extract_aweme_app(video_id)
        except ExtractorError as e:
            self.report_warning(f'{e}; trying with webpage')

        url = self._create_url(user_id, video_id)
        webpage = self._download_webpage(url, video_id, headers={'User-Agent': 'Mozilla/5.0'})
        next_data = self._search_nextjs_data(webpage, video_id, default='{}')
        if next_data:
            status = traverse_obj(next_data, ('props', 'pageProps', 'statusCode'), expected_type=int) or 0
            video_data = traverse_obj(next_data, ('props', 'pageProps', 'itemInfo', 'itemStruct'), expected_type=dict)
        else:
            sigi_data = self._get_sigi_state(webpage, video_id)
            status = traverse_obj(sigi_data, ('VideoPage', 'statusCode'), expected_type=int) or 0
            video_data = traverse_obj(sigi_data, ('ItemModule', video_id), expected_type=dict)

        if status == 0:
            return self._parse_aweme_video_web(video_data, url, video_id)
        elif status == 10216:
            raise ExtractorError('This video is private', expected=True)
        raise ExtractorError('Video not available', video_id=video_id)


class TikTokUserIE(TikTokBaseIE):
    IE_NAME = 'tiktok:user'
    _VALID_URL = r'https?://(?:www\.)?tiktok\.com/@(?P<id>[\w\.-]+)/?(?:$|[#?])'
    _WORKING = False
    _TESTS = [{
        'url': 'https://tiktok.com/@corgibobaa?lang=en',
        'playlist_mincount': 45,
        'info_dict': {
            'id': '6935371178089399301',
            'title': 'corgibobaa',
            'thumbnail': r're:https://.+_1080x1080\.webp'
        },
        'expected_warnings': ['Retrying']
    }, {
        'url': 'https://www.tiktok.com/@6820838815978423302',
        'playlist_mincount': 5,
        'info_dict': {
            'id': '6820838815978423302',
            'title': '6820838815978423302',
            'thumbnail': r're:https://.+_1080x1080\.webp'
        },
        'expected_warnings': ['Retrying']
    }, {
        'url': 'https://www.tiktok.com/@meme',
        'playlist_mincount': 593,
        'info_dict': {
            'id': '79005827461758976',
            'title': 'meme',
            'thumbnail': r're:https://.+_1080x1080\.webp'
        },
        'expected_warnings': ['Retrying']
    }]

    r'''  # TODO: Fix by adding _signature to api_url
    def _entries(self, webpage, user_id, username):
        secuid = self._search_regex(r'\"secUid\":\"(?P<secUid>[^\"]+)', webpage, username)
        verifyfp_cookie = self._get_cookies('https://www.tiktok.com').get('s_v_web_id')
        if not verifyfp_cookie:
            raise ExtractorError('Improper cookies (missing s_v_web_id).', expected=True)
        api_url = f'https://m.tiktok.com/api/post/item_list/?aid=1988&cookie_enabled=true&count=30&verifyFp={verifyfp_cookie.value}&secUid={secuid}&cursor='
        cursor = '0'
        for page in itertools.count():
            data_json = self._download_json(api_url + cursor, username, note='Downloading Page %d' % page)
            for video in data_json.get('itemList', []):
                video_id = video['id']
                video_url = f'https://www.tiktok.com/@{user_id}/video/{video_id}'
                yield self._url_result(video_url, 'TikTok', video_id, str_or_none(video.get('desc')))
            if not data_json.get('hasMore'):
                break
            cursor = data_json['cursor']
    '''

    def _video_entries_api(self, webpage, user_id, username):
        query = {
            'user_id': user_id,
            'count': 21,
            'max_cursor': 0,
            'min_cursor': 0,
            'retry_type': 'no_retry',
            'device_id': ''.join(random.choices(string.digits, k=19)),  # Some endpoints don't like randomized device_id, so it isn't directly set in _call_api.
        }

        for page in itertools.count(1):
            for retry in self.RetryManager():
                try:
                    post_list = self._call_api(
                        'aweme/post', query, username, note=f'Downloading user video list page {page}',
                        errnote='Unable to download user video list')
                except ExtractorError as e:
                    if isinstance(e.cause, json.JSONDecodeError) and e.cause.pos == 0:
                        retry.error = e
                        continue
                    raise
            yield from post_list.get('aweme_list', [])
            if not post_list.get('has_more'):
                break
            query['max_cursor'] = post_list['max_cursor']

    def _entries_api(self, user_id, videos):
        for video in videos:
            yield {
                **self._parse_aweme_video_app(video),
                'extractor_key': TikTokIE.ie_key(),
                'extractor': 'TikTok',
                'webpage_url': f'https://tiktok.com/@{user_id}/video/{video["aweme_id"]}',
            }

    def _real_extract(self, url):
        user_name = self._match_id(url)
        webpage = self._download_webpage(url, user_name, headers={
            'User-Agent': 'facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)'
        })
        user_id = self._html_search_regex(r'snssdk\d*://user/profile/(\d+)', webpage, 'user ID', default=None) or user_name

        videos = LazyList(self._video_entries_api(webpage, user_id, user_name))
        thumbnail = traverse_obj(videos, (0, 'author', 'avatar_larger', 'url_list', 0))

        return self.playlist_result(self._entries_api(user_id, videos), user_id, user_name, thumbnail=thumbnail)


class TikTokBaseListIE(TikTokBaseIE):  # XXX: Conventionally, base classes should end with BaseIE/InfoExtractor
    def _entries(self, list_id, display_id):
        query = {
            self._QUERY_NAME: list_id,
            'cursor': 0,
            'count': 20,
            'type': 5,
            'device_id': ''.join(random.choices(string.digits, k=19))
        }

        for page in itertools.count(1):
            for retry in self.RetryManager():
                try:
                    post_list = self._call_api(
                        self._API_ENDPOINT, query, display_id, note=f'Downloading video list page {page}',
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
            'id': '6956990112127585029'
        },
        'expected_warnings': ['Retrying']
    }, {
        # Actual entries are less than listed video count
        'url': 'https://www.tiktok.com/music/jiefei-soap-remix-7036843036118469381',
        'playlist_mincount': 2182,
        'info_dict': {
            'id': '7036843036118469381'
        },
        'expected_warnings': ['Retrying']
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
        'expected_warnings': ['Retrying']
    }, {
        # Different entries between mobile and web, depending on region
        'url': 'https://www.tiktok.com/sticker/Elf-Friend-479565',
        'only_matching': True
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
        'expected_warnings': ['Retrying']
    }, {
        'url': 'https://tiktok.com/tag/fypシ?is_copy_url=0&is_from_webapp=v1',
        'only_matching': True
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id, headers={
            'User-Agent': 'facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)'
        })
        tag_id = self._html_search_regex(r'snssdk\d*://challenge/detail/(\d+)', webpage, 'tag ID')
        return self.playlist_result(self._entries(tag_id, display_id), tag_id, display_id)


class DouyinIE(TikTokBaseIE):
    _VALID_URL = r'https?://(?:www\.)?douyin\.com/video/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.douyin.com/video/6961737553342991651',
        'md5': 'a97db7e3e67eb57bf40735c022ffa228',
        'info_dict': {
            'id': '6961737553342991651',
            'ext': 'mp4',
            'title': '#杨超越  小小水手带你去远航❤️',
            'description': '#杨超越  小小水手带你去远航❤️',
            'uploader_id': '110403406559',
            'uploader_url': 'https://www.douyin.com/user/MS4wLjABAAAAEKnfa654JAJ_N5lgZDQluwsxmY0lhfmEYNQBBkwGG98',
            'channel_id': 'MS4wLjABAAAAEKnfa654JAJ_N5lgZDQluwsxmY0lhfmEYNQBBkwGG98',
            'creator': '杨超越',
            'duration': 19782,
            'timestamp': 1620905839,
            'upload_date': '20210513',
            'track': '@杨超越创作的原声',
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'thumbnail': r're:https?://.+\.jpe?g',
        },
    }, {
        'url': 'https://www.douyin.com/video/6982497745948921092',
        'md5': '34a87ebff3833357733da3fe17e37c0e',
        'info_dict': {
            'id': '6982497745948921092',
            'ext': 'mp4',
            'title': '这个夏日和小羊@杨超越 一起遇见白色幻想',
            'description': '这个夏日和小羊@杨超越 一起遇见白色幻想',
            'uploader_id': '408654318141572',
            'uploader_url': 'https://www.douyin.com/user/MS4wLjABAAAAZJpnglcjW2f_CMVcnqA_6oVBXKWMpH0F8LIHuUu8-lA',
            'channel_id': 'MS4wLjABAAAAZJpnglcjW2f_CMVcnqA_6oVBXKWMpH0F8LIHuUu8-lA',
            'creator': '杨超越工作室',
            'duration': 42479,
            'timestamp': 1625739481,
            'upload_date': '20210708',
            'track': '@杨超越工作室创作的原声',
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'thumbnail': r're:https?://.+\.jpe?g',
        },
    }, {
        'url': 'https://www.douyin.com/video/6953975910773099811',
        'md5': 'dde3302460f19db59c47060ff013b902',
        'info_dict': {
            'id': '6953975910773099811',
            'ext': 'mp4',
            'title': '#一起看海  出现在你的夏日里',
            'description': '#一起看海  出现在你的夏日里',
            'uploader_id': '110403406559',
            'uploader_url': 'https://www.douyin.com/user/MS4wLjABAAAAEKnfa654JAJ_N5lgZDQluwsxmY0lhfmEYNQBBkwGG98',
            'channel_id': 'MS4wLjABAAAAEKnfa654JAJ_N5lgZDQluwsxmY0lhfmEYNQBBkwGG98',
            'creator': '杨超越',
            'duration': 17343,
            'timestamp': 1619098692,
            'upload_date': '20210422',
            'track': '@杨超越创作的原声',
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
        'md5': 'cf9f11f0ec45d131445ec2f06766e122',
        'info_dict': {
            'id': '6963263655114722595',
            'ext': 'mp4',
            'title': '#哪个爱豆的105度最甜 换个角度看看我哈哈',
            'description': '#哪个爱豆的105度最甜 换个角度看看我哈哈',
            'uploader_id': '110403406559',
            'uploader_url': 'https://www.douyin.com/user/MS4wLjABAAAAEKnfa654JAJ_N5lgZDQluwsxmY0lhfmEYNQBBkwGG98',
            'channel_id': 'MS4wLjABAAAAEKnfa654JAJ_N5lgZDQluwsxmY0lhfmEYNQBBkwGG98',
            'creator': '杨超越',
            'duration': 15115,
            'timestamp': 1621261163,
            'upload_date': '20210517',
            'track': '@杨超越创作的原声',
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
            'thumbnail': r're:https?://.+\.jpe?g',
        },
    }]
    _APP_VERSIONS = [('23.3.0', '230300')]
    _APP_NAME = 'aweme'
    _AID = 1128
    _API_HOSTNAME = 'aweme.snssdk.com'
    _UPLOADER_URL_FORMAT = 'https://www.douyin.com/user/%s'
    _WEBPAGE_HOST = 'https://www.douyin.com/'

    def _real_extract(self, url):
        video_id = self._match_id(url)

        try:
            return self._extract_aweme_app(video_id)
        except ExtractorError as e:
            e.expected = True
            self.to_screen(f'{e}; trying with webpage')

        webpage = self._download_webpage(url, video_id)
        render_data = self._search_json(
            r'<script [^>]*\bid=[\'"]RENDER_DATA[\'"][^>]*>', webpage, 'render data', video_id,
            contains_pattern=r'%7B(?s:.+)%7D', fatal=False, transform_source=compat_urllib_parse_unquote)
        if not render_data:
            # TODO: Run verification challenge code to generate signature cookies
            cookies = self._get_cookies(self._WEBPAGE_HOST)
            expected = not cookies.get('s_v_web_id') or not cookies.get('ttwid')
            raise ExtractorError(
                'Fresh cookies (not necessarily logged in) are needed', expected=expected)

        return self._parse_aweme_video_web(get_first(render_data, ('aweme', 'detail')), url, video_id)


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
            HEADRequest(url), self._match_id(url), headers={'User-Agent': 'facebookexternalhit/1.1'}).geturl()
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
            data = try_call(lambda: self._get_sigi_state(webpage, uploader or room_id))
            room_id = (traverse_obj(data, ('UserModule', 'users', ..., 'roomId', {str_or_none}), get_all=False)
                       or self._search_regex(r'snssdk\d*://live\?room_id=(\d+)', webpage, 'room ID', default=None)
                       or room_id)
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
                'tbr': ('vbitrate', {lambda x: int_or_none(x, 1000)}),
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
