# coding: utf-8
from __future__ import unicode_literals

import re
import json
import datetime

from .common import InfoExtractor
from ..postprocessor.ffmpeg import FFmpegPostProcessor
from ..compat import (
    compat_str,
    compat_parse_qs,
    compat_urllib_parse_urlparse,
)
from ..utils import (
    dict_get,
    ExtractorError,
    int_or_none,
    float_or_none,
    OnDemandPagedList,
    parse_duration,
    parse_iso8601,
    PostProcessingError,
    str_or_none,
    remove_start,
    try_get,
    unified_timestamp,
    urlencode_postdata,
    xpath_text,
)


class NiconicoIE(InfoExtractor):
    IE_NAME = 'niconico'
    IE_DESC = 'ニコニコ動画'

    _TESTS = [{
        'url': 'http://www.nicovideo.jp/watch/sm22312215',
        'md5': 'a5bad06f1347452102953f323c69da34s',
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
        },
        'skip': 'Requires an account',
    }, {
        # File downloaded with and without credentials are different, so omit
        # the md5 field
        'url': 'http://www.nicovideo.jp/watch/nm14296458',
        'info_dict': {
            'id': 'nm14296458',
            'ext': 'swf',
            'title': '【鏡音リン】Dance on media【オリジナル】take2!',
            'description': 'md5:689f066d74610b3b22e0f1739add0f58',
            'thumbnail': r're:https?://.*',
            'uploader': 'りょうた',
            'uploader_id': '18822557',
            'upload_date': '20110429',
            'timestamp': 1304065916,
            'duration': 209,
        },
        'skip': 'Requires an account',
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
        'md5': '8fa81c364eb619d4085354eab075598a',
        'info_dict': {
            'id': 'sm1151009',
            'ext': 'mp4',
            'title': 'マスターシステム本体内蔵のスペハリのメインテーマ（ＰＳＧ版）',
            'description': 'md5:6ee077e0581ff5019773e2e714cdd0b7',
            'thumbnail': r're:https?://.*',
            'duration': 184,
            'timestamp': 1190868283,
            'upload_date': '20070927',
            'uploader': 'denden2',
            'uploader_id': '1392194',
            'view_count': int,
            'comment_count': int,
        },
        'skip': 'Requires an account',
    }, {
        # "New" HTML5 video
        # md5 is unstable
        'url': 'http://www.nicovideo.jp/watch/sm31464864',
        'info_dict': {
            'id': 'sm31464864',
            'ext': 'mp4',
            'title': '新作TVアニメ「戦姫絶唱シンフォギアAXZ」PV 最高画質',
            'description': 'md5:e52974af9a96e739196b2c1ca72b5feb',
            'timestamp': 1498514060,
            'upload_date': '20170626',
            'uploader': 'ゲスト',
            'uploader_id': '40826363',
            'thumbnail': r're:https?://.*',
            'duration': 198,
            'view_count': int,
            'comment_count': int,
        },
        'skip': 'Requires an account',
    }, {
        # Video without owner
        'url': 'http://www.nicovideo.jp/watch/sm18238488',
        'md5': 'd265680a1f92bdcbbd2a507fc9e78a9e',
        'info_dict': {
            'id': 'sm18238488',
            'ext': 'mp4',
            'title': '【実写版】ミュータントタートルズ',
            'description': 'md5:15df8988e47a86f9e978af2064bf6d8e',
            'timestamp': 1341160408,
            'upload_date': '20120701',
            'uploader': None,
            'uploader_id': None,
            'thumbnail': r're:https?://.*',
            'duration': 5271,
            'view_count': int,
            'comment_count': int,
        },
        'skip': 'Requires an account',
    }, {
        'url': 'http://sp.nicovideo.jp/watch/sm28964488?ss_pos=1&cp_in=wt_tg',
        'only_matching': True,
    }]

    _VALID_URL = r'https?://(?:www\.|secure\.|sp\.)?nicovideo\.jp/watch/(?P<id>(?:[a-z]{2})?[0-9]+)'
    _NETRC_MACHINE = 'niconico'

    def _real_initialize(self):
        self._login()

    def _login(self):
        username, password = self._get_login_info()
        # No authentication to be performed
        if not username:
            return True

        # Log in
        login_ok = True
        login_form_strs = {
            'mail_tel': username,
            'password': password,
        }
        urlh = self._request_webpage(
            'https://account.nicovideo.jp/api/v1/login', None,
            note='Logging in', errnote='Unable to log in',
            data=urlencode_postdata(login_form_strs))
        if urlh is False:
            login_ok = False
        else:
            parts = compat_urllib_parse_urlparse(urlh.geturl())
            if compat_parse_qs(parts.query).get('message', [None])[0] == 'cant_login':
                login_ok = False
        if not login_ok:
            self.report_warning('unable to log in: bad username or password')
        return login_ok

    def _get_heartbeat_info(self, info_dict):

        video_id, video_src_id, audio_src_id = info_dict['url'].split(':')[1].split('/')

        # Get video webpage for API data.
        webpage, handle = self._download_webpage_handle(
            'http://www.nicovideo.jp/watch/' + video_id, video_id)

        api_data = self._parse_json(self._html_search_regex(
            'data-api-data="([^"]+)"', webpage,
            'API data', default='{}'), video_id)

        session_api_data = try_get(api_data, lambda x: x['media']['delivery']['movie']['session'])
        session_api_endpoint = try_get(session_api_data, lambda x: x['urls'][0])

        # ping
        self._download_json(
            'https://nvapi.nicovideo.jp/v1/2ab0cbaa/watch', video_id,
            query={'t': try_get(api_data, lambda x: x['video']['dmcInfo']['tracking_id'])},
            headers={
                'Origin': 'https://www.nicovideo.jp',
                'Referer': 'https://www.nicovideo.jp/watch/' + video_id,
                'X-Frontend-Id': '6',
                'X-Frontend-Version': '0'
            })

        yesno = lambda x: 'yes' if x else 'no'

        # m3u8 (encryption)
        if 'encryption' in (try_get(api_data, lambda x: x['media']['delivery']['movie']) or {}):
            protocol = 'm3u8'
            session_api_http_parameters = {
                'parameters': {
                    'hls_parameters': {
                        'encryption': {
                            'hls_encryption_v1': {
                                'encrypted_key': try_get(api_data, lambda x: x['video']['dmcInfo']['encryption']['hls_encryption_v1']['encrypted_key']),
                                'key_uri': try_get(api_data, lambda x: x['video']['dmcInfo']['encryption']['hls_encryption_v1']['key_uri'])
                            }
                        },
                        'transfer_preset': '',
                        'use_ssl': yesno(session_api_endpoint['is_ssl']),
                        'use_well_known_port': yesno(session_api_endpoint['is_well_known_port']),
                        'segment_duration': 6000
                    }
                }
            }
        # http
        else:
            protocol = 'http'
            session_api_http_parameters = {
                'parameters': {
                    'http_output_download_parameters': {
                        'use_ssl': yesno(session_api_endpoint['isSsl']),
                        'use_well_known_port': yesno(session_api_endpoint['isWellKnownPort']),
                    }
                }
            }

        session_response = self._download_json(
            session_api_endpoint['url'], video_id,
            query={'_format': 'json'},
            headers={'Content-Type': 'application/json'},
            note='Downloading JSON metadata for %s' % info_dict['format_id'],
            data=json.dumps({
                'session': {
                    'client_info': {
                        'player_id': session_api_data.get('playerId'),
                    },
                    'content_auth': {
                        'auth_type': try_get(session_api_data, lambda x: x['authTypes'][session_api_data['protocols'][0]]),
                        'content_key_timeout': session_api_data.get('contentKeyTimeout'),
                        'service_id': 'nicovideo',
                        'service_user_id': session_api_data.get('serviceUserId')
                    },
                    'content_id': session_api_data.get('contentId'),
                    'content_src_id_sets': [{
                        'content_src_ids': [{
                            'src_id_to_mux': {
                                'audio_src_ids': [audio_src_id],
                                'video_src_ids': [video_src_id],
                            }
                        }]
                    }],
                    'content_type': 'movie',
                    'content_uri': '',
                    'keep_method': {
                        'heartbeat': {
                            'lifetime': session_api_data.get('heartbeatLifetime')
                        }
                    },
                    'priority': session_api_data.get('priority'),
                    'protocol': {
                        'name': 'http',
                        'parameters': {
                            'http_parameters': session_api_http_parameters
                        }
                    },
                    'recipe_id': session_api_data.get('recipeId'),
                    'session_operation_auth': {
                        'session_operation_auth_by_signature': {
                            'signature': session_api_data.get('signature'),
                            'token': session_api_data.get('token'),
                        }
                    },
                    'timing_constraint': 'unlimited'
                }
            }).encode())

        info_dict['url'] = session_response['data']['session']['content_uri']
        info_dict['protocol'] = protocol

        # get heartbeat info
        heartbeat_info_dict = {
            'url': session_api_endpoint['url'] + '/' + session_response['data']['session']['id'] + '?_format=json&_method=PUT',
            'data': json.dumps(session_response['data']),
            # interval, convert milliseconds to seconds, then halve to make a buffer.
            'interval': float_or_none(session_api_data.get('heartbeatLifetime'), scale=2000),
        }

        return info_dict, heartbeat_info_dict

    def _extract_format_for_quality(self, api_data, video_id, audio_quality, video_quality):
        def parse_format_id(id_code):
            mobj = re.match(r'''(?x)
                    (?:archive_)?
                    (?:(?P<codec>[^_]+)_)?
                    (?:(?P<br>[\d]+)kbps_)?
                    (?:(?P<res>[\d+]+)p_)?
                ''', '%s_' % id_code)
            return mobj.groupdict() if mobj else {}

        protocol = 'niconico_dmc'
        format_id = '-'.join(map(lambda s: remove_start(s['id'], 'archive_'), [video_quality, audio_quality]))
        vdict = parse_format_id(video_quality['id'])
        adict = parse_format_id(audio_quality['id'])
        resolution = try_get(video_quality, lambda x: x['metadata']['resolution'], dict) or {'height': vdict.get('res')}
        vbr = try_get(video_quality, lambda x: x['metadata']['bitrate'], float)

        return {
            'url': '%s:%s/%s/%s' % (protocol, video_id, video_quality['id'], audio_quality['id']),
            'format_id': format_id,
            'format_note': 'DMC %s' % try_get(video_quality, lambda x: x['metadata']['label'], compat_str),
            'ext': 'mp4',  # Session API are used in HTML5, which always serves mp4
            'vcodec': vdict.get('codec'),
            'acodec': adict.get('codec'),
            'vbr': float_or_none(vbr, 1000) or float_or_none(vdict.get('br')),
            'abr': float_or_none(audio_quality.get('bitrate'), 1000) or float_or_none(adict.get('br')),
            'height': int_or_none(resolution.get('height', vdict.get('res'))),
            'width': int_or_none(resolution.get('width')),
            'quality': -2 if 'low' in format_id else -1,  # Default quality value is -1
            'protocol': protocol,
            'http_headers': {
                'Origin': 'https://www.nicovideo.jp',
                'Referer': 'https://www.nicovideo.jp/watch/' + video_id,
            }
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        # Get video webpage for API data.
        webpage, handle = self._download_webpage_handle(
            'http://www.nicovideo.jp/watch/' + video_id, video_id)
        if video_id.startswith('so'):
            video_id = self._match_id(handle.geturl())

        api_data = self._parse_json(self._html_search_regex(
            'data-api-data="([^"]+)"', webpage,
            'API data', default='{}'), video_id)

        def get_video_info_web(items):
            return dict_get(api_data['video'], items)

        # Get video info
        video_info_xml = self._download_xml(
            'http://ext.nicovideo.jp/api/getthumbinfo/' + video_id,
            video_id, note='Downloading video info page')

        def get_video_info_xml(items):
            if not isinstance(items, list):
                items = [items]
            for item in items:
                ret = xpath_text(video_info_xml, './/' + item)
                if ret:
                    return ret

        if get_video_info_xml('error'):
            error_code = get_video_info_xml('code')

            if error_code == 'DELETED':
                raise ExtractorError('The video has been deleted.',
                                     expected=True)
            elif error_code == 'NOT_FOUND':
                raise ExtractorError('The video is not found.',
                                     expected=True)
            elif error_code == 'COMMUNITY':
                self.to_screen('%s: The video is community members only.' % video_id)
            else:
                raise ExtractorError('%s reports error: %s' % (self.IE_NAME, error_code))

        # Start extracting video formats
        formats = []

        # Get HTML5 videos info
        quality_info = try_get(api_data, lambda x: x['media']['delivery']['movie'])
        if not quality_info:
            raise ExtractorError('The video can\'t downloaded.', expected=True)

        for audio_quality in quality_info.get('audios') or {}:
            for video_quality in quality_info.get('videos') or {}:
                if not audio_quality.get('isAvailable') or not video_quality.get('isAvailable'):
                    continue
                formats.append(self._extract_format_for_quality(
                    api_data, video_id, audio_quality, video_quality))

        # Get flv/swf info
        timestamp = None
        video_real_url = try_get(api_data, lambda x: x['video']['smileInfo']['url'])
        if not video_real_url:
            self.report_warning('Unable to obtain smile video information')
        else:
            is_economy = video_real_url.endswith('low')

            if is_economy:
                self.report_warning('Site is currently in economy mode! You will only have access to lower quality streams')

            # Invoking ffprobe to determine resolution
            pp = FFmpegPostProcessor(self._downloader)
            cookies = self._get_cookies('https://nicovideo.jp').output(header='', sep='; path=/; domain=nicovideo.jp;\n')

            self.to_screen('%s: %s' % (video_id, 'Checking smile format with ffprobe'))

            try:
                metadata = pp.get_metadata_object(video_real_url, ['-cookies', cookies])
            except PostProcessingError as err:
                raise ExtractorError(err.msg, expected=True)

            v_stream = a_stream = {}

            # Some complex swf files doesn't have video stream (e.g. nm4809023)
            for stream in metadata['streams']:
                if stream['codec_type'] == 'video':
                    v_stream = stream
                elif stream['codec_type'] == 'audio':
                    a_stream = stream

            # Community restricted videos seem to have issues with the thumb API not returning anything at all
            filesize = int(
                (get_video_info_xml('size_high') if not is_economy else get_video_info_xml('size_low'))
                or metadata['format']['size']
            )
            extension = (
                get_video_info_xml('movie_type')
                or 'mp4' if 'mp4' in metadata['format']['format_name'] else metadata['format']['format_name']
            )

            # 'creation_time' tag on video stream of re-encoded SMILEVIDEO mp4 files are '1970-01-01T00:00:00.000000Z'.
            timestamp = (
                parse_iso8601(get_video_info_web('first_retrieve'))
                or unified_timestamp(get_video_info_web('postedDateTime'))
            )
            metadata_timestamp = (
                parse_iso8601(try_get(v_stream, lambda x: x['tags']['creation_time']))
                or timestamp if extension != 'mp4' else 0
            )

            # According to compconf, smile videos from pre-2017 are always better quality than their DMC counterparts
            smile_threshold_timestamp = parse_iso8601('2016-12-08T00:00:00+09:00')

            is_source = timestamp < smile_threshold_timestamp or metadata_timestamp > 0

            # If movie file size is unstable, old server movie is not source movie.
            if filesize > 1:
                formats.append({
                    'url': video_real_url,
                    'format_id': 'smile' if not is_economy else 'smile_low',
                    'format_note': 'SMILEVIDEO source' if not is_economy else 'SMILEVIDEO low quality',
                    'ext': extension,
                    'container': extension,
                    'vcodec': v_stream.get('codec_name'),
                    'acodec': a_stream.get('codec_name'),
                    # Some complex swf files doesn't have total bit rate metadata (e.g. nm6049209)
                    'tbr': int_or_none(metadata['format'].get('bit_rate'), scale=1000),
                    'vbr': int_or_none(v_stream.get('bit_rate'), scale=1000),
                    'abr': int_or_none(a_stream.get('bit_rate'), scale=1000),
                    'height': int_or_none(v_stream.get('height')),
                    'width': int_or_none(v_stream.get('width')),
                    'source_preference': 5 if not is_economy else -2,
                    'quality': 5 if is_source and not is_economy else None,
                    'filesize': filesize
                })

        if len(formats) == 0:
            raise ExtractorError('Unable to find video info.')

        self._sort_formats(formats)

        # Start extracting information
        title = (
            get_video_info_web(['originalTitle', 'title'])
            or self._og_search_title(webpage, default=None)
            or self._html_search_regex(
                r'<span[^>]+class="videoHeaderTitle"[^>]*>([^<]+)</span>',
                webpage, 'video title'))

        watch_api_data_string = self._html_search_regex(
            r'<div[^>]+id="watchAPIDataContainer"[^>]+>([^<]+)</div>',
            webpage, 'watch api data', default=None)
        watch_api_data = self._parse_json(watch_api_data_string, video_id) if watch_api_data_string else {}
        video_detail = watch_api_data.get('videoDetail', {})

        thumbnail = (
            self._html_search_regex(r'<meta property="og:image" content="([^"]+)">', webpage, 'thumbnail data', default=None)
            or get_video_info_web(['thumbnail_url', 'largeThumbnailURL', 'thumbnailURL'])
            or self._html_search_meta('image', webpage, 'thumbnail', default=None)
            or video_detail.get('thumbnail'))

        description = get_video_info_web('description')

        if not timestamp:
            match = self._html_search_meta('datePublished', webpage, 'date published', default=None)
            if match:
                timestamp = parse_iso8601(match.replace('+', ':00+'))
        if not timestamp and video_detail.get('postedAt'):
            timestamp = parse_iso8601(
                video_detail['postedAt'].replace('/', '-'),
                delimiter=' ', timezone=datetime.timedelta(hours=9))
        timestamp = timestamp or try_get(api_data, lambda x: parse_iso8601(x['video']['registeredAt']))

        view_count = int_or_none(get_video_info_web(['view_counter', 'viewCount']))
        if not view_count:
            match = self._html_search_regex(
                r'>Views: <strong[^>]*>([^<]+)</strong>',
                webpage, 'view count', default=None)
            if match:
                view_count = int_or_none(match.replace(',', ''))
        view_count = (
            view_count
            or video_detail.get('viewCount')
            or try_get(api_data, lambda x: x['video']['count']['view']))

        comment_count = (
            int_or_none(get_video_info_web('comment_num'))
            or video_detail.get('commentCount')
            or try_get(api_data, lambda x: x['video']['count']['comment']))

        if not comment_count:
            match = self._html_search_regex(
                r'>Comments: <strong[^>]*>([^<]+)</strong>',
                webpage, 'comment count', default=None)
            if match:
                comment_count = int_or_none(match.replace(',', ''))

        duration = (parse_duration(
            get_video_info_web('length')
            or self._html_search_meta(
                'video:duration', webpage, 'video duration', default=None))
            or video_detail.get('length')
            or get_video_info_web('duration'))

        webpage_url = get_video_info_web('watch_url') or url

        # for channel movie and community movie
        channel_id = try_get(
            api_data,
            (lambda x: x['channel']['globalId'],
             lambda x: x['community']['globalId']))
        channel = try_get(
            api_data,
            (lambda x: x['channel']['name'],
             lambda x: x['community']['name']))

        # Note: cannot use api_data.get('owner', {}) because owner may be set to "null"
        # in the JSON, which will cause None to be returned instead of {}.
        owner = try_get(api_data, lambda x: x.get('owner'), dict) or {}
        uploader_id = str_or_none(
            get_video_info_web(['ch_id', 'user_id'])
            or owner.get('id')
            or channel_id
        )
        uploader = (
            get_video_info_web(['ch_name', 'user_nickname'])
            or owner.get('nickname')
            or channel
        )

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': thumbnail,
            'description': description,
            'uploader': uploader,
            'timestamp': timestamp,
            'uploader_id': uploader_id,
            'channel': channel,
            'channel_id': channel_id,
            'view_count': view_count,
            'comment_count': comment_count,
            'duration': duration,
            'webpage_url': webpage_url,
        }


class NiconicoPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?nicovideo\.jp/(?:user/\d+/|my/)?mylist/(?P<id>\d+)'

    _TESTS = [{
        'url': 'http://www.nicovideo.jp/mylist/27411728',
        'info_dict': {
            'id': '27411728',
            'title': 'AKB48のオールナイトニッポン',
            'description': 'md5:d89694c5ded4b6c693dea2db6e41aa08',
            'uploader': 'のっく',
            'uploader_id': '805442',
        },
        'playlist_mincount': 225,
    }, {
        'url': 'https://www.nicovideo.jp/user/805442/mylist/27411728',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        list_id = self._match_id(url)
        webpage = self._download_webpage(url, list_id)

        header = self._parse_json(self._html_search_regex(
            r'data-common-header="([^"]+)"', webpage,
            'webpage header'), list_id)
        frontendId = header.get('initConfig').get('frontendId')
        frontendVersion = header.get('initConfig').get('frontendVersion')

        def get_page_data(pagenum, pagesize):
            return self._download_json(
                'http://nvapi.nicovideo.jp/v2/mylists/' + list_id, list_id,
                query={'page': 1 + pagenum, 'pageSize': pagesize},
                headers={
                    'X-Frontend-Id': frontendId,
                    'X-Frontend-Version': frontendVersion,
                }).get('data').get('mylist')

        data = get_page_data(0, 1)
        title = data.get('name')
        description = data.get('description')
        uploader = data.get('owner').get('name')
        uploader_id = data.get('owner').get('id')

        def pagefunc(pagenum):
            data = get_page_data(pagenum, 25)
            return ({
                '_type': 'url',
                'url': 'http://www.nicovideo.jp/watch/' + item.get('watchId'),
            } for item in data.get('items'))

        return {
            '_type': 'playlist',
            'id': list_id,
            'title': title,
            'description': description,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'entries': OnDemandPagedList(pagefunc, 25),
        }


class NiconicoUserIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?nicovideo\.jp/user/(?P<id>\d+)/?(?:$|[#?])'
    _TEST = {
        'url': 'https://www.nicovideo.jp/user/419948',
        'info_dict': {
            'id': '419948',
        },
        'playlist_mincount': 101,
    }
    _API_URL = "https://nvapi.nicovideo.jp/v1/users/%s/videos?sortKey=registeredAt&sortOrder=desc&pageSize=%s&page=%s"
    _api_headers = {
        'X-Frontend-ID': '6',
        'X-Frontend-Version': '0',
        'X-Niconico-Language': 'en-us'
    }
    _PAGE_SIZE = 100

    def _entries(self, list_id, ):
        total_count = 1
        count = page_num = 0
        while count < total_count:
            json_parsed = self._download_json(
                self._API_URL % (list_id, self._PAGE_SIZE, page_num + 1), list_id,
                headers=self._api_headers,
                note='Downloading JSON metadata%s' % (' page %d' % page_num if page_num else ''))
            if not page_num:
                total_count = int_or_none(json_parsed['data'].get('totalCount'))
            for entry in json_parsed["data"]["items"]:
                count += 1
                yield self.url_result('https://www.nicovideo.jp/watch/%s' % entry['id'])
            page_num += 1

    def _real_extract(self, url):
        list_id = self._match_id(url)
        return self.playlist_result(self._entries(list_id), list_id, ie=NiconicoIE.ie_key())
