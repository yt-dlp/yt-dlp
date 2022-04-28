import random
import re
import time

from .common import InfoExtractor
from ..utils import (
    clean_html,
    ExtractorError,
    strip_jsonp,
    unescapeHTML,
)


class QQMusicIE(InfoExtractor):
    IE_NAME = 'qqmusic'
    IE_DESC = 'QQ音乐'
    _VALID_URL = r'https?://y\.qq\.com/n/yqq/song/(?P<id>[0-9A-Za-z]+)\.html'
    _TESTS = [{
        'url': 'https://y.qq.com/n/yqq/song/004295Et37taLD.html',
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

    # Reference: m_r_GetRUin() in top_player.js
    # http://imgcache.gtimg.cn/music/portal_v3/y/top_player.js
    @staticmethod
    def m_r_get_ruin():
        curMs = int(time.time() * 1000) % 1000
        return int(round(random.random() * 2147483647) * curMs % 1E10)

    def _real_extract(self, url):
        mid = self._match_id(url)

        detail_info_page = self._download_webpage(
            'http://s.plcloud.music.qq.com/fcgi-bin/fcg_yqq_song_detail_info.fcg?songmid=%s&play=0' % mid,
            mid, note='Download song detail info',
            errnote='Unable to get song detail info', encoding='gbk')

        song_name = self._html_search_regex(
            r"songname:\s*'([^']+)'", detail_info_page, 'song name')

        publish_time = self._html_search_regex(
            r'发行时间：(\d{4}-\d{2}-\d{2})', detail_info_page,
            'publish time', default=None)
        if publish_time:
            publish_time = publish_time.replace('-', '')

        singer = self._html_search_regex(
            r"singer:\s*'([^']+)", detail_info_page, 'singer', default=None)

        lrc_content = self._html_search_regex(
            r'<div class="content" id="lrc_content"[^<>]*>([^<>]+)</div>',
            detail_info_page, 'LRC lyrics', default=None)
        if lrc_content:
            lrc_content = lrc_content.replace('\\n', '\n')

        thumbnail_url = None
        albummid = self._search_regex(
            [r'albummid:\'([0-9a-zA-Z]+)\'', r'"albummid":"([0-9a-zA-Z]+)"'],
            detail_info_page, 'album mid', default=None)
        if albummid:
            thumbnail_url = 'http://i.gtimg.cn/music/photo/mid_album_500/%s/%s/%s.jpg' \
                            % (albummid[-2:-1], albummid[-1], albummid)

        guid = self.m_r_get_ruin()

        vkey = self._download_json(
            'http://base.music.qq.com/fcgi-bin/fcg_musicexpress.fcg?json=3&guid=%s' % guid,
            mid, note='Retrieve vkey', errnote='Unable to get vkey',
            transform_source=strip_jsonp)['key']

        formats = []
        for format_id, details in self._FORMATS.items():
            formats.append({
                'url': 'http://cc.stream.qqmusic.qq.com/%s%s.%s?vkey=%s&guid=%s&fromtag=0'
                       % (details['prefix'], mid, details['ext'], vkey, guid),
                'format': format_id,
                'format_id': format_id,
                'quality': details['preference'],
                'abr': details.get('abr'),
            })
        self._check_formats(formats, mid)
        self._sort_formats(formats)

        actual_lrc_lyrics = ''.join(
            line + '\n' for line in re.findall(
                r'(?m)^(\[[0-9]{2}:[0-9]{2}(?:\.[0-9]{2,})?\][^\n]*|\[[^\]]*\])', lrc_content))

        info_dict = {
            'id': mid,
            'formats': formats,
            'title': song_name,
            'release_date': publish_time,
            'creator': singer,
            'description': lrc_content,
            'thumbnail': thumbnail_url
        }
        if actual_lrc_lyrics:
            info_dict['subtitles'] = {
                'origin': [{
                    'ext': 'lrc',
                    'data': actual_lrc_lyrics,
                }]
            }
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
