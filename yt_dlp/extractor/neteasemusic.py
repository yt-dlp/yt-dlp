import itertools
import re
from base64 import b64encode
from datetime import datetime
from hashlib import md5

from .common import InfoExtractor
from ..compat import compat_str, compat_urllib_parse_urlencode
from ..utils import float_or_none, sanitized_Request


class NetEaseMusicBaseIE(InfoExtractor):
    _FORMATS = ['bMusic', 'mMusic', 'hMusic']
    _NETEASE_SALT = '3go8&$8*3*3h0k(2)2'
    _API_BASE = 'http://music.163.com/api/'

    @classmethod
    def _encrypt(cls, dfsid):
        salt_bytes = bytearray(cls._NETEASE_SALT.encode('utf-8'))
        string_bytes = bytearray(compat_str(dfsid).encode('ascii'))
        salt_len = len(salt_bytes)
        for i in range(len(string_bytes)):
            string_bytes[i] = string_bytes[i] ^ salt_bytes[i % salt_len]
        m = md5()
        m.update(bytes(string_bytes))
        result = b64encode(m.digest()).decode('ascii')
        return result.replace('/', '_').replace('+', '-')

    def extract_formats(self, info):
        formats = []
        for song_format in self._FORMATS:
            details = info.get(song_format)
            if not details:
                continue
            song_file_path = '/%s/%s.%s' % (
                self._encrypt(details['dfsId']), details['dfsId'], details['extension'])

            # 203.130.59.9, 124.40.233.182, 115.231.74.139, etc is a reverse proxy-like feature
            # from NetEase's CDN provider that can be used if m5.music.126.net does not
            # work, especially for users outside of Mainland China
            # via: https://github.com/JixunMoe/unblock-163/issues/3#issuecomment-163115880
            for host in ('http://m5.music.126.net', 'http://115.231.74.139/m1.music.126.net',
                         'http://124.40.233.182/m1.music.126.net', 'http://203.130.59.9/m1.music.126.net'):
                song_url = host + song_file_path
                if self._is_valid_url(song_url, info['id'], 'song'):
                    formats.append({
                        'url': song_url,
                        'ext': details.get('extension'),
                        'abr': float_or_none(details.get('bitrate'), scale=1000),
                        'format_id': song_format,
                        'filesize': details.get('size'),
                        'asr': details.get('sr')
                    })
                    break
        return formats

    @classmethod
    def convert_milliseconds(cls, ms):
        return int(round(ms / 1000.0))

    def query_api(self, endpoint, video_id, note):
        req = sanitized_Request('%s%s' % (self._API_BASE, endpoint))
        req.add_header('Referer', self._API_BASE)
        return self._download_json(req, video_id, note)


