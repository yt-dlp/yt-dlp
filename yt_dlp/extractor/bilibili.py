import base64
import functools
import hashlib
import itertools
import math
import time
import urllib.error
import urllib.parse

from .common import InfoExtractor, SearchInfoExtractor
from ..dependencies import Cryptodome
from ..utils import (
    ExtractorError,
    GeoRestrictedError,
    InAdvancePagedList,
    OnDemandPagedList,
    filter_dict,
    float_or_none,
    format_field,
    int_or_none,
    make_archive_id,
    merge_dicts,
    mimetype2ext,
    parse_count,
    parse_qs,
    qualities,
    smuggle_url,
    srt_subtitles_timecode,
    str_or_none,
    traverse_obj,
    try_call,
    unified_timestamp,
    unsmuggle_url,
    url_or_none,
    urlencode_postdata,
)


class BilibiliBaseIE(InfoExtractor):
    def extract_formats(self, play_info):
        format_names = {
            r['quality']: traverse_obj(r, 'new_description', 'display_desc')
            for r in traverse_obj(play_info, ('support_formats', lambda _, v: v['quality']))
        }

        audios = traverse_obj(play_info, ('dash', 'audio', ...))
        flac_audio = traverse_obj(play_info, ('dash', 'flac', 'audio'))
        if flac_audio:
            audios.append(flac_audio)
        formats = [{
            'url': traverse_obj(audio, 'baseUrl', 'base_url', 'url'),
            'ext': mimetype2ext(traverse_obj(audio, 'mimeType', 'mime_type')),
            'acodec': audio.get('codecs'),
            'vcodec': 'none',
            'tbr': float_or_none(audio.get('bandwidth'), scale=1000),
            'filesize': int_or_none(audio.get('size'))
        } for audio in audios]

        formats.extend({
            'url': traverse_obj(video, 'baseUrl', 'base_url', 'url'),
            'ext': mimetype2ext(traverse_obj(video, 'mimeType', 'mime_type')),
            'fps': float_or_none(traverse_obj(video, 'frameRate', 'frame_rate')),
            'width': int_or_none(video.get('width')),
            'height': int_or_none(video.get('height')),
            'vcodec': video.get('codecs'),
            'acodec': 'none' if audios else None,
            'tbr': float_or_none(video.get('bandwidth'), scale=1000),
            'filesize': int_or_none(video.get('size')),
            'quality': int_or_none(video.get('id')),
            'format': format_names.get(video.get('id')),
        } for video in traverse_obj(play_info, ('dash', 'video', ...)))

        missing_formats = format_names.keys() - set(traverse_obj(formats, (..., 'quality')))
        if missing_formats:
            self.to_screen(f'Format(s) {", ".join(format_names[i] for i in missing_formats)} are missing; '
                           f'you have to login or become premium member to download them. {self._login_hint()}')

        return formats

    def json2srt(self, json_data):
        srt_data = ''
        for idx, line in enumerate(json_data.get('body') or []):
            srt_data += (f'{idx + 1}\n'
                         f'{srt_subtitles_timecode(line["from"])} --> {srt_subtitles_timecode(line["to"])}\n'
                         f'{line["content"]}\n\n')
        return srt_data

    def _get_subtitles(self, video_id, aid, cid):
        subtitles = {
            'danmaku': [{
                'ext': 'xml',
                'url': f'https://comment.bilibili.com/{cid}.xml',
            }]
        }

        video_info_json = self._download_json(f'https://api.bilibili.com/x/player/v2?aid={aid}&cid={cid}', video_id)
        for s in traverse_obj(video_info_json, ('data', 'subtitle', 'subtitles', ...)):
            subtitles.setdefault(s['lan'], []).append({
                'ext': 'srt',
                'data': self.json2srt(self._download_json(s['subtitle_url'], video_id))
            })
        return subtitles

    def _get_chapters(self, aid, cid):
        chapters = aid and cid and self._download_json(
            'https://api.bilibili.com/x/player/v2', aid, query={'aid': aid, 'cid': cid},
            note='Extracting chapters', fatal=False)
        return traverse_obj(chapters, ('data', 'view_points', ..., {
            'title': 'content',
            'start_time': 'from',
            'end_time': 'to',
        })) or None

    def _get_comments(self, aid):
        for idx in itertools.count(1):
            replies = traverse_obj(
                self._download_json(
                    f'https://api.bilibili.com/x/v2/reply?pn={idx}&oid={aid}&type=1&jsonp=jsonp&sort=2&_=1567227301685',
                    aid, note=f'Extracting comments from page {idx}', fatal=False),
                ('data', 'replies'))
            if not replies:
                return
            for children in map(self._get_all_children, replies):
                yield from children

    def _get_all_children(self, reply):
        yield {
            'author': traverse_obj(reply, ('member', 'uname')),
            'author_id': traverse_obj(reply, ('member', 'mid')),
            'id': reply.get('rpid'),
            'text': traverse_obj(reply, ('content', 'message')),
            'timestamp': reply.get('ctime'),
            'parent': reply.get('parent') or 'root',
        }
        for children in map(self._get_all_children, traverse_obj(reply, ('replies', ...))):
            yield from children


