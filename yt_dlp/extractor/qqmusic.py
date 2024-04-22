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
    UserNotLive,
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

    # Reference: m_r_GetRUin() in top_player.js
    # http://imgcache.gtimg.cn/music/portal_v3/y/top_player.js
    @staticmethod
    def m_r_get_ruin():
        curMs = int(time.time() * 1000) % 1000
        return int(round(random.random() * 2147483647) * curMs % 1E10)


class QQMusicIE(QQMusicBaseIE):
    IE_NAME = 'qqmusic'
    IE_DESC = 'QQ音乐'
    _VALID_URL = r'https?://y\.qq\.com/n/ryqq/songDetail/(?P<id>[0-9A-Za-z]+)'
    _TESTS = [{
        'url': 'https://y.qq.com/n/ryqq/songDetail/004295Et37taLD',
        'md5': '5f1e6cea39e182857da7ffc5ef5e6bb8',
        'info_dict': {
            'id': '004295Et37taLD',
            'ext': 'mp3',
            'title': '可惜没如果',
            'release_date': '20141227',
            'creator': '林俊杰',
            'description': 'md5:d85afb3051952ecc50a1ee8a286d1eac',
            'thumbnail': r're:^https?://.*\.jpg$',
        }
    }, {
        'note': 'There is no mp3-320 version of this song.',
        'url': 'https://y.qq.com/n/yqq/song/004MsGEo3DdNxV.html',
        'md5': 'fa3926f0c585cda0af8fa4f796482e3e',
        'info_dict': {
            'id': '004MsGEo3DdNxV',
            'ext': 'mp3',
            'title': '如果',
            'release_date': '20050626',
            'creator': '李季美',
            'description': 'md5:46857d5ed62bc4ba84607a805dccf437',
            'thumbnail': r're:^https?://.*\.jpg$',
        }
    }, {
        'note': 'lyrics not in .lrc format',
        'url': 'https://y.qq.com/n/yqq/song/001JyApY11tIp6.html',
        'info_dict': {
            'id': '001JyApY11tIp6',
            'ext': 'mp3',
            'title': 'Shadows Over Transylvania',
            'release_date': '19970225',
            'creator': 'Dark Funeral',
            'description': 'md5:c9b20210587cbcd6836a1c597bab4525',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
        'params': {
            'skip_download': True,
        },
    }]

    _FORMATS = {
        'mp3-320': {'prefix': 'M800', 'ext': 'mp3', 'preference': 40, 'abr': 320},
        'mp3-128': {'prefix': 'M500', 'ext': 'mp3', 'preference': 30, 'abr': 128},
        'm4a': {'prefix': 'C200', 'ext': 'm4a', 'preference': 10}
    }

    def _real_extract(self, url):
        mid = self._match_id(url)

        webpage = self._download_webpage(url, mid)
        init_data = self._search_json(
            r'window\.__INITIAL_DATA__\s*=\s*', webpage.replace('undefined', 'null'),
            'init data', mid, fatal=False)

        payload = json.dumps({
            "comm": {
                "cv": 4747474,
                "ct": 24,
                "format": "json",
                "inCharset": "utf-8",
                "outCharset": "utf-8",
                "notice": 0,
                "platform": "yqq.json",
                "needNewCode": 1,
                "uin": int_or_none(self._get_cookies('https://y.qq.com').get('o_cookie')) or 0,
                "g_tk_new_20200303": self._get_g_tk(),
                "g_tk": self._get_g_tk(),
            },
            "req_1": {
                "module": "vkey.GetVkeyServer",
                "method": "CgiGetVkey",
                "param": {
                    "guid": str(self.m_r_get_ruin()),
                    "songmid": [mid],
                    "songtype": [0],
                    "uin": self._get_cookies('https://y.qq.com').get('o_cookie', '0'),
                    "loginflag": 1,
                    "platform": "20"
                }
            },
            "req_2": {
                "module": "music.musichallSong.PlayLyricInfo",
                "method": "GetPlayLyricInfo",
                "param": {
                    "songMID": mid,
                    "songID": traverse_obj(init_data, ('detail', 'id', {int})),
                }
            },
        }, separators=(',', ':')).encode('utf-8')

        data = self._download_json(
            'https://u6.y.qq.com/cgi-bin/musics.fcg', mid, data=payload,
            query={'_': int(time.time()), 'sign': self._get_sign(payload)})

        formats = traverse_obj(data, ('req_1', 'data', 'midurlinfo', lambda _, v: v['songmid'] == mid, {
            'url': ('purl', {str}, {lambda x: f'https://dl.stream.qqmusic.qq.com/{x}'}),
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
            'creator': ' / '.join(traverse_obj(init_data, ('detail', 'singer', ..., 'name'))) or None,
        }
        if lrc_content:
            info_dict['subtitles'] = {
                'origin': [{
                    'ext': 'lrc',
                    'data': lrc_content,
                }]
            }
            info_dict['description'] = join_nonempty(info_dict.get('description'), lrc_content, delim='\n')
        return info_dict


class QQPlaylistBaseIE(InfoExtractor):
    @staticmethod
    def qq_static_url(category, mid):
        return 'http://y.qq.com/y/static/%s/%s/%s/%s.html' % (category, mid[-2], mid[-1], mid)

    def get_singer_all_songs(self, singmid, num):
        return self._download_webpage(
            r'https://c.y.qq.com/v8/fcg-bin/fcg_v8_singer_track_cp.fcg', singmid,
            query={
                'format': 'json',
                'inCharset': 'utf8',
                'outCharset': 'utf-8',
                'platform': 'yqq',
                'needNewCode': 0,
                'singermid': singmid,
                'order': 'listen',
                'begin': 0,
                'num': num,
                'songstatus': 1,
            })

    def get_entries_from_page(self, singmid):
        entries = []

        default_num = 1
        json_text = self.get_singer_all_songs(singmid, default_num)
        json_obj_all_songs = self._parse_json(json_text, singmid)

        if json_obj_all_songs['code'] == 0:
            total = json_obj_all_songs['data']['total']
            json_text = self.get_singer_all_songs(singmid, total)
            json_obj_all_songs = self._parse_json(json_text, singmid)

        for item in json_obj_all_songs['data']['list']:
            if item['musicData'].get('songmid') is not None:
                songmid = item['musicData']['songmid']
                entries.append(self.url_result(
                    r'https://y.qq.com/n/yqq/song/%s.html' % songmid, 'QQMusic', songmid))

        return entries


class QQMusicSingerIE(QQPlaylistBaseIE):
    IE_NAME = 'qqmusic:singer'
    IE_DESC = 'QQ音乐 - 歌手'
    _VALID_URL = r'https?://y\.qq\.com/n/yqq/singer/(?P<id>[0-9A-Za-z]+)\.html'
    _TEST = {
        'url': 'https://y.qq.com/n/yqq/singer/001BLpXF2DyJe2.html',
        'info_dict': {
            'id': '001BLpXF2DyJe2',
            'title': '林俊杰',
            'description': 'md5:870ec08f7d8547c29c93010899103751',
        },
        'playlist_mincount': 12,
    }

    def _real_extract(self, url):
        mid = self._match_id(url)

        entries = self.get_entries_from_page(mid)
        singer_page = self._download_webpage(url, mid, 'Download singer page')
        singer_name = self._html_search_regex(
            r"singername\s*:\s*'(.*?)'", singer_page, 'singer name', default=None)
        singer_desc = None

        if mid:
            singer_desc_page = self._download_xml(
                'http://s.plcloud.music.qq.com/fcgi-bin/fcg_get_singer_desc.fcg', mid,
                'Donwload singer description XML',
                query={'utf8': 1, 'outCharset': 'utf-8', 'format': 'xml', 'singermid': mid},
                headers={'Referer': 'https://y.qq.com/n/yqq/singer/'})

            singer_desc = singer_desc_page.find('./data/info/desc').text

        return self.playlist_result(entries, mid, singer_name, singer_desc)


class QQMusicAlbumIE(QQPlaylistBaseIE):
    IE_NAME = 'qqmusic:album'
    IE_DESC = 'QQ音乐 - 专辑'
    _VALID_URL = r'https?://y\.qq\.com/n/yqq/album/(?P<id>[0-9A-Za-z]+)\.html'

    _TESTS = [{
        'url': 'https://y.qq.com/n/yqq/album/000gXCTb2AhRR1.html',
        'info_dict': {
            'id': '000gXCTb2AhRR1',
            'title': '我们都是这样长大的',
            'description': 'md5:179c5dce203a5931970d306aa9607ea6',
        },
        'playlist_count': 4,
    }, {
        'url': 'https://y.qq.com/n/yqq/album/002Y5a3b3AlCu3.html',
        'info_dict': {
            'id': '002Y5a3b3AlCu3',
            'title': '그리고...',
            'description': 'md5:a48823755615508a95080e81b51ba729',
        },
        'playlist_count': 8,
    }]

    def _real_extract(self, url):
        mid = self._match_id(url)

        album = self._download_json(
            'http://i.y.qq.com/v8/fcg-bin/fcg_v8_album_info_cp.fcg?albummid=%s&format=json' % mid,
            mid, 'Download album page')['data']

        entries = [
            self.url_result(
                'https://y.qq.com/n/yqq/song/' + song['songmid'] + '.html', 'QQMusic', song['songmid']
            ) for song in album['list']
        ]
        album_name = album.get('name')
        album_detail = album.get('desc')
        if album_detail is not None:
            album_detail = album_detail.strip()

        return self.playlist_result(entries, mid, album_name, album_detail)


class QQMusicToplistIE(QQPlaylistBaseIE):
    IE_NAME = 'qqmusic:toplist'
    IE_DESC = 'QQ音乐 - 排行榜'
    _VALID_URL = r'https?://y\.qq\.com/n/yqq/toplist/(?P<id>[0-9]+)\.html'

    _TESTS = [{
        'url': 'https://y.qq.com/n/yqq/toplist/123.html',
        'info_dict': {
            'id': '123',
            'title': '美国iTunes榜',
            'description': 'md5:89db2335fdbb10678dee2d43fe9aba08',
        },
        'playlist_count': 100,
    }, {
        'url': 'https://y.qq.com/n/yqq/toplist/3.html',
        'info_dict': {
            'id': '3',
            'title': '巅峰榜·欧美',
            'description': 'md5:5a600d42c01696b26b71f8c4d43407da',
        },
        'playlist_count': 100,
    }, {
        'url': 'https://y.qq.com/n/yqq/toplist/106.html',
        'info_dict': {
            'id': '106',
            'title': '韩国Mnet榜',
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

        entries = [self.url_result(
            'https://y.qq.com/n/yqq/song/' + song['data']['songmid'] + '.html', 'QQMusic',
            song['data']['songmid'])
            for song in toplist_json['songlist']]

        topinfo = toplist_json.get('topinfo', {})
        list_name = topinfo.get('ListName')
        list_description = topinfo.get('info')
        return self.playlist_result(entries, list_id, list_name, list_description)


class QQMusicPlaylistIE(QQPlaylistBaseIE):
    IE_NAME = 'qqmusic:playlist'
    IE_DESC = 'QQ音乐 - 歌单'
    _VALID_URL = r'https?://y\.qq\.com/n/yqq/playlist/(?P<id>[0-9]+)\.html'

    _TESTS = [{
        'url': 'http://y.qq.com/n/yqq/playlist/3462654915.html',
        'info_dict': {
            'id': '3462654915',
            'title': '韩国5月新歌精选下旬',
            'description': 'md5:d2c9d758a96b9888cf4fe82f603121d4',
        },
        'playlist_count': 40,
        'skip': 'playlist gone',
    }, {
        'url': 'https://y.qq.com/n/yqq/playlist/1374105607.html',
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
            transform_source=strip_jsonp)
        if not len(list_json.get('cdlist', [])):
            if list_json.get('code'):
                raise ExtractorError(
                    'QQ Music said: error %d in fetching playlist info' % list_json['code'],
                    expected=True)
            raise ExtractorError('Unable to get playlist info')

        cdlist = list_json['cdlist'][0]
        entries = [self.url_result(
            'https://y.qq.com/n/yqq/song/' + song['songmid'] + '.html', 'QQMusic', song['songmid'])
            for song in cdlist['songlist']]

        list_name = cdlist.get('dissname')
        list_description = clean_html(unescapeHTML(cdlist.get('desc')))
        return self.playlist_result(entries, list_id, list_name, list_description)


class QQMusicVideoIE(InfoExtractor):
    _VALID_URL = r'https?://y\.qq\.com/n/ryqq/mv/(?P<id>[0-9A-Za-z]+)'

    def _parse_url_formats(self, url_data):
        formats = traverse_obj(url_data, ('mp4', lambda _, v: v.get('freeflow_url'), {
            'url': ('freeflow_url', 0, {url_or_none}),
            'filesize': ('fileSize', {int_or_none}),
            'format_id': ('newFileType', {str_or_none}),
        }))
        return formats

    def _real_extract(self, url):
        video_id = self._match_id(url)
        payload = '{"comm":{"format":"json","platform":"yqq"},"mvInfo":{"module":"music.video.VideoData","method":"get_video_info_batch","param":{"vidlist":["%s"],"required":["vid","type","sid","cover_pic","duration","singers","new_switch_str","video_pay","hint","code","msg","name","desc","playcnt","pubdate","isfav","fileid","filesize_v2","switch_pay_type","pay","pay_info","uploader_headurl","uploader_nick","uploader_uin","uploader_encuin","play_forbid_reason"]}},"mvUrl":{"module":"music.stream.MvUrlProxy","method":"GetMvUrls","param":{"vids":["%s"]}}}' % (video_id, video_id)
        video_info = self._download_json('https://u.y.qq.com/cgi-bin/musicu.fcg', video_id, data=payload.encode())
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
                'creator': ('singers', 0, 'name', {str_or_none}),
            })),
        }


class QQMusicVideoLiveIE(InfoExtractor):
    _VALID_URL = r'https?://v\.y\.qq\.com/m/play\.html\?showid=(?P<id>[0-9]+)'
    _HEIGHTS = {
        112: 720,
        110: 540,
    }

    def _parse_url_foramts(self, stream_info, stream_id):
        formats = []
        for url in traverse_obj(stream_info, ('req_0', 'data', ('streamFLV', 'streamHLS'), {url_or_none})):
            formats.append({
                'url': url,
                'quality': 10000,
                'format': '原画',
                'resolution': 'original',
            })
        for stream in traverse_obj(stream_info, ('req_0', 'data', ('streamFlvList', 'streamHlsList'), ..., {
            'url': ('stream', {url_or_none}),
            'format': ('text', {str_or_none}),
            'quality': ('resolution', {int_or_none}),
            'height': ('resolution', {lambda i: self._HEIGHTS.get(i)}),
        })):
            if stream['url']:
                formats.append(stream)
        return formats

    def _real_extract(self, url):
        stream_id = self._match_id(url)

        payload = '{"comm":{"format":"json","inCharset":"utf-8","outCharset":"utf-8","notice":0,"platform":"h5","needNewCode":1},"req_0":{"module":"mlive.show.MliveShowMemberSvr","method":"GetNewestShow","param":{"showID":%s}}}' % stream_id
        show_info = self._download_json('https://vc.y.qq.com/cgi-bin/musicu.fcg', stream_id, data=payload.encode())
        # import json
        # print(payload)
        # print(json.dumps(show_info, ensure_ascii=False))
        show_id = traverse_obj(show_info, ('req_0', 'data', 'showID'))

        payload = '{"comm":{"format":"json","inCharset":"utf-8","outCharset":"utf-8","notice":0,"platform":"h5","needNewCode":1},"req_0":{"module":"mlive.show.MliveShowMemberSvr","method":"JoinBasicShow","param":{"showID":%s,"uinStr":"v%.0f"}}}' % (show_id, time.time() * 1000)
        stream_info = self._download_json('https://vc.y.qq.com/cgi-bin/musicu.fcg', stream_id, data=payload.encode())
        # print(payload)
        # print(json.dumps(stream_info, ensure_ascii=False))

        formats = self._parse_url_foramts(stream_info, stream_id)
        if not formats and traverse_obj(stream_info, ('req_0', 'data', 'showInfo', 'liveType')) == 0:
            raise UserNotLive(video_id=stream_id)
        return {
            'id': stream_id,
            'formats': self._parse_url_foramts(stream_info, stream_id),
            'is_live': True,
            **traverse_obj(stream_info, ('req_0', 'data', 'showInfo', {
                'title': ('title', {str_or_none}),
                'thumbnail': ('cover_pic', {url_or_none}),
                'uploader_id': ('uin', {str_or_none}),
            })),
        }
