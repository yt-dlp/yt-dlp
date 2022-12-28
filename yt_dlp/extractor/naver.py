import itertools
import re
from urllib.parse import urlparse, parse_qs

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    dict_get,
    int_or_none,
    join_nonempty,
    merge_dicts,
    parse_duration,
    traverse_obj,
    try_get,
    unified_timestamp,
    update_url_query,
)


class NaverBaseIE(InfoExtractor):
    _CAPTION_EXT_RE = r'\.(?:ttml|vtt)'

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

        automatic_captions = {}
        subtitles = {}
        for caption in get_list('caption'):
            caption_url = caption.get('source')
            if not caption_url:
                continue
            sub_dict = automatic_captions if caption.get('type') == 'auto' else subtitles
            lang = caption.get('locale') or join_nonempty('language', 'country', from_dict=caption) or 'und'
            if caption.get('type') == 'fan':
                lang += '_fan%d' % next(i for i in itertools.count(1) if f'{lang}_fan{i}' not in sub_dict)
            sub_dict.setdefault(lang, []).extend({
                'url': sub_url,
                'name': join_nonempty('label', 'fanName', from_dict=caption, delim=' - '),
            } for sub_url in get_subs(caption_url))

        user = meta.get('user', {})

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'subtitles': subtitles,
            'automatic_captions': automatic_captions,
            'thumbnail': try_get(meta, lambda x: x['cover']['source']),
            'view_count': int_or_none(meta.get('count')),
            'uploader_id': user.get('id'),
            'uploader': user.get('name'),
            'uploader_url': user.get('url'),
        }


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
        },
    }, {
        'url': 'http://tv.naver.com/v/395837',
        'md5': '8a38e35354d26a17f73f4e90094febd3',
        'info_dict': {
            'id': '395837',
            'ext': 'mp4',
            'title': '9년이 지나도 아픈 기억, 전효성의 아버지',
            'description': 'md5:eb6aca9d457b922e43860a2a2b1984d3',
            'timestamp': 1432030253,
            'upload_date': '20150519',
            'uploader': '4가지쇼 시즌2',
            'uploader_id': 'wrappinguser29',
        },
        'skip': 'Georestricted',
    }, {
        'url': 'http://tvcast.naver.com/v/81652',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        content = self._download_json(
            'https://tv.naver.com/api/json/v/' + video_id,
            video_id, headers=self.geo_verification_headers())
        player_info_json = content.get('playerInfoJson') or {}
        current_clip = player_info_json.get('currentClip') or {}

        vid = current_clip.get('videoId')
        in_key = current_clip.get('inKey')

        if not vid or not in_key:
            player_auth = try_get(player_info_json, lambda x: x['playerOption']['auth'])
            if player_auth == 'notCountry':
                self.raise_geo_restricted(countries=['KR'])
            elif player_auth == 'notLogin':
                self.raise_login_required()
            raise ExtractorError('couldn\'t extract vid and key')
        info = self._extract_video_info(video_id, vid, in_key)
        info.update({
            'description': clean_html(current_clip.get('description')),
            'timestamp': int_or_none(current_clip.get('firstExposureTime'), 1000),
            'duration': parse_duration(current_clip.get('displayPlayTime')),
            'like_count': int_or_none(current_clip.get('recommendPoint')),
            'age_limit': 19 if current_clip.get('adult') else None,
        })
        return info


class NaverLiveIE(InfoExtractor):
    IE_NAME = 'Naver:live'
    _VALID_URL = r'https?://(?:m\.)?tv(?:cast)?\.naver\.com/l/(?P<id>\d+)'
    _GEO_BYPASS = False
    _TESTS = [{
        'url': 'https://tv.naver.com/l/52010',
        'info_dict': {
            'id': '52010',
            'ext': 'mp4',
            'title': '[LIVE] 뉴스특보 : "수도권 거리두기, 2주간 2단계로 조정"',
            'description': 'md5:df7f0c237a5ed5e786ce5c91efbeaab3',
            'channel_id': 'NTV-ytnnews24-0',
            'start_time': 1597026780000,
        },
    }, {
        'url': 'https://tv.naver.com/l/51549',
        'info_dict': {
            'id': '51549',
            'ext': 'mp4',
            'title': '연합뉴스TV - 코로나19 뉴스특보',
            'description': 'md5:c655e82091bc21e413f549c0eaccc481',
            'channel_id': 'NTV-yonhapnewstv-0',
            'start_time': 1596406380000,
        },
    }, {
        'url': 'https://tv.naver.com/l/54887',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        page = self._download_webpage(url, video_id, 'Downloading Page', 'Unable to download Page')
        secure_url = self._search_regex(r'sApiF:\s+(?:"|\')([^"\']+)', page, 'secureurl')

        info = self._extract_video_info(video_id, secure_url)
        info.update({
            'description': self._og_search_description(page)
        })

        return info

    def _extract_video_info(self, video_id, url):
        video_data = self._download_json(url, video_id, headers=self.geo_verification_headers())
        meta = video_data.get('meta')
        status = meta.get('status')

        if status == 'CLOSED':
            raise ExtractorError('Stream is offline.', expected=True)
        elif status != 'OPENED':
            raise ExtractorError('Unknown status %s' % status)

        title = meta.get('title')
        stream_list = video_data.get('streams')

        if stream_list is None:
            raise ExtractorError('Could not get stream data.', expected=True)

        formats = []
        for quality in stream_list:
            if not quality.get('url'):
                continue

            prop = quality.get('property')
            if prop.get('abr'):  # This abr doesn't mean Average audio bitrate.
                continue

            formats.extend(self._extract_m3u8_formats(
                quality.get('url'), video_id, 'mp4',
                m3u8_id=quality.get('qualityId'), live=True
            ))

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'channel_id': meta.get('channelId'),
            'channel_url': meta.get('channelUrl'),
            'thumbnail': meta.get('imgUrl'),
            'start_time': meta.get('startTime'),
            'categories': [meta.get('categoryId')],
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
        qs = parse_qs(urlparse(url).query)

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
