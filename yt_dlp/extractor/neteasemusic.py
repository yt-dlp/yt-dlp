import itertools
import json
import re
import time
from hashlib import md5
from random import randint

from .common import InfoExtractor
from ..aes import aes_ecb_encrypt, pkcs7_padding
from ..utils import (
    ExtractorError,
    int_or_none,
    join_nonempty,
    str_or_none,
    strftime_or_none,
    traverse_obj,
    unified_strdate,
    url_or_none,
    urljoin,
    variadic,
)


class NetEaseMusicBaseIE(InfoExtractor):
    _FORMATS = ['bMusic', 'mMusic', 'hMusic']
    _API_BASE = 'http://music.163.com/api/'
    _GEO_BYPASS = False

    @staticmethod
    def kilo_or_none(value):
        return int_or_none(value, scale=1000)

    def _create_eapi_cipher(self, api_path, query_body, cookies):
        request_text = json.dumps({**query_body, 'header': cookies}, separators=(',', ':'))

        message = f'nobody{api_path}use{request_text}md5forencrypt'.encode('latin1')
        msg_digest = md5(message).hexdigest()

        data = pkcs7_padding(list(str.encode(
            f'{api_path}-36cd479b6b5-{request_text}-36cd479b6b5-{msg_digest}')))
        encrypted = bytes(aes_ecb_encrypt(data, list(b'e82ckenh8dichen8')))
        return f'params={encrypted.hex().upper()}'.encode()

    def _download_eapi_json(self, path, video_id, query_body, headers={}, **kwargs):
        cookies = {
            'osver': 'undefined',
            'deviceId': 'undefined',
            'appver': '8.0.0',
            'versioncode': '140',
            'mobilename': 'undefined',
            'buildver': '1623435496',
            'resolution': '1920x1080',
            '__csrf': '',
            'os': 'pc',
            'channel': 'undefined',
            'requestId': f'{int(time.time() * 1000)}_{randint(0, 1000):04}',
            **traverse_obj(self._get_cookies(self._API_BASE), {
                'MUSIC_U': ('MUSIC_U', {lambda i: i.value}),
            })
        }
        return self._download_json(
            urljoin('https://interface3.music.163.com/', f'/eapi{path}'), video_id,
            data=self._create_eapi_cipher(f'/api{path}', query_body, cookies), headers={
                'Referer': 'https://music.163.com',
                'Cookie': '; '.join([f'{k}={v}' for k, v in cookies.items()]),
                **headers,
            }, **kwargs)

    def _call_player_api(self, song_id, bitrate):
        return self._download_eapi_json(
            '/song/enhance/player/url', song_id, {'ids': f'[{song_id}]', 'br': bitrate},
            note=f'Downloading song URL info: bitrate {bitrate}')

    def extract_formats(self, info):
        err = 0
        formats = []
        song_id = info['id']
        for song_format in self._FORMATS:
            details = info.get(song_format)
            if not details:
                continue
            bitrate = int_or_none(details.get('bitrate')) or 999000
            for song in traverse_obj(self._call_player_api(song_id, bitrate), ('data', lambda _, v: url_or_none(v['url']))):
                song_url = song['url']
                if self._is_valid_url(song_url, info['id'], 'song'):
                    formats.append({
                        'url': song_url,
                        'format_id': song_format,
                        'asr': traverse_obj(details, ('sr', {int_or_none})),
                        **traverse_obj(song, {
                            'ext': ('type', {str}),
                            'abr': ('br', {self.kilo_or_none}),
                            'filesize': ('size', {int_or_none}),
                        }),
                    })
                elif err == 0:
                    err = traverse_obj(song, ('code', {int})) or 0

        if not formats:
            if err != 0 and (err < 200 or err >= 400):
                raise ExtractorError(f'No media links found (site code {err})', expected=True)
            else:
                self.raise_geo_restricted(
                    'No media links found: probably due to geo restriction.', countries=['CN'])
        return formats

    def query_api(self, endpoint, video_id, note):
        result = self._download_json(
            f'{self._API_BASE}{endpoint}', video_id, note, headers={'Referer': self._API_BASE})
        code = traverse_obj(result, ('code', {int}))
        message = traverse_obj(result, ('message', {str})) or ''
        if code == -462:
            self.raise_login_required(f'Login required to download: {message}')
        elif code != 200:
            raise ExtractorError(f'Failed to get meta info: {code} {message}')
        return result

    def _get_entries(self, songs_data, entry_keys=None, id_key='id', name_key='name'):
        for song in traverse_obj(songs_data, (
                *variadic(entry_keys, (str, bytes, dict, set)),
                lambda _, v: int_or_none(v[id_key]) is not None)):
            song_id = str(song[id_key])
            yield self.url_result(
                f'http://music.163.com/#/song?id={song_id}', NetEaseMusicIE,
                song_id, traverse_obj(song, (name_key, {str})))


