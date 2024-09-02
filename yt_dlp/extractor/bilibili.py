import base64
import functools
import hashlib
import itertools
import json
import math
import re
import time
import urllib.parse
import uuid

from .common import InfoExtractor, SearchInfoExtractor
from ..dependencies import Cryptodome
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    GeoRestrictedError,
    InAdvancePagedList,
    OnDemandPagedList,
    bool_or_none,
    clean_html,
    determine_ext,
    filter_dict,
    float_or_none,
    format_field,
    get_element_by_class,
    int_or_none,
    join_nonempty,
    make_archive_id,
    merge_dicts,
    mimetype2ext,
    parse_count,
    parse_qs,
    parse_resolution,
    qualities,
    smuggle_url,
    srt_subtitles_timecode,
    str_or_none,
    traverse_obj,
    unified_timestamp,
    unsmuggle_url,
    url_or_none,
    urlencode_postdata,
    variadic,
)


class BilibiliBaseIE(InfoExtractor):
    _FORMAT_ID_RE = re.compile(r'-(\d+)\.m4s\?')
    _WBI_KEY_CACHE_TIMEOUT = 30  # exact expire timeout is unclear, use 30s for one session
    _wbi_key_cache = {}

    @property
    def is_logged_in(self):
        return bool(self._get_cookies('https://api.bilibili.com').get('SESSDATA'))

    def _check_missing_formats(self, play_info, formats):
        parsed_qualities = set(traverse_obj(formats, (..., 'quality')))
        missing_formats = join_nonempty(*[
            traverse_obj(fmt, 'new_description', 'display_desc', 'quality')
            for fmt in traverse_obj(play_info, (
                'support_formats', lambda _, v: v['quality'] not in parsed_qualities))], delim=', ')
        if missing_formats:
            self.to_screen(
                f'Format(s) {missing_formats} are missing; you have to login or '
                f'become a premium member to download them. {self._login_hint()}')

    def extract_formats(self, play_info):
        format_names = {
            r['quality']: traverse_obj(r, 'new_description', 'display_desc')
            for r in traverse_obj(play_info, ('support_formats', lambda _, v: v['quality']))
        }

        audios = traverse_obj(play_info, ('dash', (None, 'dolby'), 'audio', ..., {dict}))
        flac_audio = traverse_obj(play_info, ('dash', 'flac', 'audio'))
        if flac_audio:
            audios.append(flac_audio)
        formats = [{
            'url': traverse_obj(audio, 'baseUrl', 'base_url', 'url'),
            'ext': mimetype2ext(traverse_obj(audio, 'mimeType', 'mime_type')),
            'acodec': traverse_obj(audio, ('codecs', {str.lower})),
            'vcodec': 'none',
            'tbr': float_or_none(audio.get('bandwidth'), scale=1000),
            'filesize': int_or_none(audio.get('size')),
            'format_id': str_or_none(audio.get('id')),
        } for audio in audios]

        formats.extend({
            'url': traverse_obj(video, 'baseUrl', 'base_url', 'url'),
            'ext': mimetype2ext(traverse_obj(video, 'mimeType', 'mime_type')),
            'fps': float_or_none(traverse_obj(video, 'frameRate', 'frame_rate')),
            'width': int_or_none(video.get('width')),
            'height': int_or_none(video.get('height')),
            'vcodec': video.get('codecs'),
            'acodec': 'none' if audios else None,
            'dynamic_range': {126: 'DV', 125: 'HDR10'}.get(int_or_none(video.get('id'))),
            'tbr': float_or_none(video.get('bandwidth'), scale=1000),
            'filesize': int_or_none(video.get('size')),
            'quality': int_or_none(video.get('id')),
            'format_id': traverse_obj(
                video, (('baseUrl', 'base_url'), {self._FORMAT_ID_RE.search}, 1),
                ('id', {str_or_none}), get_all=False),
            'format': format_names.get(video.get('id')),
        } for video in traverse_obj(play_info, ('dash', 'video', ...)))

        if formats:
            self._check_missing_formats(play_info, formats)

        fragments = traverse_obj(play_info, ('durl', lambda _, v: url_or_none(v['url']), {
            'url': ('url', {url_or_none}),
            'duration': ('length', {functools.partial(float_or_none, scale=1000)}),
            'filesize': ('size', {int_or_none}),
        }))
        if fragments:
            formats.append({
                'url': fragments[0]['url'],
                'filesize': sum(traverse_obj(fragments, (..., 'filesize'))),
                **({
                    'fragments': fragments,
                    'protocol': 'http_dash_segments',
                } if len(fragments) > 1 else {}),
                **traverse_obj(play_info, {
                    'quality': ('quality', {int_or_none}),
                    'format_id': ('quality', {str_or_none}),
                    'format_note': ('quality', {lambda x: format_names.get(x)}),
                    'duration': ('timelength', {functools.partial(float_or_none, scale=1000)}),
                }),
                **parse_resolution(format_names.get(play_info.get('quality'))),
            })
        return formats

    def _get_wbi_key(self, video_id):
        if time.time() < self._wbi_key_cache.get('ts', 0) + self._WBI_KEY_CACHE_TIMEOUT:
            return self._wbi_key_cache['key']

        session_data = self._download_json(
            'https://api.bilibili.com/x/web-interface/nav', video_id, note='Downloading wbi sign')

        lookup = ''.join(traverse_obj(session_data, (
            'data', 'wbi_img', ('img_url', 'sub_url'),
            {lambda x: x.rpartition('/')[2].partition('.')[0]})))

        # from getMixinKey() in the vendor js
        mixin_key_enc_tab = [
            46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
            33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
            61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
            36, 20, 34, 44, 52,
        ]

        self._wbi_key_cache.update({
            'key': ''.join(lookup[i] for i in mixin_key_enc_tab)[:32],
            'ts': time.time(),
        })
        return self._wbi_key_cache['key']

    def _sign_wbi(self, params, video_id):
        params['wts'] = round(time.time())
        params = {
            k: ''.join(filter(lambda char: char not in "!'()*", str(v)))
            for k, v in sorted(params.items())
        }
        query = urllib.parse.urlencode(params)
        params['w_rid'] = hashlib.md5(f'{query}{self._get_wbi_key(video_id)}'.encode()).hexdigest()
        return params

    def _download_playinfo(self, bvid, cid, headers=None, qn=None):
        params = {'bvid': bvid, 'cid': cid, 'fnval': 4048}
        if qn:
            params['qn'] = qn
        return self._download_json(
            'https://api.bilibili.com/x/player/wbi/playurl', bvid,
            query=self._sign_wbi(params, bvid), headers=headers,
            note=f'Downloading video formats for cid {cid} {qn or ""}')['data']

    def json2srt(self, json_data):
        srt_data = ''
        for idx, line in enumerate(json_data.get('body') or []):
            srt_data += (f'{idx + 1}\n'
                         f'{srt_subtitles_timecode(line["from"])} --> {srt_subtitles_timecode(line["to"])}\n'
                         f'{line["content"]}\n\n')
        return srt_data

    def _get_subtitles(self, video_id, cid, aid=None):
        subtitles = {
            'danmaku': [{
                'ext': 'xml',
                'url': f'https://comment.bilibili.com/{cid}.xml',
            }],
        }

        video_info = self._download_json(
            'https://api.bilibili.com/x/player/v2', video_id,
            query={'aid': aid, 'cid': cid} if aid else {'bvid': video_id, 'cid': cid},
            note=f'Extracting subtitle info {cid}')
        if traverse_obj(video_info, ('data', 'need_login_subtitle')):
            self.report_warning(
                f'Subtitles are only available when logged in. {self._login_hint()}', only_once=True)
        for s in traverse_obj(video_info, (
                'data', 'subtitle', 'subtitles', lambda _, v: v['subtitle_url'] and v['lan'])):
            subtitles.setdefault(s['lan'], []).append({
                'ext': 'srt',
                'data': self.json2srt(self._download_json(s['subtitle_url'], video_id)),
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

    def _get_episodes_from_season(self, ss_id, url):
        season_info = self._download_json(
            'https://api.bilibili.com/pgc/web/season/section', ss_id,
            note='Downloading season info', query={'season_id': ss_id},
            headers={'Referer': url, **self.geo_verification_headers()})

        for entry in traverse_obj(season_info, (
                'result', 'main_section', 'episodes',
                lambda _, v: url_or_none(v['share_url']) and v['id'])):
            yield self.url_result(entry['share_url'], BiliBiliBangumiIE, str_or_none(entry.get('id')))

    def _get_divisions(self, video_id, graph_version, edges, edge_id, cid_edges=None):
        cid_edges = cid_edges or {}
        division_data = self._download_json(
            'https://api.bilibili.com/x/stein/edgeinfo_v2', video_id,
            query={'graph_version': graph_version, 'edge_id': edge_id, 'bvid': video_id},
            note=f'Extracting divisions from edge {edge_id}')
        edges.setdefault(edge_id, {}).update(
            traverse_obj(division_data, ('data', 'story_list', lambda _, v: v['edge_id'] == edge_id, {
                'title': ('title', {str}),
                'cid': ('cid', {int_or_none}),
            }), get_all=False))

        edges[edge_id].update(traverse_obj(division_data, ('data', {
            'title': ('title', {str}),
            'choices': ('edges', 'questions', ..., 'choices', ..., {
                'edge_id': ('id', {int_or_none}),
                'cid': ('cid', {int_or_none}),
                'text': ('option', {str}),
            }),
        })))
        # use dict to combine edges that use the same video section (same cid)
        cid_edges.setdefault(edges[edge_id]['cid'], {})[edge_id] = edges[edge_id]
        for choice in traverse_obj(edges, (edge_id, 'choices', ...)):
            if choice['edge_id'] not in edges:
                edges[choice['edge_id']] = {'cid': choice['cid']}
                self._get_divisions(video_id, graph_version, edges, choice['edge_id'], cid_edges=cid_edges)
        return cid_edges

    def _get_interactive_entries(self, video_id, cid, metainfo, headers=None):
        graph_version = traverse_obj(
            self._download_json(
                'https://api.bilibili.com/x/player/wbi/v2', video_id,
                'Extracting graph version', query={'bvid': video_id, 'cid': cid}, headers=headers),
            ('data', 'interaction', 'graph_version', {int_or_none}))
        cid_edges = self._get_divisions(video_id, graph_version, {1: {'cid': cid}}, 1)
        for cid, edges in cid_edges.items():
            play_info = self._download_playinfo(video_id, cid, headers=headers)
            yield {
                **metainfo,
                'id': f'{video_id}_{cid}',
                'title': f'{metainfo.get("title")} - {next(iter(edges.values())).get("title")}',
                'formats': self.extract_formats(play_info),
                'description': f'{json.dumps(edges, ensure_ascii=False)}\n{metainfo.get("description", "")}',
                'duration': float_or_none(play_info.get('timelength'), scale=1000),
                'subtitles': self.extract_subtitles(video_id, cid),
            }


class BiliBiliIE(BilibiliBaseIE):
    _VALID_URL = r'https?://(?:www\.)?bilibili\.com/(?:video/|festival/[^/?#]+\?(?:[^#]*&)?bvid=)[aAbB][vV](?P<id>[^/?#&]+)'

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
            '_old_archive_ids': ['bilibili 8903802_part1'],
        },
    }, {
        'note': 'old av URL version',
        'url': 'http://www.bilibili.com/video/av1074402/',
        'info_dict': {
            'id': 'BV11x411K7CN',
            'ext': 'mp4',
            'title': '【金坷垃】金泡沫',
            'uploader': '菊子桑',
            'uploader_id': '156160',
            'duration': 308.36,
            'upload_date': '20140420',
            'timestamp': 1397983878,
            'description': 'md5:ce18c2a2d2193f0df2917d270f2e5923',
            'like_count': int,
            'comment_count': int,
            'view_count': int,
            'tags': list,
            'thumbnail': r're:^https?://.*\.(jpg|jpeg)$',
            '_old_archive_ids': ['bilibili 1074402_part1'],
        },
        'params': {'skip_download': True},
    }, {
        'note': 'Anthology',
        'url': 'https://www.bilibili.com/video/BV1bK411W797',
        'info_dict': {
            'id': 'BV1bK411W797',
            'title': '物语中的人物是如何吐槽自己的OP的',
        },
        'playlist_count': 18,
        'playlist': [{
            'info_dict': {
                'id': 'BV1bK411W797_p1',
                'ext': 'mp4',
                'title': '物语中的人物是如何吐槽自己的OP的 p01 Staple Stable/战场原+羽川',
                'tags': 'count:10',
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
                '_old_archive_ids': ['bilibili 498159642_part1'],
            },
        }],
    }, {
        'note': 'Specific page of Anthology',
        'url': 'https://www.bilibili.com/video/BV1bK411W797?p=1',
        'info_dict': {
            'id': 'BV1bK411W797_p1',
            'ext': 'mp4',
            'title': '物语中的人物是如何吐槽自己的OP的 p01 Staple Stable/战场原+羽川',
            'tags': 'count:10',
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
            '_old_archive_ids': ['bilibili 498159642_part1'],
        },
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
            '_old_archive_ids': ['bilibili 8903802_part1'],
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
            '_old_archive_ids': ['bilibili 463665680_part1'],
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
            '_old_archive_ids': ['bilibili 893839363_part1'],
        },
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
            '_old_archive_ids': ['bilibili 778246196_part1'],
        },
    }, {
        'note': 'legacy flv/mp4 video',
        'url': 'https://www.bilibili.com/video/BV1ms411Q7vw/?p=4',
        'info_dict': {
            'id': 'BV1ms411Q7vw_p4',
            'title': '[搞笑]【动画】云南方言快乐生产线出品 p04 新烧包谷之漫游桃花岛',
            'timestamp': 1458222815,
            'upload_date': '20160317',
            'description': '云南方言快乐生产线出品',
            'duration': float,
            'uploader': '一笑颠天',
            'uploader_id': '3916081',
            'view_count': int,
            'comment_count': int,
            'like_count': int,
            'tags': list,
            'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)$',
            '_old_archive_ids': ['bilibili 4120229_part4'],
        },
        'params': {'extractor_args': {'bilibili': {'prefer_multi_flv': ['32']}}},
        'playlist_count': 19,
        'playlist': [{
            'info_dict': {
                'id': 'BV1ms411Q7vw_p4_0',
                'ext': 'flv',
                'title': '[搞笑]【动画】云南方言快乐生产线出品 p04 新烧包谷之漫游桃花岛',
                'duration': 399.102,
            },
        }],
    }, {
        'note': 'legacy mp4-only video',
        'url': 'https://www.bilibili.com/video/BV1nx411u79K',
        'info_dict': {
            'id': 'BV1nx411u79K',
            'ext': 'mp4',
            'title': '【练习室】201603声乐练习《No Air》with VigoVan',
            'timestamp': 1508893551,
            'upload_date': '20171025',
            'description': '@ZERO-G伯远\n声乐练习 《No Air》with Vigo Van',
            'duration': 80.384,
            'uploader': '伯远',
            'uploader_id': '10584494',
            'comment_count': int,
            'view_count': int,
            'like_count': int,
            'tags': list,
            'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)$',
            '_old_archive_ids': ['bilibili 15700301_part1'],
        },
    }, {
        'note': 'interactive/split-path video',
        'url': 'https://www.bilibili.com/video/BV1af4y1H7ga/',
        'info_dict': {
            'id': 'BV1af4y1H7ga',
            'title': '【互动游戏】花了大半年时间做的自我介绍~请查收！！',
            'timestamp': 1630500414,
            'upload_date': '20210901',
            'description': 'md5:01113e39ab06e28042d74ac356a08786',
            'tags': list,
            'uploader': '钉宫妮妮Ninico',
            'duration': 1503,
            'uploader_id': '8881297',
            'comment_count': int,
            'view_count': int,
            'like_count': int,
            'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)$',
            '_old_archive_ids': ['bilibili 292734508_part1'],
        },
        'playlist_count': 33,
        'playlist': [{
            'info_dict': {
                'id': 'BV1af4y1H7ga_400950101',
                'ext': 'mp4',
                'title': '【互动游戏】花了大半年时间做的自我介绍~请查收！！ - 听见猫猫叫~',
                'timestamp': 1630500414,
                'upload_date': '20210901',
                'description': 'md5:db66ac7a2813a94b8291dbce990cc5b2',
                'tags': list,
                'uploader': '钉宫妮妮Ninico',
                'duration': 11.605,
                'uploader_id': '8881297',
                'comment_count': int,
                'view_count': int,
                'like_count': int,
                'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)$',
                '_old_archive_ids': ['bilibili 292734508_part1'],
            },
        }],
    }, {
        'note': '301 redirect to bangumi link',
        'url': 'https://www.bilibili.com/video/BV1TE411f7f1',
        'info_dict': {
            'id': '288525',
            'title': '李永乐老师 钱学森弹道和乘波体飞行器是什么？',
            'ext': 'mp4',
            'series': '我和我的祖国',
            'series_id': '4780',
            'season': '幕后纪实',
            'season_id': '28609',
            'season_number': 1,
            'episode': '钱学森弹道和乘波体飞行器是什么？',
            'episode_id': '288525',
            'episode_number': 105,
            'duration': 1183.957,
            'timestamp': 1571648124,
            'upload_date': '20191021',
            'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)$',
        },
    }, {
        'note': 'video has subtitles, which requires login',
        'url': 'https://www.bilibili.com/video/BV12N4y1M7rh',
        'info_dict': {
            'id': 'BV12N4y1M7rh',
            'ext': 'mp4',
            'title': 'md5:96e8bb42c2b432c0d4ce3434a61479c1',
            'tags': list,
            'description': 'md5:afde2b7ba9025c01d9e3dde10de221e4',
            'duration': 313.557,
            'upload_date': '20220709',
            'uploader': '小夫太渴',
            'timestamp': 1657347907,
            'uploader_id': '1326814124',
            'comment_count': int,
            'view_count': int,
            'like_count': int,
            'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)$',
            'subtitles': 'count:2',  # login required for CC subtitle
            '_old_archive_ids': ['bilibili 898179753_part1'],
        },
        'params': {'listsubtitles': True},
        'skip': 'login required for subtitle',
    }, {
        'url': 'https://www.bilibili.com/video/BV1jL41167ZG/',
        'info_dict': {
            'id': 'BV1jL41167ZG',
            'title': '一场大火引发的离奇死亡！古典推理经典短篇集《不可能犯罪诊断书》！',
            'ext': 'mp4',
        },
        'skip': 'supporter-only video',
    }, {
        'url': 'https://www.bilibili.com/video/BV1Ks411f7aQ/',
        'info_dict': {
            'id': 'BV1Ks411f7aQ',
            'title': '【BD1080P】狼与香辛料I【华盟】',
            'ext': 'mp4',
        },
        'skip': 'login required',
    }, {
        'url': 'https://www.bilibili.com/video/BV1GJ411x7h7/',
        'info_dict': {
            'id': 'BV1GJ411x7h7',
            'title': '【官方 MV】Never Gonna Give You Up - Rick Astley',
            'ext': 'mp4',
        },
        'skip': 'geo-restricted',
    }, {
        'note': 'has - in the last path segment of the url',
        'url': 'https://www.bilibili.com/festival/bh3-7th?bvid=BV1tr4y1f7p2&',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        headers = self.geo_verification_headers()
        webpage, urlh = self._download_webpage_handle(url, video_id, headers=headers)
        if not self._match_valid_url(urlh.url):
            return self.url_result(urlh.url)

        headers['Referer'] = url

        initial_state = self._search_json(r'window\.__INITIAL_STATE__\s*=', webpage, 'initial state', video_id)
        is_festival = 'videoData' not in initial_state
        if is_festival:
            video_data = initial_state['videoInfo']
        else:
            play_info_obj = self._search_json(
                r'window\.__playinfo__\s*=', webpage, 'play info', video_id, fatal=False)
            if not play_info_obj:
                if traverse_obj(initial_state, ('error', 'trueCode')) == -403:
                    self.raise_login_required()
                if traverse_obj(initial_state, ('error', 'trueCode')) == -404:
                    raise ExtractorError(
                        'This video may be deleted or geo-restricted. '
                        'You might want to try a VPN or a proxy server (with --proxy)', expected=True)
            play_info = traverse_obj(play_info_obj, ('data', {dict}))
            if not play_info:
                if traverse_obj(play_info_obj, 'code') == 87007:
                    toast = get_element_by_class('tips-toast', webpage) or ''
                    msg = clean_html(
                        f'{get_element_by_class("belongs-to", toast) or ""}，'
                        + (get_element_by_class('level', toast) or ''))
                    raise ExtractorError(
                        f'This is a supporter-only video: {msg}. {self._login_hint()}', expected=True)
                raise ExtractorError('Failed to extract play info')
            video_data = initial_state['videoData']

        video_id, title = video_data['bvid'], video_data.get('title')

        # Bilibili anthologies are similar to playlists but all videos share the same video ID as the anthology itself.
        page_list_json = not is_festival and traverse_obj(
            self._download_json(
                'https://api.bilibili.com/x/player/pagelist', video_id,
                fatal=False, query={'bvid': video_id, 'jsonp': 'jsonp'},
                note='Extracting videos in anthology', headers=headers),
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
            play_info = self._download_playinfo(video_id, cid, headers=headers)

            festival_info = traverse_obj(initial_state, {
                'uploader': ('videoInfo', 'upName'),
                'uploader_id': ('videoInfo', 'upMid', {str_or_none}),
                'like_count': ('videoStatus', 'like', {int_or_none}),
                'thumbnail': ('sectionEpisodes', lambda _, v: v['bvid'] == video_id, 'cover'),
            }, get_all=False)

        metainfo = {
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
            '_old_archive_ids': [make_archive_id(self, old_video_id)] if old_video_id else None,
            'title': title,
            'http_headers': {'Referer': url},
        }

        is_interactive = traverse_obj(video_data, ('rights', 'is_stein_gate'))
        if is_interactive:
            return self.playlist_result(
                self._get_interactive_entries(video_id, cid, metainfo, headers=headers), **metainfo,
                duration=traverse_obj(initial_state, ('videoData', 'duration', {int_or_none})),
                __post_extractor=self.extract_comments(aid))
        else:
            formats = self.extract_formats(play_info)

            if not traverse_obj(play_info, ('dash')):
                # we only have legacy formats and need additional work
                has_qn = lambda x: x in traverse_obj(formats, (..., 'quality'))
                for qn in traverse_obj(play_info, ('accept_quality', lambda _, v: not has_qn(v), {int})):
                    formats.extend(traverse_obj(
                        self.extract_formats(self._download_playinfo(video_id, cid, headers=headers, qn=qn)),
                        lambda _, v: not has_qn(v['quality'])))
                self._check_missing_formats(play_info, formats)
                flv_formats = traverse_obj(formats, lambda _, v: v['fragments'])
                if flv_formats and len(flv_formats) < len(formats):
                    # Flv and mp4 are incompatible due to `multi_video` workaround, so drop one
                    if not self._configuration_arg('prefer_multi_flv'):
                        dropped_fmts = ', '.join(
                            f'{f.get("format_note")} ({f.get("format_id")})' for f in flv_formats)
                        formats = traverse_obj(formats, lambda _, v: not v.get('fragments'))
                        if dropped_fmts:
                            self.to_screen(
                                f'Dropping incompatible flv format(s) {dropped_fmts} since mp4 is available. '
                                'To extract flv, pass --extractor-args "bilibili:prefer_multi_flv"')
                    else:
                        formats = traverse_obj(
                            # XXX: Filtering by extractor-arg is for testing purposes
                            formats, lambda _, v: v['quality'] == int(self._configuration_arg('prefer_multi_flv')[0]),
                        ) or [max(flv_formats, key=lambda x: x['quality'])]

            if traverse_obj(formats, (0, 'fragments')):
                # We have flv formats, which are individual short videos with their own timestamps and metainfo
                # Binary concatenation corrupts their timestamps, so we need a `multi_video` workaround
                return {
                    **metainfo,
                    '_type': 'multi_video',
                    'entries': [{
                        'id': f'{metainfo["id"]}_{idx}',
                        'title': metainfo['title'],
                        'http_headers': metainfo['http_headers'],
                        'formats': [{
                            **fragment,
                            'format_id': formats[0].get('format_id'),
                        }],
                        'subtitles': self.extract_subtitles(video_id, cid) if idx == 0 else None,
                        '__post_extractor': self.extract_comments(aid) if idx == 0 else None,
                    } for idx, fragment in enumerate(formats[0]['fragments'])],
                    'duration': float_or_none(play_info.get('timelength'), scale=1000),
                }
            else:
                return {
                    **metainfo,
                    'formats': formats,
                    'duration': float_or_none(play_info.get('timelength'), scale=1000),
                    'chapters': self._get_chapters(aid, cid),
                    'subtitles': self.extract_subtitles(video_id, cid),
                    '__post_extractor': self.extract_comments(aid),
                }


class BiliBiliBangumiIE(BilibiliBaseIE):
    _VALID_URL = r'https?://(?:www\.)?bilibili\.com/bangumi/play/ep(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://www.bilibili.com/bangumi/play/ep21495/',
        'info_dict': {
            'id': '21495',
            'ext': 'mp4',
            'series': '悠久之翼',
            'series_id': '774',
            'season': '第二季',
            'season_id': '1182',
            'season_number': 2,
            'episode': 'forever／ef',
            'episode_id': '21495',
            'episode_number': 12,
            'title': '12 forever／ef',
            'duration': 1420.791,
            'timestamp': 1320412200,
            'upload_date': '20111104',
            'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)$',
        },
    }, {
        'url': 'https://www.bilibili.com/bangumi/play/ep267851',
        'info_dict': {
            'id': '267851',
            'ext': 'mp4',
            'series': '鬼灭之刃',
            'series_id': '4358',
            'season': '立志篇',
            'season_id': '26801',
            'season_number': 1,
            'episode': '残酷',
            'episode_id': '267851',
            'episode_number': 1,
            'title': '1 残酷',
            'duration': 1425.256,
            'timestamp': 1554566400,
            'upload_date': '20190406',
            'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)$',
        },
        'skip': 'Geo-restricted',
    }, {
        'note': 'a making-of which falls outside main section',
        'url': 'https://www.bilibili.com/bangumi/play/ep345120',
        'info_dict': {
            'id': '345120',
            'ext': 'mp4',
            'series': '鬼灭之刃',
            'series_id': '4358',
            'season': '立志篇',
            'season_id': '26801',
            'season_number': 1,
            'episode': '炭治郎篇',
            'episode_id': '345120',
            'episode_number': 27,
            'title': '#1 炭治郎篇',
            'duration': 1922.129,
            'timestamp': 1602853860,
            'upload_date': '20201016',
            'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)$',
        },
    }]

    def _real_extract(self, url):
        episode_id = self._match_id(url)
        headers = self.geo_verification_headers()
        webpage = self._download_webpage(url, episode_id, headers=headers)

        if '您所在的地区无法观看本片' in webpage:
            raise GeoRestrictedError('This video is restricted')
        elif '正在观看预览，大会员免费看全片' in webpage:
            self.raise_login_required('This video is for premium members only')

        headers['Referer'] = url
        play_info = self._download_json(
            'https://api.bilibili.com/pgc/player/web/v2/playurl', episode_id,
            'Extracting episode', query={'fnval': '4048', 'ep_id': episode_id},
            headers=headers)
        premium_only = play_info.get('code') == -10403
        play_info = traverse_obj(play_info, ('result', 'video_info', {dict})) or {}

        formats = self.extract_formats(play_info)
        if not formats and (premium_only or '成为大会员抢先看' in webpage or '开通大会员观看' in webpage):
            self.raise_login_required('This video is for premium members only')

        bangumi_info = self._download_json(
            'https://api.bilibili.com/pgc/view/web/season', episode_id, 'Get episode details',
            query={'ep_id': episode_id}, headers=headers)['result']

        episode_number, episode_info = next((
            (idx, ep) for idx, ep in enumerate(traverse_obj(
                bangumi_info, (('episodes', ('section', ..., 'episodes')), ..., {dict})), 1)
            if str_or_none(ep.get('id')) == episode_id), (1, {}))

        season_id = bangumi_info.get('season_id')
        season_number, season_title = season_id and next((
            (idx + 1, e.get('season_title')) for idx, e in enumerate(
                traverse_obj(bangumi_info, ('seasons', ...)))
            if e.get('season_id') == season_id
        ), (None, None))

        aid = episode_info.get('aid')

        return {
            'id': episode_id,
            'formats': formats,
            **traverse_obj(bangumi_info, {
                'series': ('series', 'series_title', {str}),
                'series_id': ('series', 'series_id', {str_or_none}),
                'thumbnail': ('square_cover', {url_or_none}),
            }),
            **traverse_obj(episode_info, {
                'episode': ('long_title', {str}),
                'episode_number': ('title', {int_or_none}, {lambda x: x or episode_number}),
                'timestamp': ('pub_time', {int_or_none}),
                'title': {lambda v: v and join_nonempty('title', 'long_title', delim=' ', from_dict=v)},
            }),
            'episode_id': episode_id,
            'season': str_or_none(season_title),
            'season_id': str_or_none(season_id),
            'season_number': season_number,
            'duration': float_or_none(play_info.get('timelength'), scale=1000),
            'subtitles': self.extract_subtitles(episode_id, episode_info.get('cid'), aid=aid),
            '__post_extractor': self.extract_comments(aid),
            'http_headers': {'Referer': url},
        }


