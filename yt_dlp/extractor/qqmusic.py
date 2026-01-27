import base64
import functools
import json
import random
import time

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    clean_html,
    int_or_none,
    join_nonempty,
    js_to_json,
    str_or_none,
    strip_jsonp,
    traverse_obj,
    url_or_none,
    urljoin,
)


class QQMusicBaseIE(InfoExtractor):
    def _get_cookie(self, key, default=None):
        return getattr(self._get_cookies('https://y.qq.com').get(key), 'value', default)

    def _get_g_tk(self):
        n = 5381
        for c in self._get_cookie('qqmusic_key', ''):
            n += (n << 5) + ord(c)
        return n & 2147483647

    def _get_uin(self):
        return int_or_none(self._get_cookie('uin')) or 0

    @property
    def is_logged_in(self):
        return bool(self._get_uin() and self._get_cookie('fqm_pvqid'))

    # Reference: m_r_GetRUin() in top_player.js
    # http://imgcache.gtimg.cn/music/portal_v3/y/top_player.js
    @staticmethod
    def _m_r_get_ruin():
        cur_ms = int(time.time() * 1000) % 1000
        return int(round(random.random() * 2147483647) * cur_ms % 1E10)

    def _download_init_data(self, url, mid, fatal=True):
        webpage = self._download_webpage(url, mid, fatal=fatal)
        return self._search_json(r'window\.__INITIAL_DATA__\s*=', webpage,
                                 'init data', mid, transform_source=js_to_json, fatal=fatal)

    def _make_fcu_req(self, req_dict, mid, headers={}, **kwargs):
        return self._download_json(
            'https://u.y.qq.com/cgi-bin/musicu.fcg', mid, data=json.dumps({
                'comm': {
                    'cv': 0,
                    'ct': 24,
                    'format': 'json',
                    'uin': self._get_uin(),
                },
                **req_dict,
            }, separators=(',', ':')).encode(), headers=headers, **kwargs)


