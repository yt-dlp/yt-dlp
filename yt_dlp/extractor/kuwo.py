import re

from .common import InfoExtractor
from ..compat import compat_urlparse
from ..utils import (
    get_element_by_id,
    clean_html,
    ExtractorError,
    InAdvancePagedList,
    remove_start,
)


class KuwoBaseIE(InfoExtractor):
    _FORMATS = [
        {'format': 'ape', 'ext': 'ape', 'preference': 100},
        {'format': 'mp3-320', 'ext': 'mp3', 'br': '320kmp3', 'abr': 320, 'preference': 80},
        {'format': 'mp3-192', 'ext': 'mp3', 'br': '192kmp3', 'abr': 192, 'preference': 70},
        {'format': 'mp3-128', 'ext': 'mp3', 'br': '128kmp3', 'abr': 128, 'preference': 60},
        {'format': 'wma', 'ext': 'wma', 'preference': 20},
        {'format': 'aac', 'ext': 'aac', 'abr': 48, 'preference': 10}
    ]

    def _get_formats(self, song_id, tolerate_ip_deny=False):
        formats = []
        for file_format in self._FORMATS:
            query = {
                'format': file_format['ext'],
                'br': file_format.get('br', ''),
                'rid': 'MUSIC_%s' % song_id,
                'type': 'convert_url',
                'response': 'url'
            }

            song_url = self._download_webpage(
                'http://antiserver.kuwo.cn/anti.s',
                song_id, note='Download %s url info' % file_format['format'],
                query=query, headers=self.geo_verification_headers(),
            )

            if song_url == 'IPDeny' and not tolerate_ip_deny:
                raise ExtractorError('This song is blocked in this region', expected=True)

            if song_url.startswith('http://') or song_url.startswith('https://'):
                formats.append({
                    'url': song_url,
                    'format_id': file_format['format'],
                    'format': file_format['format'],
                    'quality': file_format['preference'],
                    'abr': file_format.get('abr'),
                })

        return formats


class KuwoIE(KuwoBaseIE):
    IE_NAME = 'kuwo:song'
    IE_DESC = '酷我音乐'
    _VALID_URL = r'https?://(?:www\.)?kuwo\.cn/yinyue/(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.kuwo.cn/yinyue/635632/',
        'info_dict': {
            'id': '635632',
            'ext': 'ape',
            'title': '爱我别走',
            'creator': '张震岳',
            'upload_date': '20080122',
            'description': 'md5:ed13f58e3c3bf3f7fd9fbc4e5a7aa75c'
        },
        'skip': 'this song has been offline because of copyright issues',
    }, {
        'url': 'http://www.kuwo.cn/yinyue/6446136/',
        'info_dict': {
            'id': '6446136',
            'ext': 'mp3',
            'title': '心',
            'description': 'md5:589730b2111d5ac605689d15e5d25926',
            'upload_date': '20130527',
        }
    }]

    def _real_extract(self, url):
        song_id = self._match_id(url)
        song_info = self._download_json(
            'http://www.kuwo.cn/api/www/music/musicInfo?mid=MUSIC_%s' % song_id,
            song_id, 'Downloading song info JSON',
            query={
                'httpsStatus': '1',
                'reqId': 'd8dc5d10-4dc0-11eb-aae6-cfdb349a8527',
            },
        )['data']
        title = song_info['songName']
        creator = song_info.get('artist')
        upload_date = song_info.get('releaseDate')
        description = song_info.get('remark')
        formats = self._get_formats(song_id)
        self._sort_formats(formats)

        return {
            'id': song_id,
            'title': title,
            'creator': creator,
            'upload_date': upload_date,
            'description': description,
            'formats': formats,
        }