class BiliBiliBangumiMediaIE(BilibiliBaseIE):
    _VALID_URL = r'https?://(?:www\.)?bilibili\.com/bangumi/media/md(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.bilibili.com/bangumi/media/md24097891',
        'info_dict': {
            'id': '24097891',
            'title': 'CAROLE & TUESDAY',
            'description': 'md5:42417ad33d1eaa1c93bfd2dd1626b829',
        },
        'playlist_mincount': 25,
    }, {
        'url': 'https://www.bilibili.com/bangumi/media/md1565/',
        'info_dict': {
            'id': '1565',
            'title': '攻壳机动队 S.A.C. 2nd GIG',
            'description': 'md5:46cac00bafd645b97f4d6df616fc576d',
        },
        'playlist_count': 26,
        'playlist': [{
            'info_dict': {
                'id': '68540',
                'ext': 'mp4',
                'series': '攻壳机动队',
                'series_id': '1077',
                'season': '第二季',
                'season_id': '1565',
                'season_number': 2,
                'episode': '再启动 REEMBODY',
                'episode_id': '68540',
                'episode_number': 1,
                'title': '1 再启动 REEMBODY',
                'duration': 1525.777,
                'timestamp': 1425074413,
                'upload_date': '20150227',
                'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)$',
            },
        }],
    }]

    def _real_extract(self, url):
        media_id = self._match_id(url)
        webpage = self._download_webpage(url, media_id)

        initial_state = self._search_json(
            r'window\.__INITIAL_STATE__\s*=', webpage, 'initial_state', media_id)
        ss_id = initial_state['mediaInfo']['season_id']

        return self.playlist_result(
            self._get_episodes_from_season(ss_id, url), media_id,
            **traverse_obj(initial_state, ('mediaInfo', {
                'title': ('title', {str}),
                'description': ('evaluate', {str}),
            })))