class QQMusicIE(QQMusicBaseIE):
    IE_NAME = 'qqmusic'
    IE_DESC = 'QQ音乐'
    _VALID_URL = r'https?://y\.qq\.com/n/ryqq/songDetail/(?P<id>[0-9A-Za-z]+)'
    _TESTS = [{
        'url': 'https://y.qq.com/n/ryqq/songDetail/004Ti8rT003TaZ',
        'md5': 'd7adc5c438d12e2cb648cca81593fd47',
        'info_dict': {
            'id': '004Ti8rT003TaZ',
            'ext': 'mp3',
            'title': '永夜のパレード (永夜的游行)',
            'album': '幻想遊園郷 -Fantastic Park-',
            'release_date': '20111230',
            'duration': 281,
            'creators': ['ケーキ姫', 'JUMA'],
            'genres': ['Pop'],
            'description': 'md5:b5261f3d595657ae561e9e6aee7eb7d9',
            'size': 4501244,
            'thumbnail': r're:^https?://.*\.jpg(?:$|[#?])',
            'subtitles': 'count:1',
        },
    }, {
        'url': 'https://y.qq.com/n/ryqq/songDetail/004295Et37taLD',
        'md5': '5f1e6cea39e182857da7ffc5ef5e6bb8',
        'info_dict': {
            'id': '004295Et37taLD',
            'ext': 'mp3',
            'title': '可惜没如果',
            'album': '新地球 - 人 (Special Edition)',
            'release_date': '20150129',
            'duration': 298,
            'creators': ['林俊杰'],
            'genres': ['Pop'],
            'description': 'md5:f568421ff618d2066e74b65a04149c4e',
            'thumbnail': r're:^https?://.*\.jpg(?:$|[#?])',
        },
        'skip': 'premium member only',
    }, {
        'note': 'There is no mp3-320 version of this song.',
        'url': 'https://y.qq.com/n/ryqq/songDetail/004MsGEo3DdNxV',
        'md5': '028aaef1ae13d8a9f4861a92614887f9',
        'info_dict': {
            'id': '004MsGEo3DdNxV',
            'ext': 'mp3',
            'title': '如果',
            'album': '新传媒电视连续剧金曲系列II',
            'release_date': '20050626',
            'duration': 220,
            'creators': ['李季美'],
            'genres': [],
            'description': 'md5:fc711212aa623b28534954dc4bd67385',
            'size': 3535730,
            'thumbnail': r're:^https?://.*\.jpg(?:$|[#?])',
        },
    }, {
        'note': 'lyrics not in .lrc format',
        'url': 'https://y.qq.com/n/ryqq/songDetail/001JyApY11tIp6',
        'info_dict': {
            'id': '001JyApY11tIp6',
            'ext': 'mp3',
            'title': 'Shadows Over Transylvania',
            'release_date': '19970225',
            'creator': 'Dark Funeral',
            'description': 'md5:c9b20210587cbcd6836a1c597bab4525',
            'thumbnail': r're:^https?://.*\.jpg(?:$|[#?])',
        },
        'params': {'skip_download': True},
        'skip': 'no longer available',
    }]

    _FORMATS = {
        'F000': {'name': 'flac', 'prefix': 'F000', 'ext': 'flac', 'preference': 60},
        'A000': {'name': 'ape', 'prefix': 'A000', 'ext': 'ape', 'preference': 50},
        'M800': {'name': '320mp3', 'prefix': 'M800', 'ext': 'mp3', 'preference': 40, 'abr': 320},
        'M500': {'name': '128mp3', 'prefix': 'M500', 'ext': 'mp3', 'preference': 30, 'abr': 128},
        'C400': {'name': '96aac', 'prefix': 'C400', 'ext': 'm4a', 'preference': 20, 'abr': 96},
        'C200': {'name': '48aac', 'prefix': 'C200', 'ext': 'm4a', 'preference': 20, 'abr': 48},
    }

    def _real_extract(self, url):
        mid = self._match_id(url)

        init_data = self._download_init_data(url, mid, fatal=False)
        info_data = self._make_fcu_req({'info': {
            'module': 'music.pf_song_detail_svr',
            'method': 'get_song_detail_yqq',
            'param': {
                'song_mid': mid,
                'song_type': 0,
            },
        }}, mid, note='Downloading song info')['info']['data']['track_info']

        media_mid = info_data['file']['media_mid']

        data = self._make_fcu_req({
            'req_1': {
                'module': 'vkey.GetVkeyServer',
                'method': 'CgiGetVkey',
                'param': {
                    'guid': str(self._m_r_get_ruin()),
                    'songmid': [mid] * len(self._FORMATS),
                    'songtype': [0] * len(self._FORMATS),
                    'uin': str(self._get_uin()),
                    'loginflag': 1,
                    'platform': '20',
                    'filename': [f'{f["prefix"]}{media_mid}.{f["ext"]}' for f in self._FORMATS.values()],
                },
            },
            'req_2': {
                'module': 'music.musichallSong.PlayLyricInfo',
                'method': 'GetPlayLyricInfo',
                'param': {'songMID': mid},
            },
        }, mid, note='Downloading formats and lyric', headers=self.geo_verification_headers())

        code = traverse_obj(data, ('req_1', 'code', {int}))
        if code != 0:
            raise ExtractorError(f'Failed to download format info, error code {code or "unknown"}')
        formats = []
        for media_info in traverse_obj(data, (
            'req_1', 'data', 'midurlinfo', lambda _, v: v['songmid'] == mid and v['purl']),
        ):
            format_key = traverse_obj(media_info, ('filename', {str}, {lambda x: x[:4]}))
            format_info = self._FORMATS.get(format_key) or {}
            format_id = format_info.get('name')
            formats.append({
                'url': urljoin('https://dl.stream.qqmusic.qq.com', media_info['purl']),
                'format': format_id,
                'format_id': format_id,
                'size': traverse_obj(info_data, ('file', f'size_{format_id}', {int_or_none})),
                'quality': format_info.get('preference'),
                'abr': format_info.get('abr'),
                'ext': format_info.get('ext'),
                'vcodec': 'none',
            })

        if not formats and not self.is_logged_in:
            self.raise_login_required()

        if traverse_obj(data, ('req_2', 'code')):
            self.report_warning(f'Failed to download lyric, error {data["req_2"]["code"]!r}')
        lrc_content = traverse_obj(data, ('req_2', 'data', 'lyric', {lambda x: base64.b64decode(x).decode('utf-8')}))

        info_dict = {
            'id': mid,
            'formats': formats,
            **traverse_obj(info_data, {
                'title': ('title', {str}),
                'album': ('album', 'title', {str}, filter),
                'release_date': ('time_public', {lambda x: x.replace('-', '') or None}),
                'creators': ('singer', ..., 'name', {str}),
                'alt_title': ('subtitle', {str}, filter),
                'duration': ('interval', {int_or_none}),
            }),
            **traverse_obj(init_data, ('detail', {
                'thumbnail': ('picurl', {url_or_none}),
                'description': ('info', 'intro', 'content', ..., 'value', {str}),
                'genres': ('info', 'genre', 'content', ..., 'value', {str}, all),
            }), get_all=False),
        }
        if lrc_content:
            info_dict['subtitles'] = {'origin': [{'ext': 'lrc', 'data': lrc_content}]}
            info_dict['description'] = join_nonempty(info_dict.get('description'), lrc_content, delim='\n')
        return info_dict