class NetEaseMusicIE(NetEaseMusicBaseIE):
    IE_NAME = 'netease:song'
    IE_DESC = '网易云音乐'
    _VALID_URL = r'https?://music\.163\.com/(#/)?song\?id=(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'http://music.163.com/#/song?id=32102397',
        'md5': 'f2e97280e6345c74ba9d5677dd5dcb45',
        'info_dict': {
            'id': '32102397',
            'ext': 'mp3',
            'title': 'Bad Blood (feat. Kendrick Lamar)',
            'creator': 'Taylor Swift / Kendrick Lamar',
            'upload_date': '20150517',
            'timestamp': 1431878400,
            'description': 'md5:a10a54589c2860300d02e1de821eb2ef',
        },
        'skip': 'Blocked outside Mainland China',
    }, {
        'note': 'No lyrics translation.',
        'url': 'http://music.163.com/#/song?id=29822014',
        'info_dict': {
            'id': '29822014',
            'ext': 'mp3',
            'title': '听见下雨的声音',
            'creator': '周杰伦',
            'upload_date': '20141225',
            'timestamp': 1419523200,
            'description': 'md5:a4d8d89f44656af206b7b2555c0bce6c',
        },
        'skip': 'Blocked outside Mainland China',
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
            'description': 'md5:79d99cc560e4ca97e0c4d86800ee4184',
            'upload_date': '20100127',
            'timestamp': 1264608000,
            'alt_title': '说出愿望吧(Genie)',
        },
        'skip': 'Blocked outside Mainland China',
    }]

    def _process_lyrics(self, lyrics_info):
        original = lyrics_info.get('lrc', {}).get('lyric')
        translated = lyrics_info.get('tlyric', {}).get('lyric')

        if not translated:
            return original

        lyrics_expr = r'(\[[0-9]{2}:[0-9]{2}\.[0-9]{2,}\])([^\n]+)'
        original_ts_texts = re.findall(lyrics_expr, original)
        translation_ts_dict = dict(
            (time_stamp, text) for time_stamp, text in re.findall(lyrics_expr, translated)
        )
        lyrics = '\n'.join([
            '%s%s / %s' % (time_stamp, text, translation_ts_dict.get(time_stamp, ''))
            for time_stamp, text in original_ts_texts
        ])
        return lyrics

    def _real_extract(self, url):
        song_id = self._match_id(url)

        params = {
            'id': song_id,
            'ids': '[%s]' % song_id
        }
        info = self.query_api(
            'song/detail?' + compat_urllib_parse_urlencode(params),
            song_id, 'Downloading song info')['songs'][0]

        formats = self.extract_formats(info)
        self._sort_formats(formats)

        lyrics_info = self.query_api(
            'song/lyric?id=%s&lv=-1&tv=-1' % song_id,
            song_id, 'Downloading lyrics data')
        lyrics = self._process_lyrics(lyrics_info)

        alt_title = None
        if info.get('transNames'):
            alt_title = '/'.join(info.get('transNames'))

        return {
            'id': song_id,
            'title': info['name'],
            'alt_title': alt_title,
            'creator': ' / '.join([artist['name'] for artist in info.get('artists', [])]),
            'timestamp': self.convert_milliseconds(info.get('album', {}).get('publishTime')),
            'thumbnail': info.get('album', {}).get('picUrl'),
            'duration': self.convert_milliseconds(info.get('duration', 0)),
            'description': lyrics,
            'formats': formats,
        }


class NetEaseMusicAlbumIE(NetEaseMusicBaseIE):
    IE_NAME = 'netease:album'
    IE_DESC = '网易云音乐 - 专辑'
    _VALID_URL = r'https?://music\.163\.com/(#/)?album\?id=(?P<id>[0-9]+)'
    _TEST = {
        'url': 'http://music.163.com/#/album?id=220780',
        'info_dict': {
            'id': '220780',
            'title': 'B\'day',
        },
        'playlist_count': 23,
        'skip': 'Blocked outside Mainland China',
    }

    def _real_extract(self, url):
        album_id = self._match_id(url)

        info = self.query_api(
            'album/%s?id=%s' % (album_id, album_id),
            album_id, 'Downloading album data')['album']

        name = info['name']
        desc = info.get('description')
        entries = [
            self.url_result('http://music.163.com/#/song?id=%s' % song['id'],
                            'NetEaseMusic', song['id'])
            for song in info['songs']
        ]
        return self.playlist_result(entries, album_id, name, desc)