class BiliBiliBangumiSeasonIE(BilibiliBaseIE):
    _VALID_URL = r'(?x)https?://(?:www\.)?bilibili\.com/bangumi/play/ss(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.bilibili.com/bangumi/play/ss26801',
        'info_dict': {
            'id': '26801',
            'title': '鬼灭之刃',
            'description': 'md5:e2cc9848b6f69be6db79fc2a82d9661b',
        },
        'playlist_mincount': 26,
    }, {
        'url': 'https://www.bilibili.com/bangumi/play/ss2251',
        'info_dict': {
            'id': '2251',
            'title': '玲音',
            'description': 'md5:1fd40e3df4c08d4d9d89a6a34844bdc4',
        },
        'playlist_count': 13,
        'playlist': [{
            'info_dict': {
                'id': '50188',
                'ext': 'mp4',
                'series': '玲音',
                'series_id': '1526',
                'season': 'TV',
                'season_id': '2251',
                'season_number': 1,
                'episode': 'WEIRD',
                'episode_id': '50188',
                'episode_number': 1,
                'title': '1 WEIRD',
                'duration': 1436.992,
                'timestamp': 1343185080,
                'upload_date': '20120725',
                'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)$',
            },
        }],
    }]

    def _real_extract(self, url):
        ss_id = self._match_id(url)
        webpage = self._download_webpage(url, ss_id)
        metainfo = traverse_obj(
            self._search_json(r'<script[^>]+type="application/ld\+json"[^>]*>', webpage, 'info', ss_id),
            ('itemListElement', ..., {
                'title': ('name', {str}),
                'description': ('description', {str}),
            }), get_all=False)

        return self.playlist_result(self._get_episodes_from_season(ss_id, url), ss_id, **metainfo)