class QQMusicSingerIE(QQMusicBaseIE):
    IE_NAME = 'qqmusic:singer'
    IE_DESC = 'QQ音乐 - 歌手'
    _VALID_URL = r'https?://y\.qq\.com/n/ryqq/singer/(?P<id>[0-9A-Za-z]+)'
    _TESTS = [{
        'url': 'https://y.qq.com/n/ryqq/singer/001BLpXF2DyJe2',
        'info_dict': {
            'id': '001BLpXF2DyJe2',
            'title': '林俊杰',
            'description': 'md5:10624ce73b06fa400bc846f59b0305fa',
            'thumbnail': r're:^https?://.*\.jpg(?:$|[#?])',
        },
        'playlist_mincount': 100,
    }, {
        'url': 'https://y.qq.com/n/ryqq/singer/000Q00f213YzNV',
        'info_dict': {
            'id': '000Q00f213YzNV',
            'title': '桃几OvO',
            'description': '小破站小唱见~希望大家喜欢听我唱歌~！',
            'thumbnail': r're:^https?://.*\.jpg(?:$|[#?])',
        },
        'playlist_count': 12,
        'playlist': [{
            'info_dict': {
                'id': '0016cvsy02mmCl',
                'ext': 'mp3',
                'title': '群青',
                'album': '桃几2021年翻唱集',
                'release_date': '20210913',
                'duration': 248,
                'creators': ['桃几OvO'],
                'genres': ['Pop'],
                'description': 'md5:4296005a04edcb5cdbe0889d5055a7ae',
                'size': 3970822,
                'thumbnail': r're:^https?://.*\.jpg(?:$|[#?])',
            },
        }],
    }]

    _PAGE_SIZE = 50

    def _fetch_page(self, mid, page_size, page_num):
        data = self._make_fcu_req({'req_1': {
            'module': 'music.web_singer_info_svr',
            'method': 'get_singer_detail_info',
            'param': {
                'sort': 5,
                'singermid': mid,
                'sin': page_num * page_size,
                'num': page_size,
            }}}, mid, note=f'Downloading page {page_num}')
        yield from traverse_obj(data, ('req_1', 'data', 'songlist', ..., {lambda x: self.url_result(
            f'https://y.qq.com/n/ryqq/songDetail/{x["mid"]}', QQMusicIE, x['mid'], x.get('title'))}))

    def _real_extract(self, url):
        mid = self._match_id(url)
        init_data = self._download_init_data(url, mid, fatal=False)

        return self.playlist_result(
            OnDemandPagedList(functools.partial(self._fetch_page, mid, self._PAGE_SIZE), self._PAGE_SIZE),
            mid, **traverse_obj(init_data, ('singerDetail', {
                'title': ('basic_info', 'name', {str}),
                'description': ('ex_info', 'desc', {str}),
                'thumbnail': ('pic', 'pic', {url_or_none}),
            })))