class NetEaseMusicSingerIE(NetEaseMusicBaseIE):
    IE_NAME = 'netease:singer'
    IE_DESC = '网易云音乐 - 歌手'
    _VALID_URL = r'https?://music\.163\.com/(#/)?artist\?id=(?P<id>[0-9]+)'
    _TESTS = [{
        'note': 'Singer has aliases.',
        'url': 'http://music.163.com/#/artist?id=10559',
        'info_dict': {
            'id': '10559',
            'title': '张惠妹 - aMEI;阿密特',
        },
        'playlist_count': 50,
        'skip': 'Blocked outside Mainland China',
    }, {
        'note': 'Singer has translated name.',
        'url': 'http://music.163.com/#/artist?id=124098',
        'info_dict': {
            'id': '124098',
            'title': '李昇基 - 이승기',
        },
        'playlist_count': 50,
        'skip': 'Blocked outside Mainland China',
    }]

    def _real_extract(self, url):
        singer_id = self._match_id(url)

        info = self.query_api(
            'artist/%s?id=%s' % (singer_id, singer_id),
            singer_id, 'Downloading singer data')

        name = info['artist']['name']
        if info['artist']['trans']:
            name = '%s - %s' % (name, info['artist']['trans'])
        if info['artist']['alias']:
            name = '%s - %s' % (name, ';'.join(info['artist']['alias']))

        entries = [
            self.url_result('http://music.163.com/#/song?id=%s' % song['id'],
                            'NetEaseMusic', song['id'])
            for song in info['hotSongs']
        ]
        return self.playlist_result(entries, singer_id, name)


class NetEaseMusicListIE(NetEaseMusicBaseIE):
    IE_NAME = 'netease:playlist'
    IE_DESC = '网易云音乐 - 歌单'
    _VALID_URL = r'https?://music\.163\.com/(#/)?(playlist|discover/toplist)\?id=(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'http://music.163.com/#/playlist?id=79177352',
        'info_dict': {
            'id': '79177352',
            'title': 'Billboard 2007 Top 100',
            'description': 'md5:12fd0819cab2965b9583ace0f8b7b022'
        },
        'playlist_count': 99,
        'skip': 'Blocked outside Mainland China',
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

        info = self.query_api(
            'playlist/detail?id=%s&lv=-1&tv=-1' % list_id,
            list_id, 'Downloading playlist data')['result']

        name = info['name']
        desc = info.get('description')

        if info.get('specialType') == 10:  # is a chart/toplist
            datestamp = datetime.fromtimestamp(
                self.convert_milliseconds(info['updateTime'])).strftime('%Y-%m-%d')
            name = '%s %s' % (name, datestamp)

        entries = [
            self.url_result('http://music.163.com/#/song?id=%s' % song['id'],
                            'NetEaseMusic', song['id'])
            for song in info['tracks']
        ]
        return self.playlist_result(entries, list_id, name, desc)


class NetEaseMusicMvIE(NetEaseMusicBaseIE):
    IE_NAME = 'netease:mv'
    IE_DESC = '网易云音乐 - MV'
    _VALID_URL = r'https?://music\.163\.com/(#/)?mv\?id=(?P<id>[0-9]+)'
    _TEST = {
        'url': 'http://music.163.com/#/mv?id=415350',
        'info_dict': {
            'id': '415350',
            'ext': 'mp4',
            'title': '이럴거면 그러지말지',
            'description': '白雅言自作曲唱甜蜜爱情',
            'creator': '白雅言',
            'upload_date': '20150520',
        },
        'skip': 'Blocked outside Mainland China',
    }

    def _real_extract(self, url):
        mv_id = self._match_id(url)

        info = self.query_api(
            'mv/detail?id=%s&type=mp4' % mv_id,
            mv_id, 'Downloading mv info')['data']

        formats = [
            {'url': mv_url, 'ext': 'mp4', 'format_id': '%sp' % brs, 'height': int(brs)}
            for brs, mv_url in info['brs'].items()
        ]
        self._sort_formats(formats)

        return {
            'id': mv_id,
            'title': info['name'],
            'description': info.get('desc') or info.get('briefDesc'),
            'creator': info['artistName'],
            'upload_date': info['publishTime'].replace('-', ''),
            'formats': formats,
            'thumbnail': info.get('cover'),
            'duration': self.convert_milliseconds(info.get('duration', 0)),
        }