class BilibiliCheeseBaseIE(BilibiliBaseIE):
    _HEADERS = {'Referer': 'https://www.bilibili.com/'}

    def _extract_episode(self, season_info, ep_id):
        episode_info = traverse_obj(season_info, (
            'episodes', lambda _, v: v['id'] == int(ep_id)), get_all=False)
        aid, cid = episode_info['aid'], episode_info['cid']

        if traverse_obj(episode_info, 'ep_status') == -1:
            raise ExtractorError('This course episode is not yet available.', expected=True)
        if not traverse_obj(episode_info, 'playable'):
            self.raise_login_required('You need to purchase the course to download this episode')

        play_info = self._download_json(
            'https://api.bilibili.com/pugv/player/web/playurl', ep_id,
            query={'avid': aid, 'cid': cid, 'ep_id': ep_id, 'fnval': 16, 'fourk': 1},
            headers=self._HEADERS, note='Downloading playinfo')['data']

        return {
            'id': str_or_none(ep_id),
            'episode_id': str_or_none(ep_id),
            'formats': self.extract_formats(play_info),
            'extractor_key': BilibiliCheeseIE.ie_key(),
            'extractor': BilibiliCheeseIE.IE_NAME,
            'webpage_url': f'https://www.bilibili.com/cheese/play/ep{ep_id}',
            **traverse_obj(episode_info, {
                'episode': ('title', {str}),
                'title': {lambda v: v and join_nonempty('index', 'title', delim=' - ', from_dict=v)},
                'alt_title': ('subtitle', {str}),
                'duration': ('duration', {int_or_none}),
                'episode_number': ('index', {int_or_none}),
                'thumbnail': ('cover', {url_or_none}),
                'timestamp': ('release_date', {int_or_none}),
                'view_count': ('play', {int_or_none}),
            }),
            **traverse_obj(season_info, {
                'uploader': ('up_info', 'uname', {str}),
                'uploader_id': ('up_info', 'mid', {str_or_none}),
            }),
            'subtitles': self.extract_subtitles(ep_id, cid, aid=aid),
            '__post_extractor': self.extract_comments(aid),
            'http_headers': self._HEADERS,
        }

    def _download_season_info(self, query_key, video_id):
        return self._download_json(
            f'https://api.bilibili.com/pugv/view/web/season?{query_key}={video_id}', video_id,
            headers=self._HEADERS, note='Downloading season info')['data']