class KuwoPlaylistIE(KuwoBaseIE):
    IE_NAME = 'kuwo:playlist'
    IE_DESC = '酷我音乐-歌单'
    _VALID_URL = r'https?://(?:www\.)?kuwo\.cn/playlist/(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.kuwo.cn/playlist/2693096540',
        'info_dict': {
            'id': '2693096540',
            'title': '我的播放',
            'description': 'md5:e6002f88337d21e4f4d92bfb6e80d20b',
        },
        'playlist_mincount': 91,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        playlist_info = self._download_json(
            'http://www.kuwo.cn/api/www/playlist/playlistInfo',
            playlist_id, 'Downloading playlist info JSON',
            query={
                'pid': playlist_id,
                'httpsStatus': '1',
                'reqId': 'd8dc5d10-4dc0-11eb-aae6-cfdb349a8527',
            },
        )['data']
        title = playlist_info['name']
        description = playlist_info.get('desc')

        tracks = playlist_info['musicList']
        entries = []
        for track in tracks:
            song_id = track['rid']
            song_info = track['songInfo']
            title = song_info['songName']
            creator = song_info.get('artist')
            upload_date = song_info.get('releaseDate')
            description = song_info.get('remark')
            formats = self._get_formats(song_id)
            self._sort_formats(formats)

            entries.append({
                'id': song_id,
                'title': title,
                'creator': creator,
                'upload_date': upload_date,
                'description': description,
                'formats': formats,
            })

        return {
            '_type': 'playlist',
            'id': playlist_id,
            'title': title,
            'description': description,
            'entries': entries,
        }


class KuwoAlbumIE(KuwoBaseIE):
    IE_NAME = 'kuwo:album'
    IE_DESC = '酷我音乐-专辑'
    _VALID_URL = r'https?://(?:www\.)?kuwo\.cn/album/(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.kuwo.cn/album/237898/',
        'info_dict': {
            'id': '237898',
            'title': '自传',
            'description': 'md5:83c9675ee1223ae0914e14db20576d2f',
        },
        'playlist_mincount': 9,
    }]

    def _real_extract(self, url):
        album_id = self._match_id(url)
        album_info = self._download_json(
            'http://www.kuwo.cn/api/www/album/albumInfo',
            album_id, 'Downloading album info JSON',
            query={
                'albumId': album_id,
                'httpsStatus': '1',
                'reqId': 'd8dc5d10-4dc0-11eb-aae6-cfdb349a8527',
            },
        )['data']
        title = album_info['name']
        description = album_info.get('info')

        tracks = album_info['musicList']
        entries = []
        for track in tracks:
            song_id = track['rid']
            song_info = track['songInfo']
            title = song_info['songName']
            creator = song_info.get('artist')
            upload_date = song_info.get('releaseDate')
            description = song_info.get('remark')
            formats = self._get_formats(song_id)
            self._sort_formats(formats)

            entries.append({
                'id': song_id,
                'title': title,
                'creator': creator,
                'upload_date': upload_date,
                'description': description,
                'formats': formats,
            })

        return {
            '_type': 'playlist',
            'id': album_id,
            'title': title,
            'description': description,
            'entries': entries,
        }


class KuwoMvIE(InfoExtractor):
    IE_NAME = 'kuwo:mv'
    IE_DESC = '酷我音乐-MV'
    _VALID_URL = r'https?://(?:www\.)?kuwo\.cn/mv/(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.kuwo.cn/mv/5551468',
        'info_dict': {
            'id': '5551468',
            'ext': 'mp4',
            'title': '雅俗共赏',
            'creator': '许嵩',
            'upload_date': '20160525',
            'description': 'md5:4ea597e5594a8dbd88e6021d97c17f3c'
        },
    }]

    def _real_extract(self, url):
        mv_id = self._match_id(url)
        mv_info = self._download_json(
            'http://www.kuwo.cn/api/www/mv/mvInfo',
            mv_id, 'Downloading mv info JSON',
            query={
                'rid': mv_id,
                'httpsStatus': '1',
                'reqId': 'd8dc5d10-4dc0-11eb-aae6-cfdb349a8527',
            },
        )['data']
        title = mv_info['name']
        creator = mv_info.get('artist')
        upload_date = mv_info.get('publishTime')
        description = mv_info.get('remark')
        formats = []
        for file_info in mv_info['urlList']:
            if file_info.get('isPlay', 0):
                formats.append({
                    'url': file_info['url'],
                    'format_id': file_info['type'],
                    'ext': file_info['type'],
                    'quality': 1 if file_info.get('isHd') else 0,
                })
        self._sort_formats(formats)

        return {
            'id': mv_id,
            'title': title,
            'creator': creator,
            'upload_date': upload_date,
            'description': description,
            'formats': formats,
        }