class NetEaseMusicIE(NetEaseMusicBaseIE):
    IE_NAME = 'netease:song'
    IE_DESC = '网易云音乐'
    _VALID_URL = r'https?://(y\.)?music\.163\.com/(?:[#m]/)?song\?.*?\bid=(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://music.163.com/#/song?id=548648087',
        'info_dict': {
            'id': '548648087',
            'ext': 'mp3',
            'title': '戒烟 (Live)',
            'creator': '李荣浩 / 朱正廷 / 陈立农 / 尤长靖 / ONER灵超 / ONER木子洋 / 杨非同 / 陆定昊',
            'timestamp': 1522944000,
            'upload_date': '20180405',
            'description': 'md5:3650af9ee22c87e8637cb2dde22a765c',
            'subtitles': {'lyrics': [{'ext': 'lrc'}]},
            "duration": 256,
            'thumbnail': r're:^http.*\.jpg',
        },
    }, {
        'note': 'No lyrics.',
        'url': 'http://music.163.com/song?id=17241424',
        'info_dict': {
            'id': '17241424',
            'ext': 'mp3',
            'title': 'Opus 28',
            'creator': 'Dustin O\'Halloran',
            'upload_date': '20080211',
            'timestamp': 1202745600,
            'duration': 263,
            'thumbnail': r're:^http.*\.jpg',
        },
    }, {
        'url': 'https://y.music.163.com/m/song?app_version=8.8.45&id=95670&uct2=sKnvS4+0YStsWkqsPhFijw%3D%3D&dlt=0846',
        'md5': '95826c73ea50b1c288b22180ec9e754d',
        'info_dict': {
            'id': '95670',
            'ext': 'mp3',
            'title': '国际歌',
            'creator': '马备',
            'upload_date': '19911130',
            'timestamp': 691516800,
            'description': 'md5:1ba2f911a2b0aa398479f595224f2141',
            'subtitles': {'lyrics': [{'ext': 'lrc'}]},
            'duration': 268,
            'alt_title': '伴唱:现代人乐队 合唱:总政歌舞团',
            'thumbnail': r're:^http.*\.jpg',
        },
    }, {
        'url': 'http://music.163.com/#/song?id=32102397',
        'md5': '3e909614ce09b1ccef4a3eb205441190',
        'info_dict': {
            'id': '32102397',
            'ext': 'mp3',
            'title': 'Bad Blood',
            'creator': 'Taylor Swift / Kendrick Lamar',
            'upload_date': '20150516',
            'timestamp': 1431792000,
            'description': 'md5:21535156efb73d6d1c355f95616e285a',
            'subtitles': {'lyrics': [{'ext': 'lrc'}]},
            'duration': 199,
            'thumbnail': r're:^http.*\.jpg',
        },
        'skip': 'Blocked outside Mainland China',
    }, {
        'note': 'Has translated name.',
        'url': 'http://music.163.com/#/song?id=22735043',
        'info_dict': {
            'id': '22735043',
            'ext': 'mp3',
            'title': '소원을 말해봐 (Genie)',
            'creator': '少女时代',
            'upload_date': '20100127',
            'timestamp': 1264608000,
            'description': 'md5:03d1ffebec3139aa4bafe302369269c5',
            'subtitles': {'lyrics': [{'ext': 'lrc'}]},
            'duration': 229,
            'alt_title': '说出愿望吧(Genie)',
            'thumbnail': r're:^http.*\.jpg',
        },
        'skip': 'Blocked outside Mainland China',
    }]

    def _process_lyrics(self, lyrics_info):
        original = traverse_obj(lyrics_info, ('lrc', 'lyric', {str}))
        translated = traverse_obj(lyrics_info, ('tlyric', 'lyric', {str}))

        if not original or original == '[99:00.00]纯音乐，请欣赏\n':
            return None

        if not translated:
            return {
                'lyrics': [{'data': original, 'ext': 'lrc'}],
            }

        lyrics_expr = r'(\[[0-9]{2}:[0-9]{2}\.[0-9]{2,}\])([^\n]+)'
        original_ts_texts = re.findall(lyrics_expr, original)
        translation_ts_dict = dict(re.findall(lyrics_expr, translated))

        merged = '\n'.join(
            join_nonempty(f'{timestamp}{text}', translation_ts_dict.get(timestamp, ''), delim=' / ')
            for timestamp, text in original_ts_texts)

        return {
            'lyrics_merged': [{'data': merged, 'ext': 'lrc'}],
            'lyrics': [{'data': original, 'ext': 'lrc'}],
            'lyrics_translated': [{'data': translated, 'ext': 'lrc'}],
        }

    def _real_extract(self, url):
        song_id = self._match_id(url)

        info = self.query_api(
            f'song/detail?id={song_id}&ids=%5B{song_id}%5D', song_id, 'Downloading song info')['songs'][0]

        formats = self.extract_formats(info)

        lyrics = self._process_lyrics(self.query_api(
            f'song/lyric?id={song_id}&lv=-1&tv=-1', song_id, 'Downloading lyrics data'))
        lyric_data = {
            'description': traverse_obj(lyrics, (('lyrics_merged', 'lyrics'), 0, 'data'), get_all=False),
            'subtitles': lyrics,
        } if lyrics else {}

        return {
            'id': song_id,
            'formats': formats,
            'alt_title': '/'.join(traverse_obj(info, (('transNames', 'alias'), ...))) or None,
            'creator': ' / '.join(traverse_obj(info, ('artists', ..., 'name'))) or None,
            **lyric_data,
            **traverse_obj(info, {
                'title': ('name', {str}),
                'timestamp': ('album', 'publishTime', {self.kilo_or_none}),
                'thumbnail': ('album', 'picUrl', {url_or_none}),
                'duration': ('duration', {self.kilo_or_none}),
            }),
        }