class BilibiliCheeseIE(BilibiliCheeseBaseIE):
    _VALID_URL = r'https?://(?:www\.)?bilibili\.com/cheese/play/ep(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.bilibili.com/cheese/play/ep229832',
        'info_dict': {
            'id': '229832',
            'ext': 'mp4',
            'title': '1 - 课程先导片',
            'alt_title': '视频课 · 3分41秒',
            'uploader': '马督工',
            'uploader_id': '316568752',
            'episode': '课程先导片',
            'episode_id': '229832',
            'episode_number': 1,
            'duration': 221,
            'timestamp': 1695549606,
            'upload_date': '20230924',
            'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)$',
            'view_count': int,
        },
    }]

    def _real_extract(self, url):
        ep_id = self._match_id(url)
        return self._extract_episode(self._download_season_info('ep_id', ep_id), ep_id)


class BilibiliCheeseSeasonIE(BilibiliCheeseBaseIE):
    _VALID_URL = r'https?://(?:www\.)?bilibili\.com/cheese/play/ss(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.bilibili.com/cheese/play/ss5918',
        'info_dict': {
            'id': '5918',
            'title': '【限时五折】新闻系学不到：马督工教你做自媒体',
            'description': '帮普通人建立世界模型，降低人与人的沟通门槛',
        },
        'playlist': [{
            'info_dict': {
                'id': '229832',
                'ext': 'mp4',
                'title': '1 - 课程先导片',
                'alt_title': '视频课 · 3分41秒',
                'uploader': '马督工',
                'uploader_id': '316568752',
                'episode': '课程先导片',
                'episode_id': '229832',
                'episode_number': 1,
                'duration': 221,
                'timestamp': 1695549606,
                'upload_date': '20230924',
                'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)$',
                'view_count': int,
            },
        }],
        'params': {'playlist_items': '1'},
    }, {
        'url': 'https://www.bilibili.com/cheese/play/ss5918',
        'info_dict': {
            'id': '5918',
            'title': '【限时五折】新闻系学不到：马督工教你做自媒体',
            'description': '帮普通人建立世界模型，降低人与人的沟通门槛',
        },
        'playlist_mincount': 5,
        'skip': 'paid video in list',
    }]

    def _get_cheese_entries(self, season_info):
        for ep_id in traverse_obj(season_info, ('episodes', lambda _, v: v['episode_can_view'], 'id')):
            yield self._extract_episode(season_info, ep_id)

    def _real_extract(self, url):
        season_id = self._match_id(url)
        season_info = self._download_season_info('season_id', season_id)

        return self.playlist_result(
            self._get_cheese_entries(season_info), season_id,
            **traverse_obj(season_info, {
                'title': ('title', {str}),
                'description': ('subtitle', {str}),
            }))


class BilibiliSpaceBaseIE(BilibiliBaseIE):
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
        'skip': 'login required',
    }, {
        'url': 'https://space.bilibili.com/313580179/video',
        'info_dict': {
            'id': '313580179',
        },
        'playlist_mincount': 92,
        'skip': 'login required',
    }]

    def _real_extract(self, url):
        playlist_id, is_video_url = self._match_valid_url(url).group('id', 'video')
        if not is_video_url:
            self.to_screen('A channel URL was given. Only the channel\'s videos will be downloaded. '
                           'To download audios, add a "/audio" to the URL')

        def fetch_page(page_idx):
            query = {
                'keyword': '',
                'mid': playlist_id,
                'order': traverse_obj(parse_qs(url), ('order', 0)) or 'pubdate',
                'order_avoided': 'true',
                'platform': 'web',
                'pn': page_idx + 1,
                'ps': 30,
                'tid': 0,
                'web_location': 1550101,
            }

            try:
                response = self._download_json(
                    'https://api.bilibili.com/x/space/wbi/arc/search', playlist_id,
                    query=self._sign_wbi(query, playlist_id),
                    note=f'Downloading space page {page_idx}', headers={'Referer': url})
            except ExtractorError as e:
                if isinstance(e.cause, HTTPError) and e.cause.status == 412:
                    raise ExtractorError(
                        'Request is blocked by server (412), please add cookies, wait and try later.', expected=True)
                raise
            status_code = response['code']
            if status_code == -401:
                raise ExtractorError(
                    'Request is blocked by server (401), please add cookies, wait and try later.', expected=True)
            elif status_code == -352 and not self.is_logged_in:
                self.raise_login_required('Request is rejected, you need to login to access playlist')
            elif status_code != 0:
                raise ExtractorError(f'Request failed ({status_code}): {response.get("message") or "Unknown error"}')
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


