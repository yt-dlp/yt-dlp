import base64
import hashlib
import hmac
import itertools
import json
import re
import time
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    dict_get,
    int_or_none,
    join_nonempty,
    merge_dicts,
    parse_iso8601,
    traverse_obj,
    try_get,
    unified_timestamp,
    update_url_query,
    url_or_none,
)


class NaverBaseIE(InfoExtractor):
    _CAPTION_EXT_RE = r'\.(?:ttml|vtt)'

    @staticmethod  # NB: Used in WeverseIE
    def process_subtitles(vod_data, process_url):
        ret = {'subtitles': {}, 'automatic_captions': {}}
        for caption in traverse_obj(vod_data, ('captions', 'list', ...)):
            caption_url = caption.get('source')
            if not caption_url:
                continue
            type_ = 'automatic_captions' if caption.get('type') == 'auto' else 'subtitles'
            lang = caption.get('locale') or join_nonempty('language', 'country', from_dict=caption) or 'und'
            if caption.get('type') == 'fan':
                lang += '_fan%d' % next(i for i in itertools.count(1) if f'{lang}_fan{i}' not in ret[type_])
            ret[type_].setdefault(lang, []).extend({
                'url': sub_url,
                'name': join_nonempty('label', 'fanName', from_dict=caption, delim=' - '),
            } for sub_url in process_url(caption_url))
        return ret

    def _extract_video_info(self, video_id, vid, key):
        video_data = self._download_json(
            'http://play.rmcnmv.naver.com/vod/play/v2.0/' + vid,
            video_id, query={
                'key': key,
            })
        meta = video_data['meta']
        title = meta['subject']
        formats = []
        get_list = lambda x: try_get(video_data, lambda y: y[x + 's']['list'], list) or []

        def extract_formats(streams, stream_type, query={}):
            for stream in streams:
                stream_url = stream.get('source')
                if not stream_url:
                    continue
                stream_url = update_url_query(stream_url, query)
                encoding_option = stream.get('encodingOption', {})
                bitrate = stream.get('bitrate', {})
                formats.append({
                    'format_id': '%s_%s' % (stream.get('type') or stream_type, dict_get(encoding_option, ('name', 'id'))),
                    'url': stream_url,
                    'ext': 'mp4',
                    'width': int_or_none(encoding_option.get('width')),
                    'height': int_or_none(encoding_option.get('height')),
                    'vbr': int_or_none(bitrate.get('video')),
                    'abr': int_or_none(bitrate.get('audio')),
                    'filesize': int_or_none(stream.get('size')),
                    'protocol': 'm3u8_native' if stream_type == 'HLS' else None,
                })

        extract_formats(get_list('video'), 'H264')
        for stream_set in video_data.get('streams', []):
            query = {}
            for param in stream_set.get('keys', []):
                query[param['name']] = param['value']
            stream_type = stream_set.get('type')
            videos = stream_set.get('videos')
            if videos:
                extract_formats(videos, stream_type, query)
            elif stream_type == 'HLS':
                stream_url = stream_set.get('source')
                if not stream_url:
                    continue
                formats.extend(self._extract_m3u8_formats(
                    update_url_query(stream_url, query), video_id,
                    'mp4', 'm3u8_native', m3u8_id=stream_type, fatal=False))

        replace_ext = lambda x, y: re.sub(self._CAPTION_EXT_RE, '.' + y, x)

        def get_subs(caption_url):
            if re.search(self._CAPTION_EXT_RE, caption_url):
                return [
                    replace_ext(caption_url, 'ttml'),
                    replace_ext(caption_url, 'vtt'),
                ]
            return [caption_url]

        user = meta.get('user', {})

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': try_get(meta, lambda x: x['cover']['source']),
            'view_count': int_or_none(meta.get('count')),
            'uploader_id': user.get('id'),
            'uploader': user.get('name'),
            'uploader_url': user.get('url'),
            **self.process_subtitles(video_data, get_subs),
        }

    def _call_api(self, path, video_id):
        api_endpoint = f'https://apis.naver.com/now_web2/now_web_api/v1{path}'
        key = b'nbxvs5nwNG9QKEWK0ADjYA4JZoujF4gHcIwvoCxFTPAeamq5eemvt5IWAYXxrbYM'
        msgpad = int(time.time() * 1000)
        md = base64.b64encode(hmac.HMAC(
            key, f'{api_endpoint[:255]}{msgpad}'.encode(), digestmod=hashlib.sha1).digest()).decode()

        return self._download_json(api_endpoint, video_id=video_id, headers=self.geo_verification_headers(), query={
            'msgpad': msgpad,
            'md': md,
        })['result']


