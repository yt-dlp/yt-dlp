# coding: utf-8
from __future__ import unicode_literals

import datetime
import functools
import json
import math

from .common import InfoExtractor
from ..compat import (
    compat_parse_qs,
    compat_urllib_parse_urlparse,
)
from ..utils import (
    determine_ext,
    dict_get,
    ExtractorError,
    float_or_none,
    InAdvancePagedList,
    int_or_none,
    parse_duration,
    parse_iso8601,
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
        'md5': 'd1a75c0823e2f629128c43e1212760f9',
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
            self._downloader.report_warning('unable to log in: bad username or password')
        return login_ok

    def _extract_format_for_quality(self, api_data, video_id, audio_quality, video_quality):
        def yesno(boolean):
            return 'yes' if boolean else 'no'

        session_api_data = api_data['video']['dmcInfo']['session_api']
        session_api_endpoint = session_api_data['urls'][0]

        format_id = '-'.join(map(lambda s: remove_start(s['id'], 'archive_'), [video_quality, audio_quality]))

        session_response = self._download_json(
            session_api_endpoint['url'], video_id,
            query={'_format': 'json'},
            headers={'Content-Type': 'application/json'},
            note='Downloading JSON metadata for %s' % format_id,
            data=json.dumps({
                'session': {
                    'client_info': {
                        'player_id': session_api_data['player_id'],
                    },
                    'content_auth': {
                        'auth_type': session_api_data['auth_types'][session_api_data['protocols'][0]],
                        'content_key_timeout': session_api_data['content_key_timeout'],
                        'service_id': 'nicovideo',
                        'service_user_id': session_api_data['service_user_id']
                    },
                    'content_id': session_api_data['content_id'],
                    'content_src_id_sets': [{
                        'content_src_ids': [{
                            'src_id_to_mux': {
                                'audio_src_ids': [audio_quality['id']],
                                'video_src_ids': [video_quality['id']],
                            }
                        }]
                    }],
                    'content_type': 'movie',
                    'content_uri': '',
                    'keep_method': {
                        'heartbeat': {
                            'lifetime': session_api_data['heartbeat_lifetime']
                        }
                    },
                    'priority': session_api_data['priority'],
                    'protocol': {
                        'name': 'http',
                        'parameters': {
                            'http_parameters': {
                                'parameters': {
                                    'http_output_download_parameters': {
                                        'use_ssl': yesno(session_api_endpoint['is_ssl']),
                                        'use_well_known_port': yesno(session_api_endpoint['is_well_known_port']),
                                    }
                                }
                            }
                        }
                    },
                    'recipe_id': session_api_data['recipe_id'],
                    'session_operation_auth': {
                        'session_operation_auth_by_signature': {
                            'signature': session_api_data['signature'],
                            'token': session_api_data['token'],
                        }
                    },
                    'timing_constraint': 'unlimited'
                }
            }).encode())

        resolution = video_quality.get('resolution', {})

        return {
            'url': session_response['data']['session']['content_uri'],
            'format_id': format_id,
            'ext': 'mp4',  # Session API are used in HTML5, which always serves mp4
            'abr': float_or_none(audio_quality.get('bitrate'), 1000),
            'vbr': float_or_none(video_quality.get('bitrate'), 1000),
            'height': resolution.get('height'),
            'width': resolution.get('width'),
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        # Get video webpage. We are not actually interested in it for normal
        # cases, but need the cookies in order to be able to download the
        # info webpage
        webpage, handle = self._download_webpage_handle(
            'http://www.nicovideo.jp/watch/' + video_id, video_id)
        if video_id.startswith('so'):
            video_id = self._match_id(handle.geturl())

        api_data = self._parse_json(self._html_search_regex(
            'data-api-data="([^"]+)"', webpage,
            'API data', default='{}'), video_id)

        def _format_id_from_url(video_url):
            return 'economy' if video_real_url.endswith('low') else 'normal'

        try:
            video_real_url = api_data['video']['smileInfo']['url']
        except KeyError:  # Flash videos
            # Get flv info
            flv_info_webpage = self._download_webpage(
                'http://flapi.nicovideo.jp/api/getflv/' + video_id + '?as3=1',
                video_id, 'Downloading flv info')

            flv_info = compat_parse_qs(flv_info_webpage)
            if 'url' not in flv_info:
                if 'deleted' in flv_info:
                    raise ExtractorError('The video has been deleted.',
                                         expected=True)
                elif 'closed' in flv_info:
                    raise ExtractorError('Niconico videos now require logging in',
                                         expected=True)
                elif 'error' in flv_info:
                    raise ExtractorError('%s reports error: %s' % (
                        self.IE_NAME, flv_info['error'][0]), expected=True)
                else:
                    raise ExtractorError('Unable to find video URL')

            video_info_xml = self._download_xml(
                'http://ext.nicovideo.jp/api/getthumbinfo/' + video_id,
                video_id, note='Downloading video info page')

            def get_video_info(items):
                if not isinstance(items, list):
                    items = [items]
                for item in items:
                    ret = xpath_text(video_info_xml, './/' + item)
                    if ret:
                        return ret

            video_real_url = flv_info['url'][0]

            extension = get_video_info('movie_type')
            if not extension:
                extension = determine_ext(video_real_url)

            formats = [{
                'url': video_real_url,
                'ext': extension,
                'format_id': _format_id_from_url(video_real_url),
            }]
        else:
            formats = []

            dmc_info = api_data['video'].get('dmcInfo')
            if dmc_info:  # "New" HTML5 videos
                quality_info = dmc_info['quality']
                for audio_quality in quality_info['audios']:
                    for video_quality in quality_info['videos']:
                        if not audio_quality['available'] or not video_quality['available']:
                            continue
                        formats.append(self._extract_format_for_quality(
                            api_data, video_id, audio_quality, video_quality))

                self._sort_formats(formats)
            else:  # "Old" HTML5 videos
                formats = [{
                    'url': video_real_url,
                    'ext': 'mp4',
                    'format_id': _format_id_from_url(video_real_url),
                }]

            def get_video_info(items):
                return dict_get(api_data['video'], items)

        # Start extracting information
        title = get_video_info('title')
        if not title:
            title = self._og_search_title(webpage, default=None)
        if not title:
            title = self._html_search_regex(
                r'<span[^>]+class="videoHeaderTitle"[^>]*>([^<]+)</span>',
                webpage, 'video title')

        watch_api_data_string = self._html_search_regex(
            r'<div[^>]+id="watchAPIDataContainer"[^>]+>([^<]+)</div>',
            webpage, 'watch api data', default=None)
        watch_api_data = self._parse_json(watch_api_data_string, video_id) if watch_api_data_string else {}
        video_detail = watch_api_data.get('videoDetail', {})

        thumbnail = (
            get_video_info(['thumbnail_url', 'thumbnailURL'])
            or self._html_search_meta('image', webpage, 'thumbnail', default=None)
            or video_detail.get('thumbnail'))

        description = get_video_info('description')

        timestamp = (parse_iso8601(get_video_info('first_retrieve'))
                     or unified_timestamp(get_video_info('postedDateTime')))
        if not timestamp:
            match = self._html_search_meta('datePublished', webpage, 'date published', default=None)
            if match:
                timestamp = parse_iso8601(match.replace('+', ':00+'))
        if not timestamp and video_detail.get('postedAt'):
            timestamp = parse_iso8601(
                video_detail['postedAt'].replace('/', '-'),
                delimiter=' ', timezone=datetime.timedelta(hours=9))

        view_count = int_or_none(get_video_info(['view_counter', 'viewCount']))
        if not view_count:
            match = self._html_search_regex(
                r'>Views: <strong[^>]*>([^<]+)</strong>',
                webpage, 'view count', default=None)
            if match:
                view_count = int_or_none(match.replace(',', ''))
        view_count = view_count or video_detail.get('viewCount')

        comment_count = (int_or_none(get_video_info('comment_num'))
                         or video_detail.get('commentCount')
                         or try_get(api_data, lambda x: x['thread']['commentCount']))
        if not comment_count:
            match = self._html_search_regex(
                r'>Comments: <strong[^>]*>([^<]+)</strong>',
                webpage, 'comment count', default=None)
            if match:
                comment_count = int_or_none(match.replace(',', ''))

        duration = (parse_duration(
            get_video_info('length')
            or self._html_search_meta(
                'video:duration', webpage, 'video duration', default=None))
            or video_detail.get('length')
            or get_video_info('duration'))

        webpage_url = get_video_info('watch_url') or url

        # Note: cannot use api_data.get('owner', {}) because owner may be set to "null"
        # in the JSON, which will cause None to be returned instead of {}.
        owner = try_get(api_data, lambda x: x.get('owner'), dict) or {}
        uploader_id = get_video_info(['ch_id', 'user_id']) or owner.get('id')
        uploader = get_video_info(['ch_name', 'user_nickname']) or owner.get('nickname')

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': thumbnail,
            'description': description,
            'uploader': uploader,
            'timestamp': timestamp,
            'uploader_id': uploader_id,
            'view_count': view_count,
            'comment_count': comment_count,
            'duration': duration,
            'webpage_url': webpage_url,
        }


class NiconicoPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?nicovideo\.jp/(?:user/\d+/)?mylist/(?P<id>\d+)'

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
    _PAGE_SIZE = 100

    def _call_api(self, list_id, resource, query):
        return self._download_json(
            'https://nvapi.nicovideo.jp/v2/mylists/' + list_id, list_id,
            'Downloading %s JSON metatdata' % resource, query=query,
            headers={'X-Frontend-Id': 6})['data']['mylist']

    def _parse_owner(self, item):
        owner = item.get('owner') or {}
        if owner:
            return {
                'uploader': owner.get('name'),
                'uploader_id': owner.get('id'),
            }
        return {}

    def _fetch_page(self, list_id, page):
        page += 1
        items = self._call_api(list_id, 'page %d' % page, {
            'page': page,
            'pageSize': self._PAGE_SIZE,
        })['items']
        for item in items:
            video = item.get('video') or {}
            video_id = video.get('id')
            if not video_id:
                continue
            count = video.get('count') or {}
            get_count = lambda x: int_or_none(count.get(x))
            info = {
                '_type': 'url',
                'id': video_id,
                'title': video.get('title'),
                'url': 'https://www.nicovideo.jp/watch/' + video_id,
                'description': video.get('shortDescription'),
                'duration': int_or_none(video.get('duration')),
                'view_count': get_count('view'),
                'comment_count': get_count('comment'),
                'ie_key': NiconicoIE.ie_key(),
            }
            info.update(self._parse_owner(video))
            yield info

    def _real_extract(self, url):
        list_id = self._match_id(url)
        mylist = self._call_api(list_id, 'list', {
            'pageSize': 1,
        })
        entries = InAdvancePagedList(
            functools.partial(self._fetch_page, list_id),
            math.ceil(mylist['totalItemCount'] / self._PAGE_SIZE),
            self._PAGE_SIZE)
        result = self.playlist_result(
            entries, list_id, mylist.get('name'), mylist.get('description'))
        result.update(self._parse_owner(mylist))
        return result