class BilibiliSpaceListBaseIE(BilibiliSpaceBaseIE):
    def _get_entries(self, page_data, bvid_keys, ending_key='bvid'):
        for bvid in traverse_obj(page_data, (*variadic(bvid_keys, (str, bytes, dict, set)), ..., ending_key, {str})):
            yield self.url_result(f'https://www.bilibili.com/video/{bvid}', BiliBiliIE, bvid)

    def _get_uploader(self, uid, playlist_id):
        webpage = self._download_webpage(f'https://space.bilibili.com/{uid}', playlist_id, fatal=False)
        return self._search_regex(r'(?s)<title\b[^>]*>([^<]+)的个人空间-', webpage, 'uploader', fatal=False)

    def _extract_playlist(self, fetch_page, get_metadata, get_entries):
        metadata, page_list = super()._extract_playlist(fetch_page, get_metadata, get_entries)
        metadata.pop('page_count', None)
        metadata.pop('page_size', None)
        return metadata, page_list


class BilibiliCollectionListIE(BilibiliSpaceListBaseIE):
    _VALID_URL = r'https?://space\.bilibili\.com/(?P<mid>\d+)/channel/collectiondetail/?\?sid=(?P<sid>\d+)'
    _TESTS = [{
        'url': 'https://space.bilibili.com/2142762/channel/collectiondetail?sid=57445',
        'info_dict': {
            'id': '2142762_57445',
            'title': '【完结】《底特律 变人》全结局流程解说',
            'description': '',
            'uploader': '老戴在此',
            'uploader_id': '2142762',
            'timestamp': int,
            'upload_date': str,
            'thumbnail': 'https://archive.biliimg.com/bfs/archive/e0e543ae35ad3df863ea7dea526bc32e70f4c091.jpg',
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
                'uploader': self._get_uploader(mid, playlist_id),
                **traverse_obj(page_data, {
                    'title': ('meta', 'name', {str}),
                    'description': ('meta', 'description', {str}),
                    'uploader_id': ('meta', 'mid', {str_or_none}),
                    'timestamp': ('meta', 'ptime', {int_or_none}),
                    'thumbnail': ('meta', 'cover', {url_or_none}),
                }),
            }

        def get_entries(page_data):
            return self._get_entries(page_data, 'archives')

        metadata, paged_list = self._extract_playlist(fetch_page, get_metadata, get_entries)
        return self.playlist_result(paged_list, playlist_id, **metadata)


class BilibiliSeriesListIE(BilibiliSpaceListBaseIE):
    _VALID_URL = r'https?://space\.bilibili\.com/(?P<mid>\d+)/channel/seriesdetail/?\?\bsid=(?P<sid>\d+)'
    _TESTS = [{
        'url': 'https://space.bilibili.com/1958703906/channel/seriesdetail?sid=547718&ctype=0',
        'info_dict': {
            'id': '1958703906_547718',
            'title': '直播回放',
            'description': '直播回放',
            'uploader': '靡烟miya',
            'uploader_id': '1958703906',
            'timestamp': 1637985853,
            'upload_date': '20211127',
            'modified_timestamp': int,
            'modified_date': str,
        },
        'playlist_mincount': 513,
    }]

    def _real_extract(self, url):
        mid, sid = self._match_valid_url(url).group('mid', 'sid')
        playlist_id = f'{mid}_{sid}'
        playlist_meta = traverse_obj(self._download_json(
            f'https://api.bilibili.com/x/series/series?series_id={sid}', playlist_id, fatal=False,
        ), {
            'title': ('data', 'meta', 'name', {str}),
            'description': ('data', 'meta', 'description', {str}),
            'uploader_id': ('data', 'meta', 'mid', {str_or_none}),
            'timestamp': ('data', 'meta', 'ctime', {int_or_none}),
            'modified_timestamp': ('data', 'meta', 'mtime', {int_or_none}),
        })

        def fetch_page(page_idx):
            return self._download_json(
                'https://api.bilibili.com/x/series/archives',
                playlist_id, note=f'Downloading page {page_idx}',
                query={'mid': mid, 'series_id': sid, 'pn': page_idx + 1, 'ps': 30})['data']

        def get_metadata(page_data):
            page_size = page_data['page']['size']
            entry_count = page_data['page']['total']
            return {
                'page_count': math.ceil(entry_count / page_size),
                'page_size': page_size,
                'uploader': self._get_uploader(mid, playlist_id),
                **playlist_meta,
            }

        def get_entries(page_data):
            return self._get_entries(page_data, 'archives')

        metadata, paged_list = self._extract_playlist(fetch_page, get_metadata, get_entries)
        return self.playlist_result(paged_list, playlist_id, **metadata)


class BilibiliFavoritesListIE(BilibiliSpaceListBaseIE):
    _VALID_URL = r'https?://(?:space\.bilibili\.com/\d+/favlist/?\?fid=|(?:www\.)?bilibili\.com/medialist/detail/ml)(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://space.bilibili.com/84912/favlist?fid=1103407912&ftype=create',
        'info_dict': {
            'id': '1103407912',
            'title': '【V2】（旧）',
            'description': '',
            'uploader': '晓月春日',
            'uploader_id': '84912',
            'timestamp': 1604905176,
            'upload_date': '20201109',
            'modified_timestamp': int,
            'modified_date': str,
            'thumbnail': r're:http://i\d\.hdslb\.com/bfs/archive/14b83c62aa8871b79083df1e9ab4fbc699ad16fe\.jpg',
            'view_count': int,
            'like_count': int,
        },
        'playlist_mincount': 22,
    }, {
        'url': 'https://www.bilibili.com/medialist/detail/ml1103407912',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        fid = self._match_id(url)

        list_info = self._download_json(
            f'https://api.bilibili.com/x/v3/fav/resource/list?media_id={fid}&pn=1&ps=20',
            fid, note='Downloading favlist metadata')
        if list_info['code'] == -403:
            self.raise_login_required(msg='This is a private favorites list. You need to log in as its owner')

        entries = self._get_entries(self._download_json(
            f'https://api.bilibili.com/x/v3/fav/resource/ids?media_id={fid}',
            fid, note='Download favlist entries'), 'data')

        return self.playlist_result(entries, fid, **traverse_obj(list_info, ('data', 'info', {
            'title': ('title', {str}),
            'description': ('intro', {str}),
            'uploader': ('upper', 'name', {str}),
            'uploader_id': ('upper', 'mid', {str_or_none}),
            'timestamp': ('ctime', {int_or_none}),
            'modified_timestamp': ('mtime', {int_or_none}),
            'thumbnail': ('cover', {url_or_none}),
            'view_count': ('cnt_info', 'play', {int_or_none}),
            'like_count': ('cnt_info', 'thumb_up', {int_or_none}),
        })))


class BilibiliWatchlaterIE(BilibiliSpaceListBaseIE):
    _VALID_URL = r'https?://(?:www\.)?bilibili\.com/watchlater/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://www.bilibili.com/watchlater/#/list',
        'info_dict': {
            'id': r're:\d+',
            'title': '稍后再看',
        },
        'playlist_mincount': 0,
        'skip': 'login required',
    }]

    def _real_extract(self, url):
        list_id = getattr(self._get_cookies(url).get('DedeUserID'), 'value', 'watchlater')
        watchlater_info = self._download_json(
            'https://api.bilibili.com/x/v2/history/toview/web?jsonp=jsonp', list_id)
        if watchlater_info['code'] == -101:
            self.raise_login_required(msg='You need to login to access your watchlater list')
        entries = self._get_entries(watchlater_info, ('data', 'list'))
        return self.playlist_result(entries, id=list_id, title='稍后再看')