class NetEaseMusicProgramIE(NetEaseMusicBaseIE):
    IE_NAME = 'netease:program'
    IE_DESC = '网易云音乐 - 电台节目'
    _VALID_URL = r'https?://music\.163\.com/(#/?)program\?id=(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'http://music.163.com/#/program?id=10109055',
        'info_dict': {
            'id': '10109055',
            'ext': 'mp3',
            'title': '不丹足球背后的故事',
            'description': '喜马拉雅人的足球梦 ...',
            'creator': '大话西藏',
            'timestamp': 1434179342,
            'upload_date': '20150613',
            'duration': 900,
        },
        'skip': 'Blocked outside Mainland China',
    }, {
        'note': 'This program has accompanying songs.',
        'url': 'http://music.163.com/#/program?id=10141022',
        'info_dict': {
            'id': '10141022',
            'title': '25岁，你是自在如风的少年<27°C>',
            'description': 'md5:8d594db46cc3e6509107ede70a4aaa3b',
        },
        'playlist_count': 4,
        'skip': 'Blocked outside Mainland China',
    }, {
        'note': 'This program has accompanying songs.',
        'url': 'http://music.163.com/#/program?id=10141022',
        'info_dict': {
            'id': '10141022',
            'ext': 'mp3',
            'title': '25岁，你是自在如风的少年<27°C>',
            'description': 'md5:8d594db46cc3e6509107ede70a4aaa3b',
            'timestamp': 1434450841,
            'upload_date': '20150616',
        },
        'params': {
            'noplaylist': True
        },
        'skip': 'Blocked outside Mainland China',
    }]

    def _real_extract(self, url):
        program_id = self._match_id(url)

        info = self.query_api(
            'dj/program/detail?id=%s' % program_id,
            program_id, 'Downloading program info')['program']

        name = info['name']
        description = info['description']

        if not self._yes_playlist(info['songs'] and program_id, info['mainSong']['id']):
            formats = self.extract_formats(info['mainSong'])
            self._sort_formats(formats)

            return {
                'id': info['mainSong']['id'],
                'title': name,
                'description': description,
                'creator': info['dj']['brand'],
                'timestamp': self.convert_milliseconds(info['createTime']),
                'thumbnail': info['coverUrl'],
                'duration': self.convert_milliseconds(info.get('duration', 0)),
                'formats': formats,
            }

        song_ids = [info['mainSong']['id']]
        song_ids.extend([song['id'] for song in info['songs']])
        entries = [
            self.url_result('http://music.163.com/#/song?id=%s' % song_id,
                            'NetEaseMusic', song_id)
            for song_id in song_ids
        ]
        return self.playlist_result(entries, program_id, name, description)


class NetEaseMusicDjRadioIE(NetEaseMusicBaseIE):
    IE_NAME = 'netease:djradio'
    IE_DESC = '网易云音乐 - 电台'
    _VALID_URL = r'https?://music\.163\.com/(#/)?djradio\?id=(?P<id>[0-9]+)'
    _TEST = {
        'url': 'http://music.163.com/#/djradio?id=42',
        'info_dict': {
            'id': '42',
            'title': '声音蔓延',
            'description': 'md5:766220985cbd16fdd552f64c578a6b15'
        },
        'playlist_mincount': 40,
        'skip': 'Blocked outside Mainland China',
    }
    _PAGE_SIZE = 1000

    def _real_extract(self, url):
        dj_id = self._match_id(url)

        name = None
        desc = None
        entries = []
        for offset in itertools.count(start=0, step=self._PAGE_SIZE):
            info = self.query_api(
                'dj/program/byradio?asc=false&limit=%d&radioId=%s&offset=%d'
                % (self._PAGE_SIZE, dj_id, offset),
                dj_id, 'Downloading dj programs - %d' % offset)

            entries.extend([
                self.url_result(
                    'http://music.163.com/#/program?id=%s' % program['id'],
                    'NetEaseMusicProgram', program['id'])
                for program in info['programs']
            ])

            if name is None:
                radio = info['programs'][0]['radio']
                name = radio['name']
                desc = radio['desc']

            if not info['more']:
                break

        return self.playlist_result(entries, dj_id, name, desc)