class NetEaseMusicAlbumIE(NetEaseMusicBaseIE):
    IE_NAME = 'netease:album'
    IE_DESC = '网易云音乐 - 专辑'
    _VALID_URL = r'https?://music\.163\.com/(#/)?album\?id=(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://music.163.com/#/album?id=133153666',
        'info_dict': {
            'id': '133153666',
            'title': '桃几的翻唱',
            'upload_date': '20210913',
            'description': '桃几2021年翻唱合集',
            'thumbnail': r're:^http.*\.jpg',
        },
        'playlist_mincount': 13,
    }, {
        'url': 'http://music.163.com/#/album?id=220780',
        'info_dict': {
            'id': '220780',
            'title': 'B\'Day',
            'upload_date': '20060904',
            'description': 'md5:71a74e1d8f392d88cf1bbe48879ad0b0',
            'thumbnail': r're:^http.*\.jpg',
        },
        'playlist_count': 23,
    }]

    def _real_extract(self, url):
        album_id = self._match_id(url)
        webpage = self._download_webpage(f'https://music.163.com/album?id={album_id}', album_id)

        songs = self._search_json(
            r'<textarea[^>]+\bid="song-list-pre-data"[^>]*>', webpage, 'metainfo', album_id,
            end_pattern=r'</textarea>', contains_pattern=r'\[(?s:.+)\]')
        metainfo = {
            'title': self._og_search_property('title', webpage, 'title', fatal=False),
            'description': self._html_search_regex(
                (rf'<div[^>]+\bid="album-desc-{suffix}"[^>]*>(.*?)</div>' for suffix in ('more', 'dot')),
                webpage, 'description', flags=re.S, fatal=False),
            'thumbnail': self._og_search_property('image', webpage, 'thumbnail', fatal=False),
            'upload_date': unified_strdate(self._html_search_meta('music:release_date', webpage, 'date', fatal=False)),
        }
        return self.playlist_result(self._get_entries(songs), album_id, **metainfo)