class BilibiliPlaylistIE(BilibiliSpaceListBaseIE):
    _VALID_URL = r'https?://(?:www\.)?bilibili\.com/(?:medialist/play|list)/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://www.bilibili.com/list/1958703906?sid=547718',
        'info_dict': {
            'id': '5_547718',
            'title': '直播回放',
            'uploader': '靡烟miya',
            'uploader_id': '1958703906',
            'timestamp': 1637985853,
            'upload_date': '20211127',
        },
        'playlist_mincount': 513,
    }, {
        'url': 'https://www.bilibili.com/list/1958703906?sid=547718&oid=687146339&bvid=BV1DU4y1r7tz',
        'info_dict': {
            'id': 'BV1DU4y1r7tz',
            'ext': 'mp4',
            'title': '【直播回放】8.20晚9:30 3d发布喵 2022年8月20日21点场',
            'upload_date': '20220820',
            'description': '',
            'timestamp': 1661016330,
            'uploader_id': '1958703906',
            'uploader': '靡烟miya',
            'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)$',
            'duration': 9552.903,
            'tags': list,
            'comment_count': int,
            'view_count': int,
            'like_count': int,
            '_old_archive_ids': ['bilibili 687146339_part1'],
        },
        'params': {'noplaylist': True},
    }, {
        'url': 'https://www.bilibili.com/medialist/play/1958703906?business=space_series&business_id=547718&desc=1',
        'info_dict': {
            'id': '5_547718',
        },
        'playlist_mincount': 513,
        'skip': 'redirect url',
    }, {
        'url': 'https://www.bilibili.com/list/ml1103407912',
        'info_dict': {
            'id': '3_1103407912',
            'title': '【V2】（旧）',
            'uploader': '晓月春日',
            'uploader_id': '84912',
            'timestamp': 1604905176,
            'upload_date': '20201109',
            'thumbnail': r're:http://i\d\.hdslb\.com/bfs/archive/14b83c62aa8871b79083df1e9ab4fbc699ad16fe\.jpg',
        },
        'playlist_mincount': 22,
    }, {
        'url': 'https://www.bilibili.com/medialist/play/ml1103407912',
        'info_dict': {
            'id': '3_1103407912',
        },
        'playlist_mincount': 22,
        'skip': 'redirect url',
    }, {
        'url': 'https://www.bilibili.com/list/watchlater',
        'info_dict': {
            'id': r're:2_\d+',
            'title': '稍后再看',
            'uploader': str,
            'uploader_id': str,
        },
        'playlist_mincount': 0,
        'skip': 'login required',
    }, {
        'url': 'https://www.bilibili.com/medialist/play/watchlater',
        'info_dict': {'id': 'watchlater'},
        'playlist_mincount': 0,
        'skip': 'redirect url & login required',
    }]

    def _extract_medialist(self, query, list_id):
        for page_num in itertools.count(1):
            page_data = self._download_json(
                'https://api.bilibili.com/x/v2/medialist/resource/list',
                list_id, query=query, note=f'getting playlist {query["biz_id"]} page {page_num}',
            )['data']
            yield from self._get_entries(page_data, 'media_list', ending_key='bv_id')
            query['oid'] = traverse_obj(page_data, ('media_list', -1, 'id'))
            if not page_data.get('has_more', False):
                break

    def _real_extract(self, url):
        list_id = self._match_id(url)

        bvid = traverse_obj(parse_qs(url), ('bvid', 0))
        if not self._yes_playlist(list_id, bvid):
            return self.url_result(f'https://www.bilibili.com/video/{bvid}', BiliBiliIE)

        webpage = self._download_webpage(url, list_id)
        initial_state = self._search_json(r'window\.__INITIAL_STATE__\s*=', webpage, 'initial state', list_id)
        if traverse_obj(initial_state, ('error', 'code', {int_or_none})) != 200:
            error_code = traverse_obj(initial_state, ('error', 'trueCode', {int_or_none}))
            error_message = traverse_obj(initial_state, ('error', 'message', {str_or_none}))
            if error_code == -400 and list_id == 'watchlater':
                self.raise_login_required('You need to login to access your watchlater playlist')
            elif error_code == -403:
                self.raise_login_required('This is a private playlist. You need to login as its owner')
            elif error_code == 11010:
                raise ExtractorError('Playlist is no longer available', expected=True)
            raise ExtractorError(f'Could not access playlist: {error_code} {error_message}')

        query = {
            'ps': 20,
            'with_current': False,
            **traverse_obj(initial_state, {
                'type': ('playlist', 'type', {int_or_none}),
                'biz_id': ('playlist', 'id', {int_or_none}),
                'tid': ('tid', {int_or_none}),
                'sort_field': ('sortFiled', {int_or_none}),
                'desc': ('desc', {bool_or_none}, {str_or_none}, {str.lower}),
            }),
        }
        metadata = {
            'id': f'{query["type"]}_{query["biz_id"]}',
            **traverse_obj(initial_state, ('mediaListInfo', {
                'title': ('title', {str}),
                'uploader': ('upper', 'name', {str}),
                'uploader_id': ('upper', 'mid', {str_or_none}),
                'timestamp': ('ctime', {int_or_none}, {lambda x: x or None}),
                'thumbnail': ('cover', {url_or_none}),
            })),
        }
        return self.playlist_result(self._extract_medialist(query, list_id), **metadata)


class BilibiliCategoryIE(InfoExtractor):
    IE_NAME = 'Bilibili category extractor'
    _MAX_RESULTS = 1000000
    _VALID_URL = r'https?://(?:www\.)?bilibili\.com/v/[a-zA-Z]+\/[a-zA-Z]+'
    _TESTS = [{
        'url': 'https://www.bilibili.com/v/kichiku/mad',
        'info_dict': {
            'id': 'kichiku: mad',
            'title': 'kichiku: mad',
        },
        'playlist_mincount': 45,
        'params': {
            'playlistend': 45,
        },
    }]

    def _fetch_page(self, api_url, num_pages, query, page_num):
        parsed_json = self._download_json(
            api_url, query, query={'Search_key': query, 'pn': page_num},
            note=f'Extracting results from page {page_num} of {num_pages}')

        video_list = traverse_obj(parsed_json, ('data', 'archives'), expected_type=list)
        if not video_list:
            raise ExtractorError(f'Failed to retrieve video list for page {page_num}')

        for video in video_list:
            yield self.url_result(
                'https://www.bilibili.com/video/{}'.format(video['bvid']), 'BiliBili', video['bvid'])

    def _entries(self, category, subcategory, query):
        # map of categories : subcategories : RIDs
        rid_map = {
            'kichiku': {
                'mad': 26,
                'manual_vocaloid': 126,
                'guide': 22,
                'theatre': 216,
                'course': 127,
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
        query = f'{category}: {subcategory}'

        return self.playlist_result(self._entries(category, subcategory, query), query, query)


class BiliBiliSearchIE(SearchInfoExtractor):
    IE_DESC = 'Bilibili video search'
    _MAX_RESULTS = 100000
    _SEARCH_KEY = 'bilisearch'
    _TESTS = [{
        'url': 'bilisearch3:靡烟 出道一年，我怎么还在等你单推的女人睡觉后开播啊',
        'playlist_count': 3,
        'info_dict': {
            'id': '靡烟 出道一年，我怎么还在等你单推的女人睡觉后开播啊',
            'title': '靡烟 出道一年，我怎么还在等你单推的女人睡觉后开播啊',
        },
        'playlist': [{
            'info_dict': {
                'id': 'BV1n44y1Q7sc',
                'ext': 'mp4',
                'title': '“出道一年，我怎么还在等你单推的女人睡觉后开播啊？”【一分钟了解靡烟miya】',
                'timestamp': 1669889987,
                'upload_date': '20221201',
                'description': 'md5:43343c0973defff527b5a4b403b4abf9',
                'tags': list,
                'uploader': '靡烟miya',
                'duration': 123.156,
                'uploader_id': '1958703906',
                'comment_count': int,
                'view_count': int,
                'like_count': int,
                'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)$',
                '_old_archive_ids': ['bilibili 988222410_part1'],
            },
        }],
    }]

    def _search_results(self, query):
        if not self._get_cookies('https://api.bilibili.com').get('buvid3'):
            self._set_cookie('.bilibili.com', 'buvid3', f'{uuid.uuid4()}infoc')
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
            'vcodec': 'none',
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
                }],
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
            f'http://www.bilibili.tv/video/av{video_id}/',
            ie=BiliBiliIE.ie_key(), video_id=video_id)