class QQPlaylistBaseIE(InfoExtractor):
    def _extract_entries(self, info_json, path):
        for song in traverse_obj(info_json, path):
            song_mid = song.get('songmid')
            if not song_mid:
                continue
            yield self.url_result(
                f'https://y.qq.com/n/ryqq/songDetail/{song_mid}',
                QQMusicIE, song_mid, song.get('songname'))


class QQMusicAlbumIE(QQPlaylistBaseIE):
    IE_NAME = 'qqmusic:album'
    IE_DESC = 'QQ音乐 - 专辑'
    _VALID_URL = r'https?://y\.qq\.com/n/ryqq/albumDetail/(?P<id>[0-9A-Za-z]+)'

    _TESTS = [{
        'url': 'https://y.qq.com/n/ryqq/albumDetail/000gXCTb2AhRR1',
        'info_dict': {
            'id': '000gXCTb2AhRR1',
            'title': '我们都是这样长大的',
            'description': 'md5:179c5dce203a5931970d306aa9607ea6',
        },
        'playlist_count': 4,
    }, {
        'url': 'https://y.qq.com/n/ryqq/albumDetail/002Y5a3b3AlCu3',
        'info_dict': {
            'id': '002Y5a3b3AlCu3',
            'title': '그리고…',
            'description': 'md5:a48823755615508a95080e81b51ba729',
        },
        'playlist_count': 8,
    }]

    def _real_extract(self, url):
        mid = self._match_id(url)

        album_json = self._download_json(
            'http://i.y.qq.com/v8/fcg-bin/fcg_v8_album_info_cp.fcg',
            mid, 'Download album page',
            query={'albummid': mid, 'format': 'json'})['data']

        entries = self._extract_entries(album_json, ('list', ...))

        return self.playlist_result(entries, mid, **traverse_obj(album_json, {
            'title': ('name', {str}),
            'description': ('desc', {str.strip}),
        }))


class QQMusicToplistIE(QQPlaylistBaseIE):
    IE_NAME = 'qqmusic:toplist'
    IE_DESC = 'QQ音乐 - 排行榜'
    _VALID_URL = r'https?://y\.qq\.com/n/ryqq/toplist/(?P<id>[0-9]+)'

    _TESTS = [{
        'url': 'https://y.qq.com/n/ryqq/toplist/123',
        'info_dict': {
            'id': '123',
            'title': r're:美国热门音乐榜 \d{4}-\d{2}-\d{2}',
            'description': '美国热门音乐榜，每周一更新。',
        },
        'playlist_count': 95,
    }, {
        'url': 'https://y.qq.com/n/ryqq/toplist/3',
        'info_dict': {
            'id': '3',
            'title': r're:巅峰榜·欧美 \d{4}-\d{2}-\d{2}',
            'description': 'md5:4def03b60d3644be4c9a36f21fd33857',
        },
        'playlist_count': 100,
    }, {
        'url': 'https://y.qq.com/n/ryqq/toplist/106',
        'info_dict': {
            'id': '106',
            'title': r're:韩国Mnet榜 \d{4}-\d{2}-\d{2}',
            'description': 'md5:cb84b325215e1d21708c615cac82a6e7',
        },
        'playlist_count': 50,
    }]

    def _real_extract(self, url):
        list_id = self._match_id(url)

        toplist_json = self._download_json(
            'http://i.y.qq.com/v8/fcg-bin/fcg_v8_toplist_cp.fcg', list_id,
            note='Download toplist page',
            query={'type': 'toplist', 'topid': list_id, 'format': 'json'})

        return self.playlist_result(
            self._extract_entries(toplist_json, ('songlist', ..., 'data')), list_id,
            playlist_title=join_nonempty(*traverse_obj(
                toplist_json, ((('topinfo', 'ListName'), 'update_time'), None)), delim=' '),
            playlist_description=traverse_obj(toplist_json, ('topinfo', 'info')))