class NetEaseMusicSingerIE(NetEaseMusicBaseIE):
    IE_NAME = 'netease:singer'
    IE_DESC = '网易云音乐 - 歌手'
    _VALID_URL = r'https?://music\.163\.com/(#/)?artist\?id=(?P<id>[0-9]+)'
    _TESTS = [{
        'note': 'Singer has aliases.',
        'url': 'http://music.163.com/#/artist?id=10559',
        'info_dict': {
            'id': '10559',
            'title': '张惠妹 - aMEI;阿妹;阿密特',
        },
        'playlist_count': 50,
    }, {
        'note': 'Singer has translated name.',
        'url': 'http://music.163.com/#/artist?id=124098',
        'info_dict': {
            'id': '124098',
            'title': '李昇基 - 이승기',
        },
        'playlist_count': 50,
    }, {
        'note': 'Singer with both translated and alias',
        'url': 'https://music.163.com/#/artist?id=159692',
        'info_dict': {
            'id': '159692',
            'title': '初音ミク - 初音未来;Hatsune Miku',
        },
        'playlist_count': 50,
    }]

    def _real_extract(self, url):
        singer_id = self._match_id(url)

        info = self.query_api(
            f'artist/{singer_id}?id={singer_id}', singer_id, note='Downloading singer data')

        name = join_nonempty(
            traverse_obj(info, ('artist', 'name', {str})),
            join_nonempty(*traverse_obj(info, ('artist', ('trans', ('alias', ...)), {str})), delim=';'),
            delim=' - ')

        return self.playlist_result(self._get_entries(info, 'hotSongs'), singer_id, name)