class BiliIntlBaseIE(InfoExtractor):
    _API_URL = 'https://api.bilibili.tv/intl/gateway'
    _NETRC_MACHINE = 'biliintl'
    _HEADERS = {'Referer': 'https://www.bilibili.com/'}

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
        return '\n\n'.join(
            f'{i + 1}\n{srt_subtitles_timecode(line["from"])} --> {srt_subtitles_timecode(line["to"])}\n{line["content"]}'
            for i, line in enumerate(traverse_obj(json, (
                'body', lambda _, l: l['content'] and l['from'] and l['to']))))

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
        fetched_urls = set()
        for sub in traverse_obj(sub_json, (('subtitles', 'video_subtitle'), ..., {dict})):
            for url in traverse_obj(sub, ((None, 'ass', 'srt'), 'url', {url_or_none})):
                if url in fetched_urls:
                    continue
                fetched_urls.add(url)
                sub_ext = determine_ext(url)
                sub_lang = sub.get('lang_key') or 'en'

                if sub_ext == 'ass':
                    subtitles.setdefault(sub_lang, []).append({
                        'ext': 'ass',
                        'url': url,
                    })
                elif sub_ext == 'json':
                    sub_data = self._download_json(
                        url, ep_id or aid, fatal=False,
                        note=f'Downloading subtitles{format_field(sub, "lang", " for %s")} ({sub_lang})',
                        errnote='Unable to download subtitles')

                    if sub_data:
                        subtitles.setdefault(sub_lang, []).append({
                            'ext': 'srt',
                            'data': self.json2srt(sub_data),
                        })
                else:
                    self.report_warning('Unexpected subtitle extension', ep_id or aid)

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
            'description': video_data.get('desc'),
            'thumbnail': video_data.get('cover'),
            'timestamp': unified_timestamp(video_data.get('formatted_pub_date')),
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
        password_hash = Cryptodome.PKCS1_v1_5.new(public_key).encrypt((key_data['hash'] + password).encode())
        login_post = self._download_json(
            'https://passport.bilibili.tv/x/intl/passport-login/web/login/password?lang=en-US', None,
            data=urlencode_postdata({
                'username': username,
                'password': base64.b64encode(password_hash).decode('ascii'),
                'keep_me': 'true',
                's_locale': 'en_US',
                'isTrusted': 'true',
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
                'title': '<Untitled Chapter 1>',
            }, {
                'start_time': 76.242,
                'end_time': 161.161,
                'title': 'Intro',
            }, {
                'start_time': 1325.742,
                'end_time': 1403.903,
                'title': 'Outro',
            }],
        },
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
                'title': '<Untitled Chapter 1>',
            }, {
                'start_time': 88.0,
                'end_time': 156.0,
                'title': 'Intro',
            }, {
                'start_time': 1173.0,
                'end_time': 1259.535,
                'title': 'Outro',
            }],
        },
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
        'skip': 'According to the copyright owner\'s request, you may only watch the video after you log in.',
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
                'title': '<Untitled Chapter 1>',
            }, {
                'start_time': 61.0,
                'end_time': 134.0,
                'title': 'Intro',
            }, {
                'start_time': 1290.0,
                'end_time': 1379.0,
                'title': 'Outro',
            }],
        },
        'params': {
            'getcomments': True,
        },
    }, {
        # user generated content comment extraction
        'url': 'https://www.bilibili.tv/en/video/2045730385',
        'info_dict': {
            'id': '2045730385',
            'ext': 'mp4',
            'description': 'md5:693b6f3967fb4e7e7764ea817857c33a',
            'timestamp': 1667891924,
            'upload_date': '20221108',
            'title': 'That Time I Got Reincarnated as a Slime: Scarlet Bond - Official Trailer 3| AnimeStan',
            'comment_count': int,
            'thumbnail': r're:https://pic\.bstarstatic\.(?:com|net)/ugc/f6c363659efd2eabe5683fbb906b1582\.jpg',
        },
        'params': {
            'getcomments': True,
        },
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

    @staticmethod
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
                'sections', ..., 'episodes', lambda _, v: str(v['episode_id']) == video_id,
            ), expected_type=dict, get_all=False)

        # XXX: webpage metadata may not accurate, it just used to not crash when video_data not found
        return merge_dicts(
            self._parse_video_metadata(video_data), {
                'title': get_element_by_class(
                    'bstar-meta__title', webpage) or self._html_search_meta('og:title', webpage),
                'description': get_element_by_class(
                    'bstar-meta__desc', webpage) or self._html_search_meta('og:description', webpage),
            }, self._search_json_ld(webpage, video_id, default={}))

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
                'timestamp': unified_timestamp(replies.get('ctime_text')),
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
                    'title': 'Intro',
                }, {
                    'start_time': float_or_none(traverse_obj(intro_ending_json, ('skip', 'ending_start_time')), 1000),
                    'end_time': float_or_none(traverse_obj(intro_ending_json, ('skip', 'ending_end_time')), 1000),
                    'title': 'Outro',
                }]

        return {
            'id': video_id,
            **self._extract_video_metadata(url, video_id, season_id),
            'formats': self._get_formats(ep_id=ep_id, aid=aid),
            'subtitles': self.extract_subtitles(ep_id=ep_id, aid=aid),
            'chapters': chapters,
            '__post_extractor': self.extract_comments(video_id, ep_id),
            'http_headers': self._HEADERS,
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
                self._parse_video_metadata(episode),
            ), BiliIntlIE, episode_id)

    def _real_extract(self, url):
        series_id = self._match_id(url)
        series_info = self._call_api(
            f'/web/v2/ogv/play/season_info?season_id={series_id}&platform=web', series_id).get('season') or {}
        return self.playlist_result(
            self._entries(series_id), series_id, series_info.get('title'), series_info.get('description'),
            categories=traverse_obj(series_info, ('styles', ..., 'title'), expected_type=str_or_none),
            thumbnail=url_or_none(series_info.get('horizontal_cover')), view_count=parse_count(series_info.get('view')))


class BiliLiveIE(InfoExtractor):
    _VALID_URL = r'https?://live\.bilibili\.com/(?:blanc/)?(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://live.bilibili.com/196',
        'info_dict': {
            'id': '33989',
            'description': '周六杂谈回，其他时候随机游戏。 | \n录播：@下播型泛式录播组。 | \n直播通知群（全员禁言）：666906670，902092584，59971⑧481 （功能一样，别多加）',
            'ext': 'flv',
            'title': '太空狼人杀联动，不被爆杀就算赢',
            'thumbnail': 'https://i0.hdslb.com/bfs/live/new_room_cover/e607bc1529057ef4b332e1026e62cf46984c314d.jpg',
            'timestamp': 1650802769,
        },
        'skip': 'not live',
    }, {
        'url': 'https://live.bilibili.com/196?broadcast_type=0&is_room_feed=1?spm_id_from=333.999.space_home.strengthen_live_card.click',
        'only_matching': True,
    }, {
        'url': 'https://live.bilibili.com/blanc/196',
        'only_matching': True,
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
        for qn in self._FORMATS:
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