class BiliBiliIE(BilibiliBaseIE):
    _VALID_URL = r'https?://www\.bilibili\.com/(?:video/|festival/\w+\?(?:[^#]*&)?bvid=)[aAbB][vV](?P<id>[^/?#&]+)'

    _TESTS = [{
        'url': 'https://www.bilibili.com/video/BV13x41117TL',
        'info_dict': {
            'id': 'BV13x41117TL',
            'title': '阿滴英文｜英文歌分享#6 "Closer',
            'ext': 'mp4',
            'description': '滴妹今天唱Closer給你聽! 有史以来，被推最多次也是最久的歌曲，其实歌词跟我原本想像差蛮多的，不过还是好听！ 微博@阿滴英文',
            'uploader_id': '65880958',
            'uploader': '阿滴英文',
            'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)$',
            'duration': 554.117,
            'tags': list,
            'comment_count': int,
            'upload_date': '20170301',
            'timestamp': 1488353834,
            'like_count': int,
            'view_count': int,
        },
    }, {
        # old av URL version
        'url': 'http://www.bilibili.com/video/av1074402/',
        'info_dict': {
            'thumbnail': r're:^https?://.*\.(jpg|jpeg)$',
            'ext': 'mp4',
            'uploader': '菊子桑',
            'uploader_id': '156160',
            'id': 'BV11x411K7CN',
            'title': '【金坷垃】金泡沫',
            'duration': 308.36,
            'upload_date': '20140420',
            'timestamp': 1397983878,
            'description': 'md5:ce18c2a2d2193f0df2917d270f2e5923',
            'like_count': int,
            'comment_count': int,
            'view_count': int,
            'tags': list,
        },
        'params': {'skip_download': True},
    }, {
        'note': 'Anthology',
        'url': 'https://www.bilibili.com/video/BV1bK411W797',
        'info_dict': {
            'id': 'BV1bK411W797',
            'title': '物语中的人物是如何吐槽自己的OP的'
        },
        'playlist_count': 18,
        'playlist': [{
            'info_dict': {
                'id': 'BV1bK411W797_p1',
                'ext': 'mp4',
                'title': '物语中的人物是如何吐槽自己的OP的 p01 Staple Stable/战场原+羽川',
                'tags': 'count:11',
                'timestamp': 1589601697,
                'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)$',
                'uploader': '打牌还是打桩',
                'uploader_id': '150259984',
                'like_count': int,
                'comment_count': int,
                'upload_date': '20200516',
                'view_count': int,
                'description': 'md5:e3c401cf7bc363118d1783dd74068a68',
                'duration': 90.314,
            }
        }]
    }, {
        'note': 'Specific page of Anthology',
        'url': 'https://www.bilibili.com/video/BV1bK411W797?p=1',
        'info_dict': {
            'id': 'BV1bK411W797_p1',
            'ext': 'mp4',
            'title': '物语中的人物是如何吐槽自己的OP的 p01 Staple Stable/战场原+羽川',
            'tags': 'count:11',
            'timestamp': 1589601697,
            'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)$',
            'uploader': '打牌还是打桩',
            'uploader_id': '150259984',
            'like_count': int,
            'comment_count': int,
            'upload_date': '20200516',
            'view_count': int,
            'description': 'md5:e3c401cf7bc363118d1783dd74068a68',
            'duration': 90.314,
        }
    }, {
        'note': 'video has subtitles',
        'url': 'https://www.bilibili.com/video/BV12N4y1M7rh',
        'info_dict': {
            'id': 'BV12N4y1M7rh',
            'ext': 'mp4',
            'title': 'md5:96e8bb42c2b432c0d4ce3434a61479c1',
            'tags': list,
            'description': 'md5:afde2b7ba9025c01d9e3dde10de221e4',
            'duration': 313.557,
            'upload_date': '20220709',
            'uploader': '小夫Tech',
            'timestamp': 1657347907,
            'uploader_id': '1326814124',
            'comment_count': int,
            'view_count': int,
            'like_count': int,
            'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)$',
            'subtitles': 'count:2'
        },
        'params': {'listsubtitles': True},
    }, {
        'url': 'https://www.bilibili.com/video/av8903802/',
        'info_dict': {
            'id': 'BV13x41117TL',
            'ext': 'mp4',
            'title': '阿滴英文｜英文歌分享#6 "Closer',
            'upload_date': '20170301',
            'description': 'md5:3b1b9e25b78da4ef87e9b548b88ee76a',
            'timestamp': 1488353834,
            'uploader_id': '65880958',
            'uploader': '阿滴英文',
            'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)$',
            'duration': 554.117,
            'tags': list,
            'comment_count': int,
            'view_count': int,
            'like_count': int,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'note': 'video has chapter',
        'url': 'https://www.bilibili.com/video/BV1vL411G7N7/',
        'info_dict': {
            'id': 'BV1vL411G7N7',
            'ext': 'mp4',
            'title': '如何为你的B站视频添加进度条分段',
            'timestamp': 1634554558,
            'upload_date': '20211018',
            'description': 'md5:a9a3d6702b3a94518d419b2e9c320a6d',
            'tags': list,
            'uploader': '爱喝咖啡的当麻',
            'duration': 669.482,
            'uploader_id': '1680903',
            'chapters': 'count:6',
            'comment_count': int,
            'view_count': int,
            'like_count': int,
            'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)$',
        },
        'params': {'skip_download': True},
    }, {
        'note': 'video redirects to festival page',
        'url': 'https://www.bilibili.com/video/BV1wP4y1P72h',
        'info_dict': {
            'id': 'BV1wP4y1P72h',
            'ext': 'mp4',
            'title': '牛虎年相交之际，一首传统民族打击乐《牛斗虎》祝大家新春快乐，虎年大吉！【bilibili音乐虎闹新春】',
            'timestamp': 1643947497,
            'upload_date': '20220204',
            'description': 'md5:8681a0d4d2c06b4ae27e59c8080a7fe6',
            'uploader': '叨叨冯聊音乐',
            'duration': 246.719,
            'uploader_id': '528182630',
            'view_count': int,
            'like_count': int,
            'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)$',
        },
        'params': {'skip_download': True},
    }, {
        'note': 'newer festival video',
        'url': 'https://www.bilibili.com/festival/2023honkaiimpact3gala?bvid=BV1ay4y1d77f',
        'info_dict': {
            'id': 'BV1ay4y1d77f',
            'ext': 'mp4',
            'title': '【崩坏3新春剧场】为特别的你送上祝福！',
            'timestamp': 1674273600,
            'upload_date': '20230121',
            'description': 'md5:58af66d15c6a0122dc30c8adfd828dd8',
            'uploader': '果蝇轰',
            'duration': 1111.722,
            'uploader_id': '8469526',
            'view_count': int,
            'like_count': int,
            'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)$',
        },
        'params': {'skip_download': True},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        initial_state = self._search_json(r'window\.__INITIAL_STATE__\s*=', webpage, 'initial state', video_id)

        is_festival = 'videoData' not in initial_state
        if is_festival:
            video_data = initial_state['videoInfo']
        else:
            play_info = self._search_json(r'window\.__playinfo__\s*=', webpage, 'play info', video_id)['data']
            video_data = initial_state['videoData']

        video_id, title = video_data['bvid'], video_data.get('title')

        # Bilibili anthologies are similar to playlists but all videos share the same video ID as the anthology itself.
        page_list_json = not is_festival and traverse_obj(
            self._download_json(
                'https://api.bilibili.com/x/player/pagelist', video_id,
                fatal=False, query={'bvid': video_id, 'jsonp': 'jsonp'},
                note='Extracting videos in anthology'),
            'data', expected_type=list) or []
        is_anthology = len(page_list_json) > 1

        part_id = int_or_none(parse_qs(url).get('p', [None])[-1])
        if is_anthology and not part_id and self._yes_playlist(video_id, video_id):
            return self.playlist_from_matches(
                page_list_json, video_id, title, ie=BiliBiliIE,
                getter=lambda entry: f'https://www.bilibili.com/video/{video_id}?p={entry["page"]}')

        if is_anthology:
            part_id = part_id or 1
            title += f' p{part_id:02d} {traverse_obj(page_list_json, (part_id - 1, "part")) or ""}'

        aid = video_data.get('aid')
        old_video_id = format_field(aid, None, f'%s_part{part_id or 1}')

        cid = traverse_obj(video_data, ('pages', part_id - 1, 'cid')) if part_id else video_data.get('cid')

        festival_info = {}
        if is_festival:
            play_info = self._download_json(
                'https://api.bilibili.com/x/player/playurl', video_id,
                query={'bvid': video_id, 'cid': cid, 'fnval': 4048},
                note='Extracting festival video formats')['data']

            festival_info = traverse_obj(initial_state, {
                'uploader': ('videoInfo', 'upName'),
                'uploader_id': ('videoInfo', 'upMid', {str_or_none}),
                'like_count': ('videoStatus', 'like', {int_or_none}),
                'thumbnail': ('sectionEpisodes', lambda _, v: v['bvid'] == video_id, 'cover'),
            }, get_all=False)

        return {
            **traverse_obj(initial_state, {
                'uploader': ('upData', 'name'),
                'uploader_id': ('upData', 'mid', {str_or_none}),
                'like_count': ('videoData', 'stat', 'like', {int_or_none}),
                'tags': ('tags', ..., 'tag_name'),
                'thumbnail': ('videoData', 'pic', {url_or_none}),
            }),
            **festival_info,
            **traverse_obj(video_data, {
                'description': 'desc',
                'timestamp': ('pubdate', {int_or_none}),
                'view_count': (('viewCount', ('stat', 'view')), {int_or_none}),
                'comment_count': ('stat', 'reply', {int_or_none}),
            }, get_all=False),
            'id': f'{video_id}{format_field(part_id, None, "_p%d")}',
            'formats': self.extract_formats(play_info),
            '_old_archive_ids': [make_archive_id(self, old_video_id)] if old_video_id else None,
            'title': title,
            'duration': float_or_none(play_info.get('timelength'), scale=1000),
            'chapters': self._get_chapters(aid, cid),
            'subtitles': self.extract_subtitles(video_id, aid, cid),
            '__post_extractor': self.extract_comments(aid),
            'http_headers': {'Referer': url},
        }


class BiliBiliBangumiIE(BilibiliBaseIE):
    _VALID_URL = r'(?x)https?://www\.bilibili\.com/bangumi/play/(?P<id>(?:ss|ep)\d+)'

    _TESTS = [{
        'url': 'https://www.bilibili.com/bangumi/play/ss897',
        'info_dict': {
            'id': 'ss897',
            'ext': 'mp4',
            'series': '神的记事本',
            'season': '神的记事本',
            'season_id': 897,
            'season_number': 1,
            'episode': '你与旅行包',
            'episode_number': 2,
            'title': '神的记事本：第2话 你与旅行包',
            'duration': 1428.487,
            'timestamp': 1310809380,
            'upload_date': '20110716',
            'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)$',
        },
    }, {
        'url': 'https://www.bilibili.com/bangumi/play/ep508406',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        if '您所在的地区无法观看本片' in webpage:
            raise GeoRestrictedError('This video is restricted')
        elif ('开通大会员观看' in webpage and '__playinfo__' not in webpage
                or '正在观看预览，大会员免费看全片' in webpage):
            self.raise_login_required('This video is for premium members only')

        play_info = self._search_json(r'window\.__playinfo__\s*=', webpage, 'play info', video_id)['data']
        formats = self.extract_formats(play_info)
        if (not formats and '成为大会员抢先看' in webpage
                and play_info.get('durl') and not play_info.get('dash')):
            self.raise_login_required('This video is for premium members only')

        initial_state = self._search_json(r'window\.__INITIAL_STATE__\s*=', webpage, 'initial state', video_id)

        season_id = traverse_obj(initial_state, ('mediaInfo', 'season_id'))
        season_number = season_id and next((
            idx + 1 for idx, e in enumerate(
                traverse_obj(initial_state, ('mediaInfo', 'seasons', ...)))
            if e.get('season_id') == season_id
        ), None)

        return {
            'id': video_id,
            'formats': formats,
            'title': traverse_obj(initial_state, 'h1Title'),
            'episode': traverse_obj(initial_state, ('epInfo', 'long_title')),
            'episode_number': int_or_none(traverse_obj(initial_state, ('epInfo', 'title'))),
            'series': traverse_obj(initial_state, ('mediaInfo', 'series')),
            'season': traverse_obj(initial_state, ('mediaInfo', 'season_title')),
            'season_id': season_id,
            'season_number': season_number,
            'thumbnail': traverse_obj(initial_state, ('epInfo', 'cover')),
            'timestamp': traverse_obj(initial_state, ('epInfo', 'pub_time')),
            'duration': float_or_none(play_info.get('timelength'), scale=1000),
            'subtitles': self.extract_subtitles(
                video_id, initial_state, traverse_obj(initial_state, ('epInfo', 'cid'))),
            '__post_extractor': self.extract_comments(traverse_obj(initial_state, ('epInfo', 'aid'))),
            'http_headers': {'Referer': url, **self.geo_verification_headers()},
        }


class BiliBiliBangumiMediaIE(InfoExtractor):
    _VALID_URL = r'https?://www\.bilibili\.com/bangumi/media/md(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.bilibili.com/bangumi/media/md24097891',
        'info_dict': {
            'id': '24097891',
        },
        'playlist_mincount': 25,
    }]

    def _real_extract(self, url):
        media_id = self._match_id(url)
        webpage = self._download_webpage(url, media_id)

        initial_state = self._search_json(r'window\.__INITIAL_STATE__\s*=', webpage, 'initial_state', media_id)
        episode_list = self._download_json(
            'https://api.bilibili.com/pgc/web/season/section', media_id,
            query={'season_id': initial_state['mediaInfo']['season_id']},
            note='Downloading season info')['result']['main_section']['episodes']

        return self.playlist_result((
            self.url_result(entry['share_url'], BiliBiliBangumiIE, entry['aid'])
            for entry in episode_list), media_id)


class BilibiliSpaceBaseIE(InfoExtractor):
    def _extract_playlist(self, fetch_page, get_metadata, get_entries):
        first_page = fetch_page(0)
        metadata = get_metadata(first_page)

        paged_list = InAdvancePagedList(
            lambda idx: get_entries(fetch_page(idx) if idx else first_page),
            metadata['page_count'], metadata['page_size'])

        return metadata, paged_list


class BilibiliSpaceVideoIE(BilibiliSpaceBaseIE):
    _VALID_URL = r'https?://space\.bilibili\.com/(?P<id>\d+)(?P<video>/video)?/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://space.bilibili.com/3985676/video',
        'info_dict': {
            'id': '3985676',
        },
        'playlist_mincount': 178,
    }, {
        'url': 'https://space.bilibili.com/313580179/video',
        'info_dict': {
            'id': '313580179',
        },
        'playlist_mincount': 92,
    }]

    def _extract_signature(self, playlist_id):
        session_data = self._download_json('https://api.bilibili.com/x/web-interface/nav', playlist_id, fatal=False)

        key_from_url = lambda x: x[x.rfind('/') + 1:].split('.')[0]
        img_key = traverse_obj(
            session_data, ('data', 'wbi_img', 'img_url', {key_from_url})) or '34478ba821254d9d93542680e3b86100'
        sub_key = traverse_obj(
            session_data, ('data', 'wbi_img', 'sub_url', {key_from_url})) or '7e16a90d190a4355a78fd00b32a38de6'

        session_key = img_key + sub_key

        signature_values = []
        for position in (
            46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39,
            12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63,
            57, 62, 11, 36, 20, 34, 44, 52
        ):
            char_at_position = try_call(lambda: session_key[position])
            if char_at_position:
                signature_values.append(char_at_position)

        return ''.join(signature_values)[:32]

    def _real_extract(self, url):
        playlist_id, is_video_url = self._match_valid_url(url).group('id', 'video')
        if not is_video_url:
            self.to_screen('A channel URL was given. Only the channel\'s videos will be downloaded. '
                           'To download audios, add a "/audio" to the URL')

        signature = self._extract_signature(playlist_id)

        def fetch_page(page_idx):
            query = {
                'keyword': '',
                'mid': playlist_id,
                'order': 'pubdate',
                'order_avoided': 'true',
                'platform': 'web',
                'pn': page_idx + 1,
                'ps': 30,
                'tid': 0,
                'web_location': 1550101,
                'wts': int(time.time()),
            }
            query['w_rid'] = hashlib.md5(f'{urllib.parse.urlencode(query)}{signature}'.encode()).hexdigest()

            try:
                response = self._download_json('https://api.bilibili.com/x/space/wbi/arc/search',
                                               playlist_id, note=f'Downloading page {page_idx}', query=query)
            except ExtractorError as e:
                if isinstance(e.cause, urllib.error.HTTPError) and e.cause.code == 412:
                    raise ExtractorError(
                        'Request is blocked by server (412), please add cookies, wait and try later.', expected=True)
                raise
            if response['code'] == -401:
                raise ExtractorError(
                    'Request is blocked by server (401), please add cookies, wait and try later.', expected=True)
            return response['data']

        def get_metadata(page_data):
            page_size = page_data['page']['ps']
            entry_count = page_data['page']['count']
            return {
                'page_count': math.ceil(entry_count / page_size),
                'page_size': page_size,
            }

        def get_entries(page_data):
            for entry in traverse_obj(page_data, ('list', 'vlist')) or []:
                yield self.url_result(f'https://www.bilibili.com/video/{entry["bvid"]}', BiliBiliIE, entry['bvid'])

        metadata, paged_list = self._extract_playlist(fetch_page, get_metadata, get_entries)
        return self.playlist_result(paged_list, playlist_id)


class BilibiliSpaceAudioIE(BilibiliSpaceBaseIE):
    _VALID_URL = r'https?://space\.bilibili\.com/(?P<id>\d+)/audio'
    _TESTS = [{
        'url': 'https://space.bilibili.com/313580179/audio',
        'info_dict': {
            'id': '313580179',
        },
        'playlist_mincount': 1,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        def fetch_page(page_idx):
            return self._download_json(
                'https://api.bilibili.com/audio/music-service/web/song/upper', playlist_id,
                note=f'Downloading page {page_idx}',
                query={'uid': playlist_id, 'pn': page_idx + 1, 'ps': 30, 'order': 1, 'jsonp': 'jsonp'})['data']

        def get_metadata(page_data):
            return {
                'page_count': page_data['pageCount'],
                'page_size': page_data['pageSize'],
            }

        def get_entries(page_data):
            for entry in page_data.get('data', []):
                yield self.url_result(f'https://www.bilibili.com/audio/au{entry["id"]}', BilibiliAudioIE, entry['id'])

        metadata, paged_list = self._extract_playlist(fetch_page, get_metadata, get_entries)
        return self.playlist_result(paged_list, playlist_id)


class BilibiliSpacePlaylistIE(BilibiliSpaceBaseIE):
    _VALID_URL = r'https?://space.bilibili\.com/(?P<mid>\d+)/channel/collectiondetail\?sid=(?P<sid>\d+)'
    _TESTS = [{
        'url': 'https://space.bilibili.com/2142762/channel/collectiondetail?sid=57445',
        'info_dict': {
            'id': '2142762_57445',
            'title': '《底特律 变人》'
        },
        'playlist_mincount': 31,
    }]

    def _real_extract(self, url):
        mid, sid = self._match_valid_url(url).group('mid', 'sid')
        playlist_id = f'{mid}_{sid}'

        def fetch_page(page_idx):
            return self._download_json(
                'https://api.bilibili.com/x/polymer/space/seasons_archives_list',
                playlist_id, note=f'Downloading page {page_idx}',
                query={'mid': mid, 'season_id': sid, 'page_num': page_idx + 1, 'page_size': 30})['data']

        def get_metadata(page_data):
            page_size = page_data['page']['page_size']
            entry_count = page_data['page']['total']
            return {
                'page_count': math.ceil(entry_count / page_size),
                'page_size': page_size,
                'title': traverse_obj(page_data, ('meta', 'name'))
            }

        def get_entries(page_data):
            for entry in page_data.get('archives', []):
                yield self.url_result(f'https://www.bilibili.com/video/{entry["bvid"]}',
                                      BiliBiliIE, entry['bvid'])

        metadata, paged_list = self._extract_playlist(fetch_page, get_metadata, get_entries)
        return self.playlist_result(paged_list, playlist_id, metadata['title'])


class BilibiliCategoryIE(InfoExtractor):
    IE_NAME = 'Bilibili category extractor'
    _MAX_RESULTS = 1000000
    _VALID_URL = r'https?://www\.bilibili\.com/v/[a-zA-Z]+\/[a-zA-Z]+'
    _TESTS = [{
        'url': 'https://www.bilibili.com/v/kichiku/mad',
        'info_dict': {
            'id': 'kichiku: mad',
            'title': 'kichiku: mad'
        },
        'playlist_mincount': 45,
        'params': {
            'playlistend': 45
        }
    }]

    def _fetch_page(self, api_url, num_pages, query, page_num):
        parsed_json = self._download_json(
            api_url, query, query={'Search_key': query, 'pn': page_num},
            note='Extracting results from page %s of %s' % (page_num, num_pages))

        video_list = traverse_obj(parsed_json, ('data', 'archives'), expected_type=list)
        if not video_list:
            raise ExtractorError('Failed to retrieve video list for page %d' % page_num)

        for video in video_list:
            yield self.url_result(
                'https://www.bilibili.com/video/%s' % video['bvid'], 'BiliBili', video['bvid'])

    def _entries(self, category, subcategory, query):
        # map of categories : subcategories : RIDs
        rid_map = {
            'kichiku': {
                'mad': 26,
                'manual_vocaloid': 126,
                'guide': 22,
                'theatre': 216,
                'course': 127
            },
        }

        if category not in rid_map:
            raise ExtractorError(
                f'The category {category} isn\'t supported. Supported categories: {list(rid_map.keys())}')
        if subcategory not in rid_map[category]:
            raise ExtractorError(
                f'The subcategory {subcategory} isn\'t supported for this category. Supported subcategories: {list(rid_map[category].keys())}')
        rid_value = rid_map[category][subcategory]

        api_url = 'https://api.bilibili.com/x/web-interface/newlist?rid=%d&type=1&ps=20&jsonp=jsonp' % rid_value
        page_json = self._download_json(api_url, query, query={'Search_key': query, 'pn': '1'})
        page_data = traverse_obj(page_json, ('data', 'page'), expected_type=dict)
        count, size = int_or_none(page_data.get('count')), int_or_none(page_data.get('size'))
        if count is None or not size:
            raise ExtractorError('Failed to calculate either page count or size')

        num_pages = math.ceil(count / size)

        return OnDemandPagedList(functools.partial(
            self._fetch_page, api_url, num_pages, query), size)

    def _real_extract(self, url):
        category, subcategory = urllib.parse.urlparse(url).path.split('/')[2:4]
        query = '%s: %s' % (category, subcategory)

        return self.playlist_result(self._entries(category, subcategory, query), query, query)


class BiliBiliSearchIE(SearchInfoExtractor):
    IE_DESC = 'Bilibili video search'
    _MAX_RESULTS = 100000
    _SEARCH_KEY = 'bilisearch'

    def _search_results(self, query):
        for page_num in itertools.count(1):
            videos = self._download_json(
                'https://api.bilibili.com/x/web-interface/search/type', query,
                note=f'Extracting results from page {page_num}', query={
                    'Search_key': query,
                    'keyword': query,
                    'page': page_num,
                    'context': '',
                    'duration': 0,
                    'tids_2': '',
                    '__refresh__': 'true',
                    'search_type': 'video',
                    'tids': 0,
                    'highlight': 1,
                })['data'].get('result')
            if not videos:
                break
            for video in videos:
                yield self.url_result(video['arcurl'], 'BiliBili', str(video['aid']))


class BilibiliAudioBaseIE(InfoExtractor):
    def _call_api(self, path, sid, query=None):
        if not query:
            query = {'sid': sid}
        return self._download_json(
            'https://www.bilibili.com/audio/music-service-c/web/' + path,
            sid, query=query)['data']


class BilibiliAudioIE(BilibiliAudioBaseIE):
    _VALID_URL = r'https?://(?:www\.)?bilibili\.com/audio/au(?P<id>\d+)'
    _TEST = {
        'url': 'https://www.bilibili.com/audio/au1003142',
        'md5': 'fec4987014ec94ef9e666d4d158ad03b',
        'info_dict': {
            'id': '1003142',
            'ext': 'm4a',
            'title': '【tsukimi】YELLOW / 神山羊',
            'artist': 'tsukimi',
            'comment_count': int,
            'description': 'YELLOW的mp3版！',
            'duration': 183,
            'subtitles': {
                'origin': [{
                    'ext': 'lrc',
                }],
            },
            'thumbnail': r're:^https?://.+\.jpg',
            'timestamp': 1564836614,
            'upload_date': '20190803',
            'uploader': 'tsukimi-つきみぐー',
            'view_count': int,
        },
    }

    def _real_extract(self, url):
        au_id = self._match_id(url)

        play_data = self._call_api('url', au_id)
        formats = [{
            'url': play_data['cdns'][0],
            'filesize': int_or_none(play_data.get('size')),
            'vcodec': 'none'
        }]

        for a_format in formats:
            a_format.setdefault('http_headers', {}).update({
                'Referer': url,
            })

        song = self._call_api('song/info', au_id)
        title = song['title']
        statistic = song.get('statistic') or {}

        subtitles = None
        lyric = song.get('lyric')
        if lyric:
            subtitles = {
                'origin': [{
                    'url': lyric,
                }]
            }

        return {
            'id': au_id,
            'title': title,
            'formats': formats,
            'artist': song.get('author'),
            'comment_count': int_or_none(statistic.get('comment')),
            'description': song.get('intro'),
            'duration': int_or_none(song.get('duration')),
            'subtitles': subtitles,
            'thumbnail': song.get('cover'),
            'timestamp': int_or_none(song.get('passtime')),
            'uploader': song.get('uname'),
            'view_count': int_or_none(statistic.get('play')),
        }


class BilibiliAudioAlbumIE(BilibiliAudioBaseIE):
    _VALID_URL = r'https?://(?:www\.)?bilibili\.com/audio/am(?P<id>\d+)'
    _TEST = {
        'url': 'https://www.bilibili.com/audio/am10624',
        'info_dict': {
            'id': '10624',
            'title': '每日新曲推荐（每日11:00更新）',
            'description': '每天11:00更新，为你推送最新音乐',
        },
        'playlist_count': 19,
    }

    def _real_extract(self, url):
        am_id = self._match_id(url)

        songs = self._call_api(
            'song/of-menu', am_id, {'sid': am_id, 'pn': 1, 'ps': 100})['data']

        entries = []
        for song in songs:
            sid = str_or_none(song.get('id'))
            if not sid:
                continue
            entries.append(self.url_result(
                'https://www.bilibili.com/audio/au' + sid,
                BilibiliAudioIE.ie_key(), sid))

        if entries:
            album_data = self._call_api('menu/info', am_id) or {}
            album_title = album_data.get('title')
            if album_title:
                for entry in entries:
                    entry['album'] = album_title
                return self.playlist_result(
                    entries, am_id, album_title, album_data.get('intro'))

        return self.playlist_result(entries, am_id)


class BiliBiliPlayerIE(InfoExtractor):
    _VALID_URL = r'https?://player\.bilibili\.com/player\.html\?.*?\baid=(?P<id>\d+)'
    _TEST = {
        'url': 'http://player.bilibili.com/player.html?aid=92494333&cid=157926707&page=1',
        'only_matching': True,
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result(
            'http://www.bilibili.tv/video/av%s/' % video_id,
            ie=BiliBiliIE.ie_key(), video_id=video_id)


class BiliIntlBaseIE(InfoExtractor):
    _API_URL = 'https://api.bilibili.tv/intl/gateway'
    _NETRC_MACHINE = 'biliintl'

    def _call_api(self, endpoint, *args, **kwargs):
        json = self._download_json(self._API_URL + endpoint, *args, **kwargs)
        if json.get('code'):
            if json['code'] in (10004004, 10004005, 10023006):
                self.raise_login_required()
            elif json['code'] == 10004001:
                self.raise_geo_restricted()
            else:
                if json.get('message') and str(json['code']) != json['message']:
                    errmsg = f'{kwargs.get("errnote", "Unable to download JSON metadata")}: {self.IE_NAME} said: {json["message"]}'
                else:
                    errmsg = kwargs.get('errnote', 'Unable to download JSON metadata')
                if kwargs.get('fatal'):
                    raise ExtractorError(errmsg)
                else:
                    self.report_warning(errmsg)
        return json.get('data')

    def json2srt(self, json):
        data = '\n\n'.join(
            f'{i + 1}\n{srt_subtitles_timecode(line["from"])} --> {srt_subtitles_timecode(line["to"])}\n{line["content"]}'
            for i, line in enumerate(traverse_obj(json, (
                'body', lambda _, l: l['content'] and l['from'] and l['to']))))
        return data

    def _get_subtitles(self, *, ep_id=None, aid=None):
        sub_json = self._call_api(
            '/web/v2/subtitle', ep_id or aid, fatal=False,
            note='Downloading subtitles list', errnote='Unable to download subtitles list',
            query=filter_dict({
                'platform': 'web',
                's_locale': 'en_US',
                'episode_id': ep_id,
                'aid': aid,
            })) or {}
        subtitles = {}
        for sub in sub_json.get('subtitles') or []:
            sub_url = sub.get('url')
            if not sub_url:
                continue
            sub_data = self._download_json(
                sub_url, ep_id or aid, errnote='Unable to download subtitles', fatal=False,
                note='Downloading subtitles%s' % f' for {sub["lang"]}' if sub.get('lang') else '')
            if not sub_data:
                continue
            subtitles.setdefault(sub.get('lang_key', 'en'), []).append({
                'ext': 'srt',
                'data': self.json2srt(sub_data)
            })
        return subtitles

    def _get_formats(self, *, ep_id=None, aid=None):
        video_json = self._call_api(
            '/web/playurl', ep_id or aid, note='Downloading video formats',
            errnote='Unable to download video formats', query=filter_dict({
                'platform': 'web',
                'ep_id': ep_id,
                'aid': aid,
            }))
        video_json = video_json['playurl']
        formats = []
        for vid in video_json.get('video') or []:
            video_res = vid.get('video_resource') or {}
            video_info = vid.get('stream_info') or {}
            if not video_res.get('url'):
                continue
            formats.append({
                'url': video_res['url'],
                'ext': 'mp4',
                'format_note': video_info.get('desc_words'),
                'width': video_res.get('width'),
                'height': video_res.get('height'),
                'vbr': video_res.get('bandwidth'),
                'acodec': 'none',
                'vcodec': video_res.get('codecs'),
                'filesize': video_res.get('size'),
            })
        for aud in video_json.get('audio_resource') or []:
            if not aud.get('url'):
                continue
            formats.append({
                'url': aud['url'],
                'ext': 'mp4',
                'abr': aud.get('bandwidth'),
                'acodec': aud.get('codecs'),
                'vcodec': 'none',
                'filesize': aud.get('size'),
            })

        return formats

    def _parse_video_metadata(self, video_data):
        return {
            'title': video_data.get('title_display') or video_data.get('title'),
            'thumbnail': video_data.get('cover'),
            'episode_number': int_or_none(self._search_regex(
                r'^E(\d+)(?:$| - )', video_data.get('title_display') or '', 'episode number', default=None)),
        }

    def _perform_login(self, username, password):
        if not Cryptodome.RSA:
            raise ExtractorError('pycryptodomex not found. Please install', expected=True)

        key_data = self._download_json(
            'https://passport.bilibili.tv/x/intl/passport-login/web/key?lang=en-US', None,
            note='Downloading login key', errnote='Unable to download login key')['data']

        public_key = Cryptodome.RSA.importKey(key_data['key'])
        password_hash = Cryptodome.PKCS1_v1_5.new(public_key).encrypt((key_data['hash'] + password).encode('utf-8'))
        login_post = self._download_json(
            'https://passport.bilibili.tv/x/intl/passport-login/web/login/password?lang=en-US', None, data=urlencode_postdata({
                'username': username,
                'password': base64.b64encode(password_hash).decode('ascii'),
                'keep_me': 'true',
                's_locale': 'en_US',
                'isTrusted': 'true'
            }), note='Logging in', errnote='Unable to log in')
        if login_post.get('code'):
            if login_post.get('message'):
                raise ExtractorError(f'Unable to log in: {self.IE_NAME} said: {login_post["message"]}', expected=True)
            else:
                raise ExtractorError('Unable to log in')


class BiliIntlIE(BiliIntlBaseIE):
    _VALID_URL = r'https?://(?:www\.)?bili(?:bili\.tv|intl\.com)/(?:[a-zA-Z]{2}/)?(play/(?P<season_id>\d+)/(?P<ep_id>\d+)|video/(?P<aid>\d+))'
    _TESTS = [{
        # Bstation page
        'url': 'https://www.bilibili.tv/en/play/34613/341736',
        'info_dict': {
            'id': '341736',
            'ext': 'mp4',
            'title': 'E2 - The First Night',
            'thumbnail': r're:^https://pic\.bstarstatic\.com/ogv/.+\.png$',
            'episode_number': 2,
            'upload_date': '20201009',
            'episode': 'Episode 2',
            'timestamp': 1602259500,
            'description': 'md5:297b5a17155eb645e14a14b385ab547e',
            'chapters': [{
                'start_time': 0,
                'end_time': 76.242,
                'title': '<Untitled Chapter 1>'
            }, {
                'start_time': 76.242,
                'end_time': 161.161,
                'title': 'Intro'
            }, {
                'start_time': 1325.742,
                'end_time': 1403.903,
                'title': 'Outro'
            }],
        }
    }, {
        # Non-Bstation page
        'url': 'https://www.bilibili.tv/en/play/1033760/11005006',
        'info_dict': {
            'id': '11005006',
            'ext': 'mp4',
            'title': 'E3 - Who?',
            'thumbnail': r're:^https://pic\.bstarstatic\.com/ogv/.+\.png$',
            'episode_number': 3,
            'description': 'md5:e1a775e71a35c43f141484715470ad09',
            'episode': 'Episode 3',
            'upload_date': '20211219',
            'timestamp': 1639928700,
            'chapters': [{
                'start_time': 0,
                'end_time': 88.0,
                'title': '<Untitled Chapter 1>'
            }, {
                'start_time': 88.0,
                'end_time': 156.0,
                'title': 'Intro'
            }, {
                'start_time': 1173.0,
                'end_time': 1259.535,
                'title': 'Outro'
            }],
        }
    }, {
        # Subtitle with empty content
        'url': 'https://www.bilibili.tv/en/play/1005144/10131790',
        'info_dict': {
            'id': '10131790',
            'ext': 'mp4',
            'title': 'E140 - Two Heartbeats: Kabuto\'s Trap',
            'thumbnail': r're:^https://pic\.bstarstatic\.com/ogv/.+\.png$',
            'episode_number': 140,
        },
        'skip': 'According to the copyright owner\'s request, you may only watch the video after you log in.'
    }, {
        'url': 'https://www.bilibili.tv/en/video/2041863208',
        'info_dict': {
            'id': '2041863208',
            'ext': 'mp4',
            'timestamp': 1670874843,
            'description': 'Scheduled for April 2023.\nStudio: ufotable',
            'thumbnail': r're:https?://pic[-\.]bstarstatic.+/ugc/.+\.jpg$',
            'upload_date': '20221212',
            'title': 'Kimetsu no Yaiba Season 3 Official Trailer - Bstation',
        },
    }, {
        # episode comment extraction
        'url': 'https://www.bilibili.tv/en/play/34580/340317',
        'info_dict': {
            'id': '340317',
            'ext': 'mp4',
            'timestamp': 1604057820,
            'upload_date': '20201030',
            'episode_number': 5,
            'title': 'E5 - My Own Steel',
            'description': 'md5:2b17ab10aebb33e3c2a54da9e8e487e2',
            'thumbnail': r're:https?://pic\.bstarstatic\.com/ogv/.+\.png$',
            'episode': 'Episode 5',
            'comment_count': int,
            'chapters': [{
                'start_time': 0,
                'end_time': 61.0,
                'title': '<Untitled Chapter 1>'
            }, {
                'start_time': 61.0,
                'end_time': 134.0,
                'title': 'Intro'
            }, {
                'start_time': 1290.0,
                'end_time': 1379.0,
                'title': 'Outro'
            }],
        },
        'params': {
            'getcomments': True
        }
    }, {
        # user generated content comment extraction
        'url': 'https://www.bilibili.tv/en/video/2045730385',
        'info_dict': {
            'id': '2045730385',
            'ext': 'mp4',
            'description': 'md5:693b6f3967fb4e7e7764ea817857c33a',
            'timestamp': 1667891924,
            'upload_date': '20221108',
            'title': 'That Time I Got Reincarnated as a Slime: Scarlet Bond - Official Trailer 3| AnimeStan - Bstation',
            'comment_count': int,
            'thumbnail': 'https://pic.bstarstatic.com/ugc/f6c363659efd2eabe5683fbb906b1582.jpg',
        },
        'params': {
            'getcomments': True
        }
    }, {
        # episode id without intro and outro
        'url': 'https://www.bilibili.tv/en/play/1048837/11246489',
        'info_dict': {
            'id': '11246489',
            'ext': 'mp4',
            'title': 'E1 - Operation \'Strix\' <Owl>',
            'description': 'md5:b4434eb1a9a97ad2bccb779514b89f17',
            'timestamp': 1649516400,
            'thumbnail': 'https://pic.bstarstatic.com/ogv/62cb1de23ada17fb70fbe7bdd6ff29c29da02a64.png',
            'episode': 'Episode 1',
            'episode_number': 1,
            'upload_date': '20220409',
        },
    }, {
        'url': 'https://www.biliintl.com/en/play/34613/341736',
        'only_matching': True,
    }, {
        # User-generated content (as opposed to a series licensed from a studio)
        'url': 'https://bilibili.tv/en/video/2019955076',
        'only_matching': True,
    }, {
        # No language in URL
        'url': 'https://www.bilibili.tv/video/2019955076',
        'only_matching': True,
    }, {
        # Uppercase language in URL
        'url': 'https://www.bilibili.tv/EN/video/2019955076',
        'only_matching': True,
    }]

    def _make_url(video_id, series_id=None):
        if series_id:
            return f'https://www.bilibili.tv/en/play/{series_id}/{video_id}'
        return f'https://www.bilibili.tv/en/video/{video_id}'

    def _extract_video_metadata(self, url, video_id, season_id):
        url, smuggled_data = unsmuggle_url(url, {})
        if smuggled_data.get('title'):
            return smuggled_data

        webpage = self._download_webpage(url, video_id)
        # Bstation layout
        initial_data = (
            self._search_json(r'window\.__INITIAL_(?:DATA|STATE)__\s*=', webpage, 'preload state', video_id, default={})
            or self._search_nuxt_data(webpage, video_id, '__initialState', fatal=False, traverse=None))
        video_data = traverse_obj(
            initial_data, ('OgvVideo', 'epDetail'), ('UgcVideo', 'videoData'), ('ugc', 'archive'), expected_type=dict) or {}

        if season_id and not video_data:
            # Non-Bstation layout, read through episode list
            season_json = self._call_api(f'/web/v2/ogv/play/episodes?season_id={season_id}&platform=web', video_id)
            video_data = traverse_obj(season_json, (
                'sections', ..., 'episodes', lambda _, v: str(v['episode_id']) == video_id
            ), expected_type=dict, get_all=False)

        # XXX: webpage metadata may not accurate, it just used to not crash when video_data not found
        return merge_dicts(
            self._parse_video_metadata(video_data), self._search_json_ld(webpage, video_id, fatal=False), {
                'title': self._html_search_meta('og:title', webpage),
                'description': self._html_search_meta('og:description', webpage)
            })

    def _get_comments_reply(self, root_id, next_id=0, display_id=None):
        comment_api_raw_data = self._download_json(
            'https://api.bilibili.tv/reply/web/detail', display_id,
            note=f'Downloading reply comment of {root_id} - {next_id}',
            query={
                'platform': 'web',
                'ps': 20,  # comment's reply per page (default: 3)
                'root': root_id,
                'next': next_id,
            })

        for replies in traverse_obj(comment_api_raw_data, ('data', 'replies', ...)):
            yield {
                'author': traverse_obj(replies, ('member', 'name')),
                'author_id': traverse_obj(replies, ('member', 'mid')),
                'author_thumbnail': traverse_obj(replies, ('member', 'face')),
                'text': traverse_obj(replies, ('content', 'message')),
                'id': replies.get('rpid'),
                'like_count': int_or_none(replies.get('like_count')),
                'parent': replies.get('parent'),
                'timestamp': unified_timestamp(replies.get('ctime_text'))
            }

        if not traverse_obj(comment_api_raw_data, ('data', 'cursor', 'is_end')):
            yield from self._get_comments_reply(
                root_id, comment_api_raw_data['data']['cursor']['next'], display_id)

    def _get_comments(self, video_id, ep_id):
        for i in itertools.count(0):
            comment_api_raw_data = self._download_json(
                'https://api.bilibili.tv/reply/web/root', video_id,
                note=f'Downloading comment page {i + 1}',
                query={
                    'platform': 'web',
                    'pn': i,  # page number
                    'ps': 20,  # comment per page (default: 20)
                    'oid': video_id,
                    'type': 3 if ep_id else 1,  # 1: user generated content, 3: series content
                    'sort_type': 1,  # 1: best, 2: recent
                })

            for replies in traverse_obj(comment_api_raw_data, ('data', 'replies', ...)):
                yield {
                    'author': traverse_obj(replies, ('member', 'name')),
                    'author_id': traverse_obj(replies, ('member', 'mid')),
                    'author_thumbnail': traverse_obj(replies, ('member', 'face')),
                    'text': traverse_obj(replies, ('content', 'message')),
                    'id': replies.get('rpid'),
                    'like_count': int_or_none(replies.get('like_count')),
                    'timestamp': unified_timestamp(replies.get('ctime_text')),
                    'author_is_uploader': bool(traverse_obj(replies, ('member', 'type'))),
                }
                if replies.get('count'):
                    yield from self._get_comments_reply(replies.get('rpid'), display_id=video_id)

            if traverse_obj(comment_api_raw_data, ('data', 'cursor', 'is_end')):
                break

    def _real_extract(self, url):
        season_id, ep_id, aid = self._match_valid_url(url).group('season_id', 'ep_id', 'aid')
        video_id = ep_id or aid
        chapters = None

        if ep_id:
            intro_ending_json = self._call_api(
                f'/web/v2/ogv/play/episode?episode_id={ep_id}&platform=web',
                video_id, fatal=False) or {}
            if intro_ending_json.get('skip'):
                # FIXME: start time and end time seems a bit off a few second even it corrext based on ogv.*.js
                # ref: https://p.bstarstatic.com/fe-static/bstar-web-new/assets/ogv.2b147442.js
                chapters = [{
                    'start_time': float_or_none(traverse_obj(intro_ending_json, ('skip', 'opening_start_time')), 1000),
                    'end_time': float_or_none(traverse_obj(intro_ending_json, ('skip', 'opening_end_time')), 1000),
                    'title': 'Intro'
                }, {
                    'start_time': float_or_none(traverse_obj(intro_ending_json, ('skip', 'ending_start_time')), 1000),
                    'end_time': float_or_none(traverse_obj(intro_ending_json, ('skip', 'ending_end_time')), 1000),
                    'title': 'Outro'
                }]

        return {
            'id': video_id,
            **self._extract_video_metadata(url, video_id, season_id),
            'formats': self._get_formats(ep_id=ep_id, aid=aid),
            'subtitles': self.extract_subtitles(ep_id=ep_id, aid=aid),
            'chapters': chapters,
            '__post_extractor': self.extract_comments(video_id, ep_id)
        }


class BiliIntlSeriesIE(BiliIntlBaseIE):
    IE_NAME = 'biliIntl:series'
    _VALID_URL = r'https?://(?:www\.)?bili(?:bili\.tv|intl\.com)/(?:[a-zA-Z]{2}/)?(?:play|media)/(?P<id>\d+)/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://www.bilibili.tv/en/play/34613',
        'playlist_mincount': 15,
        'info_dict': {
            'id': '34613',
            'title': 'TONIKAWA: Over the Moon For You',
            'description': 'md5:297b5a17155eb645e14a14b385ab547e',
            'categories': ['Slice of life', 'Comedy', 'Romance'],
            'thumbnail': r're:^https://pic\.bstarstatic\.com/ogv/.+\.png$',
            'view_count': int,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.bilibili.tv/en/media/1048837',
        'info_dict': {
            'id': '1048837',
            'title': 'SPY×FAMILY',
            'description': 'md5:b4434eb1a9a97ad2bccb779514b89f17',
            'categories': ['Adventure', 'Action', 'Comedy'],
            'thumbnail': r're:^https://pic\.bstarstatic\.com/ogv/.+\.jpg$',
            'view_count': int,
        },
        'playlist_mincount': 25,
    }, {
        'url': 'https://www.biliintl.com/en/play/34613',
        'only_matching': True,
    }, {
        'url': 'https://www.biliintl.com/EN/play/34613',
        'only_matching': True,
    }]

    def _entries(self, series_id):
        series_json = self._call_api(f'/web/v2/ogv/play/episodes?season_id={series_id}&platform=web', series_id)
        for episode in traverse_obj(series_json, ('sections', ..., 'episodes', ...), expected_type=dict):
            episode_id = str(episode['episode_id'])
            yield self.url_result(smuggle_url(
                BiliIntlIE._make_url(episode_id, series_id),
                self._parse_video_metadata(episode)
            ), BiliIntlIE, episode_id)

    def _real_extract(self, url):
        series_id = self._match_id(url)
        series_info = self._call_api(f'/web/v2/ogv/play/season_info?season_id={series_id}&platform=web', series_id).get('season') or {}
        return self.playlist_result(
            self._entries(series_id), series_id, series_info.get('title'), series_info.get('description'),
            categories=traverse_obj(series_info, ('styles', ..., 'title'), expected_type=str_or_none),
            thumbnail=url_or_none(series_info.get('horizontal_cover')), view_count=parse_count(series_info.get('view')))


class BiliLiveIE(InfoExtractor):
    _VALID_URL = r'https?://live.bilibili.com/(?:blanc/)?(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://live.bilibili.com/196',
        'info_dict': {
            'id': '33989',
            'description': "周六杂谈回，其他时候随机游戏。 | \n录播：@下播型泛式录播组。 | \n直播通知群（全员禁言）：666906670，902092584，59971⑧481 （功能一样，别多加）",
            'ext': 'flv',
            'title': "太空狼人杀联动，不被爆杀就算赢",
            'thumbnail': "https://i0.hdslb.com/bfs/live/new_room_cover/e607bc1529057ef4b332e1026e62cf46984c314d.jpg",
            'timestamp': 1650802769,
        },
        'skip': 'not live'
    }, {
        'url': 'https://live.bilibili.com/196?broadcast_type=0&is_room_feed=1?spm_id_from=333.999.space_home.strengthen_live_card.click',
        'only_matching': True
    }, {
        'url': 'https://live.bilibili.com/blanc/196',
        'only_matching': True
    }]

    _FORMATS = {
        80: {'format_id': 'low', 'format_note': '流畅'},
        150: {'format_id': 'high_res', 'format_note': '高清'},
        250: {'format_id': 'ultra_high_res', 'format_note': '超清'},
        400: {'format_id': 'blue_ray', 'format_note': '蓝光'},
        10000: {'format_id': 'source', 'format_note': '原画'},
        20000: {'format_id': '4K', 'format_note': '4K'},
        30000: {'format_id': 'dolby', 'format_note': '杜比'},
    }

    _quality = staticmethod(qualities(list(_FORMATS)))

    def _call_api(self, path, room_id, query):
        api_result = self._download_json(f'https://api.live.bilibili.com/{path}', room_id, query=query)
        if api_result.get('code') != 0:
            raise ExtractorError(api_result.get('message') or 'Unable to download JSON metadata')
        return api_result.get('data') or {}

    def _parse_formats(self, qn, fmt):
        for codec in fmt.get('codec') or []:
            if codec.get('current_qn') != qn:
                continue
            for url_info in codec['url_info']:
                yield {
                    'url': f'{url_info["host"]}{codec["base_url"]}{url_info["extra"]}',
                    'ext': fmt.get('format_name'),
                    'vcodec': codec.get('codec_name'),
                    'quality': self._quality(qn),
                    **self._FORMATS[qn],
                }

    def _real_extract(self, url):
        room_id = self._match_id(url)
        room_data = self._call_api('room/v1/Room/get_info', room_id, {'id': room_id})
        if room_data.get('live_status') == 0:
            raise ExtractorError('Streamer is not live', expected=True)

        formats = []
        for qn in self._FORMATS.keys():
            stream_data = self._call_api('xlive/web-room/v2/index/getRoomPlayInfo', room_id, {
                'room_id': room_id,
                'qn': qn,
                'codec': '0,1',
                'format': '0,2',
                'mask': '0',
                'no_playurl': '0',
                'platform': 'web',
                'protocol': '0,1',
            })
            for fmt in traverse_obj(stream_data, ('playurl_info', 'playurl', 'stream', ..., 'format', ...)) or []:
                formats.extend(self._parse_formats(qn, fmt))

        return {
            'id': room_id,
            'title': room_data.get('title'),
            'description': room_data.get('description'),
            'thumbnail': room_data.get('user_cover'),
            'timestamp': stream_data.get('live_time'),
            'formats': formats,
            'is_live': True,
            'http_headers': {
                'Referer': url,
            },
        }