class NaverIE(NaverBaseIE):
    _VALID_URL = r'https?://(?:m\.)?tv(?:cast)?\.naver\.com/(?:v|embed)/(?P<id>\d+)'
    _GEO_BYPASS = False
    _TESTS = [{
        'url': 'http://tv.naver.com/v/81652',
        'info_dict': {
            'id': '81652',
            'ext': 'mp4',
            'title': '[9월 모의고사 해설강의][수학_김상희] 수학 A형 16~20번',
            'description': '메가스터디 수학 김상희 선생님이 9월 모의고사 수학A형 16번에서 20번까지 해설강의를 공개합니다.',
            'timestamp': 1378200754,
            'upload_date': '20130903',
            'uploader': '메가스터디, 합격불변의 법칙',
            'uploader_id': 'megastudy',
            'uploader_url': 'https://tv.naver.com/megastudy',
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'duration': 2118,
            'thumbnail': r're:^https?://.*\.jpg',
        },
    }, {
        'url': 'http://tv.naver.com/v/395837',
        'md5': '7791205fa89dbed2f5e3eb16d287ff05',
        'info_dict': {
            'id': '395837',
            'ext': 'mp4',
            'title': '9년이 지나도 아픈 기억, 전효성의 아버지',
            'description': 'md5:c76be23e21403a6473d8119678cdb5cb',
            'timestamp': 1432030253,
            'upload_date': '20150519',
            'uploader': '4가지쇼',
            'uploader_id': '4show',
            'uploader_url': 'https://tv.naver.com/4show',
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'duration': 277,
            'thumbnail': r're:^https?://.*\.jpg',
        },
    }, {
        'url': 'http://tvcast.naver.com/v/81652',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._call_api(f'/clips/{video_id}/play-info', video_id)

        vid = traverse_obj(data, ('clip', 'videoId', {str}))
        in_key = traverse_obj(data, ('play', 'inKey', {str}))

        if not vid or not in_key:
            raise ExtractorError('Unable to extract video info')

        info = self._extract_video_info(video_id, vid, in_key)
        info.update(traverse_obj(data, ('clip', {
            'title': 'title',
            'description': 'description',
            'timestamp': ('firstExposureDatetime', {parse_iso8601}),
            'duration': ('playTime', {int_or_none}),
            'like_count': ('likeItCount', {int_or_none}),
            'view_count': ('playCount', {int_or_none}),
            'comment_count': ('commentCount', {int_or_none}),
            'thumbnail': ('thumbnailImageUrl', {url_or_none}),
            'uploader': 'channelName',
            'uploader_id': 'channelId',
            'uploader_url': ('channelUrl', {url_or_none}),
            'age_limit': ('adultVideo', {lambda x: 19 if x else None}),
        })))
        return info


class NaverLiveIE(NaverBaseIE):
    IE_NAME = 'Naver:live'
    _VALID_URL = r'https?://(?:m\.)?tv(?:cast)?\.naver\.com/l/(?P<id>\d+)'
    _GEO_BYPASS = False
    _TESTS = [{
        'url': 'https://tv.naver.com/l/127062',
        'info_dict': {
            'id': '127062',
            'ext': 'mp4',
            'live_status': 'is_live',
            'channel': '뉴스는 YTN',
            'channel_id': 'ytnnews24',
            'title': 're:^대한민국 24시간 뉴스 채널 [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'description': 'md5:f938b5956711beab6f882314ffadf4d5',
            'start_time': 1677752280,
            'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)',
            'like_count': int,
        },
    }, {
        'url': 'https://tv.naver.com/l/140535',
        'info_dict': {
            'id': '140535',
            'ext': 'mp4',
            'live_status': 'is_live',
            'channel': 'KBS뉴스',
            'channel_id': 'kbsnews',
            'start_time': 1696867320,
            'title': 're:^언제 어디서나! KBS 뉴스 24 [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'description': 'md5:6ad419c0bf2f332829bda3f79c295284',
            'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)',
            'like_count': int,
        },
    }, {
        'url': 'https://tv.naver.com/l/54887',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._call_api(f'/live-end/normal/{video_id}/play-info?renewLastPlayDate=true', video_id)

        status = traverse_obj(data, ('live', 'liveStatus'))
        if status == 'CLOSED':
            raise ExtractorError('Stream is offline.', expected=True)
        elif status != 'OPENED':
            raise ExtractorError(f'Unknown status {status!r}')

        return {
            'id': video_id,
            'formats': self._extract_m3u8_formats(
                traverse_obj(data, ('playbackBody', {json.loads}, 'media', 0, 'path')), video_id, live=True),
            **traverse_obj(data, ('live', {
                'title': 'title',
                'channel': 'channelName',
                'channel_id': 'channelId',
                'description': 'description',
                'like_count': (('likeCount', 'likeItCount'), {int_or_none}),
                'thumbnail': ('thumbnailImageUrl', {url_or_none}),
                'start_time': (('startTime', 'startDateTime', 'startYmdt'), {parse_iso8601}),
            }), get_all=False),
            'is_live': True
        }


class NaverNowIE(NaverBaseIE):
    IE_NAME = 'navernow'
    _VALID_URL = r'https?://now\.naver\.com/s/now\.(?P<id>\w+)'
    _API_URL = 'https://apis.naver.com/now_web/oldnow_web/v4'
    _TESTS = [{
        'url': 'https://now.naver.com/s/now.4759?shareReplayId=26331132#replay=',
        'md5': 'e05854162c21c221481de16b2944a0bc',
        'info_dict': {
            'id': '4759-26331132',
            'title': '아이키X노제\r\n💖꽁냥꽁냥💖(1)',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.*\.jpg',
            'timestamp': 1650369600,
            'upload_date': '20220419',
            'uploader_id': 'now',
            'view_count': int,
            'uploader_url': 'https://now.naver.com/show/4759',
            'uploader': '아이키의 떰즈업',
        },
        'params': {
            'noplaylist': True,
        }
    }, {
        'url': 'https://now.naver.com/s/now.4759?shareHightlight=26601461#highlight=',
        'md5': '9f6118e398aa0f22b2152f554ea7851b',
        'info_dict': {
            'id': '4759-26601461',
            'title': '아이키: 나 리정한테 흔들렸어,,, 질투 폭발하는 노제 여보😾 [아이키의 떰즈업]ㅣ네이버 NOW.',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.*\.jpg',
            'upload_date': '20220504',
            'timestamp': 1651648311,
            'uploader_id': 'now',
            'view_count': int,
            'uploader_url': 'https://now.naver.com/show/4759',
            'uploader': '아이키의 떰즈업',
        },
        'params': {
            'noplaylist': True,
        },
    }, {
        'url': 'https://now.naver.com/s/now.4759',
        'info_dict': {
            'id': '4759',
            'title': '아이키의 떰즈업',
        },
        'playlist_mincount': 101
    }, {
        'url': 'https://now.naver.com/s/now.4759?shareReplayId=26331132#replay',
        'info_dict': {
            'id': '4759',
            'title': '아이키의 떰즈업',
        },
        'playlist_mincount': 101,
    }, {
        'url': 'https://now.naver.com/s/now.4759?shareHightlight=26601461#highlight=',
        'info_dict': {
            'id': '4759',
            'title': '아이키의 떰즈업',
        },
        'playlist_mincount': 101,
    }, {
        'url': 'https://now.naver.com/s/now.kihyunplay?shareReplayId=30573291#replay',
        'only_matching': True,
    }]

    def _extract_replay(self, show_id, replay_id):
        vod_info = self._download_json(f'{self._API_URL}/shows/now.{show_id}/vod/{replay_id}', replay_id)
        in_key = self._download_json(f'{self._API_URL}/shows/now.{show_id}/vod/{replay_id}/inkey', replay_id)['inKey']
        return merge_dicts({
            'id': f'{show_id}-{replay_id}',
            'title': traverse_obj(vod_info, ('episode', 'title')),
            'timestamp': unified_timestamp(traverse_obj(vod_info, ('episode', 'start_time'))),
            'thumbnail': vod_info.get('thumbnail_image_url'),
        }, self._extract_video_info(replay_id, vod_info['video_id'], in_key))

    def _extract_show_replays(self, show_id):
        page_size = 15
        page = 1
        while True:
            show_vod_info = self._download_json(
                f'{self._API_URL}/vod-shows/now.{show_id}', show_id,
                query={'page': page, 'page_size': page_size},
                note=f'Downloading JSON vod list for show {show_id} - page {page}'
            )['response']['result']
            for v in show_vod_info.get('vod_list') or []:
                yield self._extract_replay(show_id, v['id'])

            if len(show_vod_info.get('vod_list') or []) < page_size:
                break
            page += 1

    def _extract_show_highlights(self, show_id, highlight_id=None):
        page_size = 10
        page = 1
        while True:
            highlights_videos = self._download_json(
                f'{self._API_URL}/shows/now.{show_id}/highlights/videos/', show_id,
                query={'page': page, 'page_size': page_size},
                note=f'Downloading JSON highlights for show {show_id} - page {page}')

            for highlight in highlights_videos.get('results') or []:
                if highlight_id and highlight.get('clip_no') != int(highlight_id):
                    continue
                yield merge_dicts({
                    'id': f'{show_id}-{highlight["clip_no"]}',
                    'title': highlight.get('title'),
                    'timestamp': unified_timestamp(highlight.get('regdate')),
                    'thumbnail': highlight.get('thumbnail_url'),
                }, self._extract_video_info(highlight['clip_no'], highlight['video_id'], highlight['video_inkey']))

            if len(highlights_videos.get('results') or []) < page_size:
                break
            page += 1

    def _extract_highlight(self, show_id, highlight_id):
        try:
            return next(self._extract_show_highlights(show_id, highlight_id))
        except StopIteration:
            raise ExtractorError(f'Unable to find highlight {highlight_id} for show {show_id}')

    def _real_extract(self, url):
        show_id = self._match_id(url)
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)

        if not self._yes_playlist(show_id, qs.get('shareHightlight')):
            return self._extract_highlight(show_id, qs['shareHightlight'][0])
        elif not self._yes_playlist(show_id, qs.get('shareReplayId')):
            return self._extract_replay(show_id, qs['shareReplayId'][0])

        show_info = self._download_json(
            f'{self._API_URL}/shows/now.{show_id}/', show_id,
            note=f'Downloading JSON vod list for show {show_id}')

        return self.playlist_result(
            itertools.chain(self._extract_show_replays(show_id), self._extract_show_highlights(show_id)),
            show_id, show_info.get('title'))
