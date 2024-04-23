import base64
import json
import hashlib
import random
import re
import time

from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    join_nonempty,
    strip_jsonp,
    str_or_none,
    traverse_obj,
    unescapeHTML,
    url_or_none,
    ExtractorError,
)


class QQMusicBaseIE(InfoExtractor):
    def _get_sign(self, payload: bytes):
        # This may not work for domains other than `y.qq.com` and browswer UA that contains `Headless`
        md5hex = hashlib.md5(payload).hexdigest().upper()
        hex_digits = [int(c, base=16) for c in md5hex]

        xor_digits = []
        for i, xor in enumerate([212, 45, 80, 68, 195, 163, 163, 203, 157, 220, 254, 91, 204, 79, 104, 6]):
            xor_digits.append((hex_digits[i * 2] * 16 + hex_digits[i * 2 + 1]) ^ xor)

        char_indicies = []
        for i in range(0, len(xor_digits) - 1, 3):
            char_indicies.extend([
                xor_digits[i] >> 2,
                ((xor_digits[i] & 3) << 4) | (xor_digits[i + 1] >> 4),
                ((xor_digits[i + 1] & 15) << 2) | (xor_digits[i + 2] >> 6),
                xor_digits[i + 2] & 63,
            ])
        char_indicies.extend([
            xor_digits[15] >> 2,
            (xor_digits[15] & 3) << 4,
        ])

        head = ''.join(md5hex[i] for i in [21, 4, 9, 26, 16, 20, 27, 30])
        tail = ''.join(md5hex[i] for i in [18, 11, 3, 2, 1, 7, 6, 25])
        body = ''.join('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/='[i] for i in char_indicies)
        return re.sub(r'[\/+]', '', f'zzb{head}{body}{tail}'.lower())

    def _get_g_tk(self):
        n = 5381
        for chr in self._get_cookies('https://y.qq.com').get('qqmusic_key', ''):
            n += (n << 5) + ord(chr)
        return n & 2147483647

    def _get_uin(self):
        return int_or_none(self._get_cookies('https://y.qq.com').get('o_cookie')) or 0

    # Reference: m_r_GetRUin() in top_player.js
    # http://imgcache.gtimg.cn/music/portal_v3/y/top_player.js
    @staticmethod
    def m_r_get_ruin():
        curMs = int(time.time() * 1000) % 1000
        return int(round(random.random() * 2147483647) * curMs % 1E10)

    def download_init_data(self, url, mid):
        webpage = self._download_webpage(url, mid)
        return self._search_json(
            r'window\.__INITIAL_DATA__\s*=\s*',
            webpage.replace('undefined', 'null'), 'init data', mid)

    def make_fcu_req(self, mid, req_dict, **kwargs):
        payload = json.dumps({
            'comm': {
                'cv': 4747474,
                'ct': 24,
                'format': 'json',
                'inCharset': 'utf-8',
                'outCharset': 'utf-8',
                'notice': 0,
                'platform': 'yqq.json',
                'needNewCode': 1,
                'uin': self._get_uin(),
                'g_tk_new_20200303': self._get_g_tk(),
                'g_tk': self._get_g_tk(),
            },
            **req_dict
        }, separators=(',', ':')).encode('utf-8')

        return self._download_json(
            'https://u.y.qq.com/cgi-bin/musics.fcg', mid, data=payload,
            query={'_': int(time.time()), 'sign': self._get_sign(payload)}, **kwargs)


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
            'release_date': '20111230',
            'duration': 281,
            'creators': ['ケーキ姫', 'JUMA'],
            'album': '幻想遊園郷 -Fantastic Park-',
            'description': 'md5:b5261f3d595657ae561e9e6aee7eb7d9',
            'size': 4501244,
            'thumbnail': r're:^https?://.*\.jpg(?:$|[#?])',
            'subtitles': 'count:1',
        },
        'params': {'listsubtitles': True},
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

        init_data = self.download_init_data(url, mid)
        media_id = traverse_obj(init_data, (
            'songList', lambda _, v: v['mid'] == mid, 'file', 'media_mid'), get_all=False)

        data = self.make_fcu_req(mid, {
            'req_1': {
                'module': 'vkey.GetVkeyServer',
                'method': 'CgiGetVkey',
                'param': {
                    'guid': str(self.m_r_get_ruin()),
                    'songmid': [mid],
                    'songtype': [0],
                    'uin': self._get_cookies('https://y.qq.com').get('o_cookie', '0'),
                    'loginflag': 1,
                    'platform': '20',
                    **({
                        'songmid': [mid] * len(self._FORMATS),
                        'songtype': [0] * len(self._FORMATS),
                        'filename': [f'{f["prefix"]}{media_id}.{f["ext"]}' for f in self._FORMATS.values()],
                    } if media_id else {}),
                }
            },
            'req_2': {
                'module': 'music.musichallSong.PlayLyricInfo',
                'method': 'GetPlayLyricInfo',
                'param': {
                    'songMID': mid,
                    'songID': traverse_obj(init_data, ('detail', 'id', {int})),
                }
            }})

        formats = traverse_obj(data, ('req_1', 'data', 'midurlinfo', lambda _, v: v['songmid'] == mid and v['purl'], {
            'url': ('purl', {str}, {lambda x: f'https://dl.stream.qqmusic.qq.com/{x}'}),
            'format': ('filename', {lambda x: self._FORMATS[x[:4]]['name']}),
            'format_id': ('filename', {lambda x: self._FORMATS[x[:4]]['name']}),
            'size': ('filename', {lambda x: self._FORMATS[x[:4]]['name']},
                     {lambda x: traverse_obj(init_data, ('songList', ..., 'file', f'size_{x}'), get_all=False)}),
            'quality': ('filename', {lambda x: self._FORMATS[x[:4]]['preference']}),
            'abr': ('filename', {lambda x: self._FORMATS[x[:4]]['abr']}),
        }))
        lrc_content = traverse_obj(data, ('req_2', 'data', 'lyric', {lambda x: base64.b64decode(x).decode('utf-8')}))

        info_dict = {
            'id': mid,
            'formats': formats,
            **traverse_obj(init_data, ('detail', {
                'title': ('title', {str}),
                'album': ('albumName', {str}, {lambda x: x or None}),
                'thumbnail': ('picurl', {url_or_none}),
                'release_date': ('ctime', {lambda x: x.replace('-', '') or None}),
                'description': ('info', 'intro', 'content', ..., 'value', {str}),
            }), get_all=False),
            **traverse_obj(init_data, ('songList', lambda _, v: v['mid'] == mid, {
                'alt_title': ('subtitle', {str}, {lambda x: x or None}),
                'duration': ('interval', {int}),
            }), get_all=False),
            'creators': traverse_obj(init_data, ('detail', 'singer', ..., 'name')),
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
        'playlist_mincount': 10,
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
                'release_date': '20210913',
                'duration': 248,
                'creators': ['桃几OvO'],
                'album': '桃几2021年翻唱集',
                'description': 'md5:4296005a04edcb5cdbe0889d5055a7ae',
                'size': 3970822,
                'thumbnail': r're:^https?://.*\.jpg(?:$|[#?])',
            },
        }],
    }]

    def _entries(self, mid, init_data):
        size = 50
        max_num = traverse_obj(init_data, ('singerDetail', 'songTotalNum'))
        for page in range(0, max_num // size + 1):
            data = self.make_fcu_req(mid, {'req_1': {
                'module': 'music.web_singer_info_svr',
                'method': 'get_singer_detail_info',
                'param': {
                    'sort': 5,
                    'singermid': mid,
                    'sin': page * size,
                    'num': size,
                }}}, note=f'Downloading page {page}')
            yield from traverse_obj(data, ('req_1', 'data', 'songlist', ..., {lambda x: self.url_result(
                f'https://y.qq.com/n/ryqq/songDetail/{x["mid"]}', QQMusicIE, x['mid'], x.get('title'))}))

    def _real_extract(self, url):
        mid = self._match_id(url)

        init_data = self.download_init_data(url, mid)
        return self.playlist_result(
            self._entries(mid, init_data), mid, **traverse_obj(init_data, ('singerDetail', {
                'title': ('basic_info', 'name', {str}),
                'description': ('ex_info', 'desc', {str}),
                'thumbnail': ('pic', 'pic', {url_or_none}),
            })))


class QQPlaylistBaseIE(InfoExtractor):
    def _extract_entries(self, info_json, path):
        return traverse_obj(info_json, (*path, {lambda song: self.url_result(
            f'https://y.qq.com/n/ryqq/songDetail/{song["songmid"]}', QQMusicIE, song['songmid'], song['songname'])}))


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
            'description': ('desc', {str}, {str.strip}),
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

        entries = self._extract_entries(toplist_json, ('songlist', ..., 'data'))

        list_name = join_nonempty(*traverse_obj(toplist_json, ((('topinfo', 'ListName'), 'update_time'),)), delim=' ')
        list_description = traverse_obj(toplist_json, ('topinfo', 'info'))

        return self.playlist_result(entries, list_id, list_name, list_description)


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
            error_msg = ''
            if list_json.get('code') or list_json.get('subcode'):
                error_msg = f': Error {list_json.get("code")}-{list_json["subcode"]}: {list_json.get("msg", "")}'
            raise ExtractorError(f'Unable to get playlist info{error_msg}')

        entries = self._extract_entries(list_json, ('cdlist', 0, 'songlist', ...))

        return self.playlist_result(entries, list_id, **traverse_obj(list_json, ('cdlist', 0, {
            'title': ('dissname', {str}),
            'description': ('desc', {lambda x: clean_html(unescapeHTML(x))}),
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
            'view_count': 542,
        },
    }]

    def _parse_url_formats(self, url_data):
        formats = traverse_obj(url_data, ('mp4', lambda _, v: v.get('freeflow_url'), {
            'url': ('freeflow_url', 0, {url_or_none}),
            'filesize': ('fileSize', {int_or_none}),
            'format_id': ('newFileType', {str_or_none}),
        }))
        return formats

    def _real_extract(self, url):
        video_id = self._match_id(url)

        payload = json.dumps({
            'comm': {
                'ct': 6,
                'cv': 0,
                'g_tk': self._get_g_tk(),
                'uin': self._get_uin(),
                'format': 'json',
                'platform': 'yqq',
            },
            'mvInfo': {
                'module': 'music.video.VideoData',
                'method': 'get_video_info_batch',
                'param': {
                    'vidlist': [video_id],
                    'required': [
                        'vid', 'type', 'sid', 'cover_pic', 'duration', 'singers',
                        'new_switch_str', 'video_pay', 'hint', 'code', 'msg',
                        'name', 'desc', 'playcnt', 'pubdate', 'isfav', 'fileid',
                        'filesize_v2', 'switch_pay_type', 'pay', 'pay_info',
                        'uploader_headurl', 'uploader_nick', 'uploader_uin',
                        'uploader_encuin', 'play_forbid_reason']
                }
            },
            'mvUrl': {
                'module': 'music.stream.MvUrlProxy',
                'method': 'GetMvUrls',
                'param': {
                    'vids': [video_id],
                    'request_type': 10003,
                    'addrtype': 3,
                    'format': 264,
                    'maxFiletype': 60,
                }
            }
        }, separators=(',', ':')).encode('utf-8')

        video_info = self._download_json('https://u.y.qq.com/cgi-bin/musicu.fcg', video_id, data=payload)
        if traverse_obj(video_info, ('mvInfo', 'data', video_id, 'play_forbid_reason')) == 3:
            self.raise_geo_restricted()

        return {
            'id': video_id,
            'formats': self._parse_url_formats(traverse_obj(video_info, ('mvUrl', 'data', video_id))),
            **traverse_obj(video_info, ('mvInfo', 'data', video_id, {
                'title': ('name', {str_or_none}),
                'description': ('desc', {str_or_none}),
                'thumbnail': ('cover_pic', {url_or_none}),
                'release_timestamp': ('pubdate', {int_or_none}),
                'duration': ('duration', {int_or_none}),
                'creators': ('singers', ..., 'name', {str}),
                'view_count': ('playcnt', {int_or_none}),
            })),
        }