class QQMusicPlaylistIE(QQPlaylistBaseIE):
    IE_NAME = 'qqmusic:playlist'
    IE_DESC = 'QQ音乐 - 歌单'
    _VALID_URL = r'https?://y\.qq\.com/n/ryqq/playlist/(?P<id>[0-9]+)'

    _TESTS = [{
        'url': 'https://y.qq.com/n/ryqq/playlist/1374105607',
        'info_dict': {
            'id': '1374105607',
            'title': '易入人心的华语民谣',
            'description': '民谣的歌曲易于传唱、、歌词朗朗伤口、旋律简单温馨。属于那种才入耳孔。却上心头的感觉。没有太多的复杂情绪。简单而直接地表达乐者的情绪，就是这样的简单才易入人心。',
        },
        'playlist_count': 20,
    }]

    def _real_extract(self, url):
        list_id = self._match_id(url)

        list_json = self._download_json(
            'http://i.y.qq.com/qzone-music/fcg-bin/fcg_ucc_getcdinfo_byids_cp.fcg',
            list_id, 'Download list page',
            query={'type': 1, 'json': 1, 'utf8': 1, 'onlysong': 0, 'disstid': list_id},
            transform_source=strip_jsonp, headers={'Referer': url})
        if not len(list_json.get('cdlist', [])):
            raise ExtractorError(join_nonempty(
                'Unable to get playlist info',
                join_nonempty('code', 'subcode', from_dict=list_json),
                list_json.get('msg'), delim=': '))

        entries = self._extract_entries(list_json, ('cdlist', 0, 'songlist', ...))

        return self.playlist_result(entries, list_id, **traverse_obj(list_json, ('cdlist', 0, {
            'title': ('dissname', {str}),
            'description': ('desc', {clean_html}),
        })))


class QQMusicVideoIE(QQMusicBaseIE):
    IE_NAME = 'qqmusic:mv'
    IE_DESC = 'QQ音乐 - MV'
    _VALID_URL = r'https?://y\.qq\.com/n/ryqq/mv/(?P<id>[0-9A-Za-z]+)'

    _TESTS = [{
        'url': 'https://y.qq.com/n/ryqq/mv/002Vsarh3SVU8K',
        'info_dict': {
            'id': '002Vsarh3SVU8K',
            'ext': 'mp4',
            'title': 'The Chant (Extended Mix / Audio)',
            'description': '',
            'thumbnail': r're:^https?://.*\.jpg(?:$|[#?])',
            'release_timestamp': 1688918400,
            'release_date': '20230709',
            'duration': 313,
            'creators': ['Duke Dumont'],
            'view_count': int,
        },
    }]

    def _parse_url_formats(self, url_data):
        return traverse_obj(url_data, ('mp4', lambda _, v: v['freeflow_url'], {
            'url': ('freeflow_url', 0, {url_or_none}),
            'filesize': ('fileSize', {int_or_none}),
            'format_id': ('newFileType', {str_or_none}),
        }))

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video_info = self._make_fcu_req({
            'mvInfo': {
                'module': 'music.video.VideoData',
                'method': 'get_video_info_batch',
                'param': {
                    'vidlist': [video_id],
                    'required': [
                        'vid', 'type', 'sid', 'cover_pic', 'duration', 'singers',
                        'video_pay', 'hint', 'code', 'msg', 'name', 'desc',
                        'playcnt', 'pubdate', 'play_forbid_reason'],
                },
            },
            'mvUrl': {
                'module': 'music.stream.MvUrlProxy',
                'method': 'GetMvUrls',
                'param': {'vids': [video_id]},
            },
        }, video_id, headers=self.geo_verification_headers())
        if traverse_obj(video_info, ('mvInfo', 'data', video_id, 'play_forbid_reason')) == 3:
            self.raise_geo_restricted()

        return {
            'id': video_id,
            'formats': self._parse_url_formats(traverse_obj(video_info, ('mvUrl', 'data', video_id))),
            **traverse_obj(video_info, ('mvInfo', 'data', video_id, {
                'title': ('name', {str}),
                'description': ('desc', {str}),
                'thumbnail': ('cover_pic', {url_or_none}),
                'release_timestamp': ('pubdate', {int_or_none}),
                'duration': ('duration', {int_or_none}),
                'creators': ('singers', ..., 'name', {str}),
                'view_count': ('playcnt', {int_or_none}),
            })),
        }