class KuwoUserIE(InfoExtractor):
    IE_NAME = 'kuwo:user'
    IE_DESC = '酷我音乐-用户'
    _VALID_URL = r'https?://(?:www\.)?kuwo\.cn/user/(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.kuwo.cn/user/368202605',
        'info_dict': {
            'id': '368202605',
            'title': '「Miles」',
            'description': 'md5:d01c8b9ee24ff64f7c7fd5f769f21e06',
        },
        'playlist_mincount': 43,
    }]

    def _real_extract(self, url):
        user_id = self._match_id(url)
        user_info = self._download_json(
            'http://www.kuwo.cn/api/www/user/userInfo',
            user_id, 'Downloading user info JSON',
            query={
                'uid': user_id,
                'httpsStatus': '1',
                'reqId': 'd8dc5d10-4dc0-11eb-aae6-cfdb349a8527',
            },
        )['data']
        title = user_info['nick']
        description = user_info.get('signature')

        playlist_id = user_info.get('pid')
        if playlist_id:
            playlist = self.url_result(
                'http://www.kuwo.cn/playlist/%s' % playlist_id,
                KuwoPlaylistIE.ie_key())
            playlist.update({
                'id': user_id,
                'title': title,
                'description': description,
            })
            return playlist

        entries = []
        playlist_ids = user_info.get('ids', [])
        for playlist_id in playlist_ids:
            playlist = self.url_result(
                'http://www.kuwo.cn/playlist/%s' % playlist_id,
                KuwoPlaylistIE.ie_key())
            entries.append(playlist)

        return self.playlist_result(entries, user_id, title, description)


class KuwoCategoryIE(KuwoBaseIE):
    IE_NAME = 'kuwo:category'
    IE_DESC = '酷我音乐-分类'
    _VALID_URL = r'https?://(?:www\.)?kuwo\.cn/category/(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.kuwo.cn/category/10000000',
        'playlist_mincount': 180,
        'info_dict': {
            'id': '10000000',
            'title': '热门歌曲',
            'description': 'md5:2eb2962a1e4c6b3f29e1e2f48d4a9bb8',
        },
    }]

    def _real_extract(self, url):
        category_id = self._match_id(url)
        category_info = self._download_json(
            'http://www.kuwo.cn/api/www/category/playlistInfo',
            category_id, 'Downloading category info JSON',
            query={
                'id': category_id,
                'httpsStatus': '1',
                'reqId': 'd8dc5d10-4dc0-11eb-aae6-cfdb349a8527',
            },
        )['data']
        title = category_info['name']
        description = category_info.get('intro')

        playlist_id = category_info.get('id')
        if playlist_id:
            playlist = self.url_result(
                'http://www.kuwo.cn/playlist/%s' % playlist_id,
                KuwoPlaylistIE.ie_key())
            playlist.update({
                'id': category_id,
                'title': title,
                'description': description,
            })
            return playlist

        entries = []
        playlist_ids = category_info.get('list', [])
        for playlist_id in playlist_ids:
            playlist = self.url_result(
                'http://www.kuwo.cn/playlist/%s' % playlist_id,
                KuwoPlaylistIE.ie_key())
            entries.append(playlist)

        return self.playlist_result(entries, category_id, title, description)