class NetEaseMusicListIE(NetEaseMusicBaseIE):
    IE_NAME = 'netease:playlist'
    IE_DESC = '网易云音乐 - 歌单'
    _VALID_URL = r'https?://music\.163\.com/(#/)?(playlist|discover/toplist)\?id=(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'http://music.163.com/#/playlist?id=79177352',
        'info_dict': {
            'id': '79177352',
            'title': 'Billboard 2007 Top 100',
            'description': 'md5:12fd0819cab2965b9583ace0f8b7b022',
            'tags': ['欧美'],
            'uploader': '浑然破灭',
            'uploader_id': '67549805',
            'timestamp': int,
            'upload_date': r're:\d{8}',
        },
        'playlist_mincount': 95,
    }, {
        'note': 'Toplist/Charts sample',
        'url': 'https://music.163.com/#/discover/toplist?id=60198',
        'info_dict': {
            'id': '60198',
            'title': 're:美国Billboard榜 [0-9]{4}-[0-9]{2}-[0-9]{2}',
            'description': '美国Billboard排行榜',
            'tags': ['流行', '欧美', '榜单'],
            'uploader': 'Billboard公告牌',
            'uploader_id': '48171',
            'timestamp': int,
            'upload_date': r're:\d{8}',
        },
        'playlist_count': 100,
    }, {
        'note': 'Toplist/Charts sample',
        'url': 'http://music.163.com/#/discover/toplist?id=3733003',
        'info_dict': {
            'id': '3733003',
            'title': 're:韩国Melon排行榜周榜 [0-9]{4}-[0-9]{2}-[0-9]{2}',
            'description': 'md5:73ec782a612711cadc7872d9c1e134fc',
        },
        'playlist_count': 50,
        'skip': 'Blocked outside Mainland China',
    }]

    def _real_extract(self, url):
        list_id = self._match_id(url)

        info = self._download_eapi_json(
            '/v3/playlist/detail', list_id,
            {'id': list_id, 't': '-1', 'n': '500', 's': '0'},
            note="Downloading playlist info")

        metainfo = traverse_obj(info, ('playlist', {
            'title': ('name', {str}),
            'description': ('description', {str}),
            'tags': ('tags', ..., {str}),
            'uploader': ('creator', 'nickname', {str}),
            'uploader_id': ('creator', 'userId', {str_or_none}),
            'timestamp': ('updateTime', {self.kilo_or_none}),
        }))
        if traverse_obj(info, ('playlist', 'specialType')) == 10:
            metainfo['title'] = f'{metainfo.get("title")} {strftime_or_none(metainfo.get("timestamp"), "%Y-%m-%d")}'

        return self.playlist_result(self._get_entries(info, ('playlist', 'tracks')), list_id, **metainfo)


class NetEaseMusicMvIE(NetEaseMusicBaseIE):
    IE_NAME = 'netease:mv'
    IE_DESC = '网易云音乐 - MV'
    _VALID_URL = r'https?://music\.163\.com/(#/)?mv\?id=(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://music.163.com/#/mv?id=10958064',
        'info_dict': {
            'id': '10958064',
            'ext': 'mp4',
            'title': '交换余生',
            'description': 'md5:e845872cff28820642a2b02eda428fea',
            'creator': '林俊杰',
            'upload_date': '20200916',
            'thumbnail': r're:http.*\.jpg',
            'duration': 364,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
        },
    }, {
        'url': 'http://music.163.com/#/mv?id=415350',
        'info_dict': {
            'id': '415350',
            'ext': 'mp4',
            'title': '이럴거면 그러지말지',
            'description': '白雅言自作曲唱甜蜜爱情',
            'creator': '白娥娟',
            'upload_date': '20150520',
            'thumbnail': r're:http.*\.jpg',
            'duration': 216,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
        },
    }]

    def _real_extract(self, url):
        mv_id = self._match_id(url)

        info = self.query_api(
            f'mv/detail?id={mv_id}&type=mp4', mv_id, 'Downloading mv info')['data']

        formats = [
            {'url': mv_url, 'ext': 'mp4', 'format_id': f'{brs}p', 'height': int_or_none(brs)}
            for brs, mv_url in info['brs'].items()
        ]

        return {
            'id': mv_id,
            'formats': formats,
            **traverse_obj(info, {
                'title': ('name', {str}),
                'description': (('desc', 'briefDesc'), {str}, {lambda x: x or None}),
                'creator': ('artistName', {str}),
                'upload_date': ('publishTime', {unified_strdate}),
                'thumbnail': ('cover', {url_or_none}),
                'duration': ('duration', {self.kilo_or_none}),
                'view_count': ('playCount', {int_or_none}),
                'like_count': ('likeCount', {int_or_none}),
                'comment_count': ('commentCount', {int_or_none}),
            }, get_all=False),
        }


class NetEaseMusicProgramIE(NetEaseMusicBaseIE):
    IE_NAME = 'netease:program'
    IE_DESC = '网易云音乐 - 电台节目'
    _VALID_URL = r'https?://music\.163\.com/(#/?)program\?id=(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'http://music.163.com/#/program?id=10109055',
        'info_dict': {
            'id': '32593346',
            'ext': 'mp3',
            'title': '不丹足球背后的故事',
            'description': '喜马拉雅人的足球梦 ...',
            'creator': '大话西藏',
            'timestamp': 1434179287,
            'upload_date': '20150613',
            'thumbnail': r're:http.*\.jpg',
            'duration': 900,
        },
    }, {
        'note': 'This program has accompanying songs.',
        'url': 'http://music.163.com/#/program?id=10141022',
        'info_dict': {
            'id': '10141022',
            'title': '滚滚电台的有声节目',
            'description': 'md5:8d594db46cc3e6509107ede70a4aaa3b',
            'creator': '滚滚电台ORZ',
            'timestamp': 1434450733,
            'upload_date': '20150616',
            'thumbnail': r're:http.*\.jpg',
        },
        'playlist_count': 4,
    }, {
        'note': 'This program has accompanying songs.',
        'url': 'http://music.163.com/#/program?id=10141022',
        'info_dict': {
            'id': '32647209',
            'ext': 'mp3',
            'title': '滚滚电台的有声节目',
            'description': 'md5:8d594db46cc3e6509107ede70a4aaa3b',
            'creator': '滚滚电台ORZ',
            'timestamp': 1434450733,
            'upload_date': '20150616',
            'thumbnail': r're:http.*\.jpg',
            'duration': 1104,
        },
        'params': {
            'noplaylist': True
        },
    }]

    def _real_extract(self, url):
        program_id = self._match_id(url)

        info = self.query_api(
            f'dj/program/detail?id={program_id}', program_id, note='Downloading program info')['program']

        metainfo = traverse_obj(info, {
            'title': ('name', {str}),
            'description': ('description', {str}),
            'creator': ('dj', 'brand', {str}),
            'thumbnail': ('coverUrl', {url_or_none}),
            'timestamp': ('createTime', {self.kilo_or_none}),
        })

        if not self._yes_playlist(info['songs'] and program_id, info['mainSong']['id']):
            formats = self.extract_formats(info['mainSong'])

            return {
                'id': str(info['mainSong']['id']),
                'formats': formats,
                'duration': traverse_obj(info, ('mainSong', 'duration', {self.kilo_or_none})),
                **metainfo,
            }

        songs = traverse_obj(info, (('mainSong', ('songs', ...)),))
        return self.playlist_result(self._get_entries(songs), program_id, **metainfo)


class NetEaseMusicDjRadioIE(NetEaseMusicBaseIE):
    IE_NAME = 'netease:djradio'
    IE_DESC = '网易云音乐 - 电台'
    _VALID_URL = r'https?://music\.163\.com/(#/)?djradio\?id=(?P<id>[0-9]+)'
    _TEST = {
        'url': 'http://music.163.com/#/djradio?id=42',
        'info_dict': {
            'id': '42',
            'title': '声音蔓延',
            'description': 'md5:c7381ebd7989f9f367668a5aee7d5f08'
        },
        'playlist_mincount': 40,
    }
    _PAGE_SIZE = 1000

    def _real_extract(self, url):
        dj_id = self._match_id(url)

        metainfo = {}
        entries = []
        for offset in itertools.count(start=0, step=self._PAGE_SIZE):
            info = self.query_api(
                f'dj/program/byradio?asc=false&limit={self._PAGE_SIZE}&radioId={dj_id}&offset={offset}',
                dj_id, note=f'Downloading dj programs - {offset}')

            entries.extend(self.url_result(
                f'http://music.163.com/#/program?id={program["id"]}', NetEaseMusicProgramIE,
                program['id'], program.get('name')) for program in info['programs'])
            if not metainfo:
                metainfo = traverse_obj(info, ('programs', 0, 'radio', {
                    'title': ('name', {str}),
                    'description': ('desc', {str}),
                }))

            if not info['more']:
                break

        return self.playlist_result(entries, dj_id, **metainfo)
