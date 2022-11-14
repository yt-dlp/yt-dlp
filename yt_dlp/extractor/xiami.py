from .common import InfoExtractor
from ..compat import compat_urllib_parse_unquote
from ..utils import int_or_none


class XiamiBaseIE(InfoExtractor):
    _API_BASE_URL = 'https://emumo.xiami.com/song/playlist/cat/json/id'

    def _download_webpage_handle(self, *args, **kwargs):
        webpage = super(XiamiBaseIE, self)._download_webpage_handle(*args, **kwargs)
        if '>Xiami is currently not available in your country.<' in webpage:
            self.raise_geo_restricted('Xiami is currently not available in your country')
        return webpage

    def _extract_track(self, track, track_id=None):
        track_name = track.get('songName') or track.get('name') or track['subName']
        artist = track.get('artist') or track.get('artist_name') or track.get('singers')
        title = '%s - %s' % (artist, track_name) if artist else track_name
        track_url = self._decrypt(track['location'])

        subtitles = {}
        lyrics_url = track.get('lyric_url') or track.get('lyric')
        if lyrics_url and lyrics_url.startswith('http'):
            subtitles['origin'] = [{'url': lyrics_url}]

        return {
            'id': track.get('song_id') or track_id,
            'url': track_url,
            'title': title,
            'thumbnail': track.get('pic') or track.get('album_pic'),
            'duration': int_or_none(track.get('length')),
            'creator': track.get('artist', '').split(';')[0],
            'track': track_name,
            'track_number': int_or_none(track.get('track')),
            'album': track.get('album_name') or track.get('title'),
            'artist': artist,
            'subtitles': subtitles,
        }

    def _extract_tracks(self, item_id, referer, typ=None):
        playlist = self._download_json(
            '%s/%s%s' % (self._API_BASE_URL, item_id, '/type/%s' % typ if typ else ''),
            item_id, headers={
                'Referer': referer,
            })
        return [
            self._extract_track(track, item_id)
            for track in playlist['data']['trackList']]

    @staticmethod
    def _decrypt(origin):
        n = int(origin[0])
        origin = origin[1:]
        short_length = len(origin) // n
        long_num = len(origin) - short_length * n
        l = tuple()
        for i in range(0, n):
            length = short_length
            if i < long_num:
                length += 1
            l += (origin[0:length], )
            origin = origin[length:]
        ans = ''
        for i in range(0, short_length + 1):
            for j in range(0, n):
                if len(l[j]) > i:
                    ans += l[j][i]
        return compat_urllib_parse_unquote(ans).replace('^', '0')


class XiamiSongIE(XiamiBaseIE):
    IE_NAME = 'xiami:song'
    IE_DESC = '虾米音乐'
    _VALID_URL = r'https?://(?:www\.)?xiami\.com/song/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'http://www.xiami.com/song/1775610518',
        'md5': '521dd6bea40fd5c9c69f913c232cb57e',
        'info_dict': {
            'id': '1775610518',
            'ext': 'mp3',
            'title': 'HONNE - Woman',
            'thumbnail': r're:http://img\.xiami\.net/images/album/.*\.jpg',
            'duration': 265,
            'creator': 'HONNE',
            'track': 'Woman',
            'album': 'Woman',
            'artist': 'HONNE',
            'subtitles': {
                'origin': [{
                    'ext': 'lrc',
                }],
            },
        },
        'skip': 'Georestricted',
    }, {
        'url': 'http://www.xiami.com/song/1775256504',
        'md5': '932a3abd45c6aa2b1fdbe028fcb4c4fc',
        'info_dict': {
            'id': '1775256504',
            'ext': 'mp3',
            'title': '戴荃 - 悟空',
            'thumbnail': r're:http://img\.xiami\.net/images/album/.*\.jpg',
            'duration': 200,
            'creator': '戴荃',
            'track': '悟空',
            'album': '悟空',
            'artist': '戴荃',
            'subtitles': {
                'origin': [{
                    'ext': 'lrc',
                }],
            },
        },
        'skip': 'Georestricted',
    }, {
        'url': 'http://www.xiami.com/song/1775953850',
        'info_dict': {
            'id': '1775953850',
            'ext': 'mp3',
            'title': 'До Скону - Чума Пожирает Землю',
            'thumbnail': r're:http://img\.xiami\.net/images/album/.*\.jpg',
            'duration': 683,
            'creator': 'До Скону',
            'track': 'Чума Пожирает Землю',
            'track_number': 7,
            'album': 'Ад',
            'artist': 'До Скону',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.xiami.com/song/xLHGwgd07a1',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        return self._extract_tracks(self._match_id(url), url)[0]


class XiamiPlaylistBaseIE(XiamiBaseIE):
    def _real_extract(self, url):
        item_id = self._match_id(url)
        return self.playlist_result(self._extract_tracks(item_id, url, self._TYPE), item_id)


class XiamiAlbumIE(XiamiPlaylistBaseIE):
    IE_NAME = 'xiami:album'
    IE_DESC = '虾米音乐 - 专辑'
    _VALID_URL = r'https?://(?:www\.)?xiami\.com/album/(?P<id>[^/?#&]+)'
    _TYPE = '1'
    _TESTS = [{
        'url': 'http://www.xiami.com/album/2100300444',
        'info_dict': {
            'id': '2100300444',
        },
        'playlist_count': 10,
        'skip': 'Georestricted',
    }, {
        'url': 'http://www.xiami.com/album/512288?spm=a1z1s.6843761.1110925389.6.hhE9p9',
        'only_matching': True,
    }, {
        'url': 'http://www.xiami.com/album/URVDji2a506',
        'only_matching': True,
    }]


class XiamiArtistIE(XiamiPlaylistBaseIE):
    IE_NAME = 'xiami:artist'
    IE_DESC = '虾米音乐 - 歌手'
    _VALID_URL = r'https?://(?:www\.)?xiami\.com/artist/(?P<id>[^/?#&]+)'
    _TYPE = '2'
    _TESTS = [{
        'url': 'http://www.xiami.com/artist/2132?spm=0.0.0.0.dKaScp',
        'info_dict': {
            'id': '2132',
        },
        'playlist_count': 20,
        'skip': 'Georestricted',
    }, {
        'url': 'http://www.xiami.com/artist/bC5Tk2K6eb99',
        'only_matching': True,
    }]


class XiamiCollectionIE(XiamiPlaylistBaseIE):
    IE_NAME = 'xiami:collection'
    IE_DESC = '虾米音乐 - 精选集'
    _VALID_URL = r'https?://(?:www\.)?xiami\.com/collect/(?P<id>[^/?#&]+)'
    _TYPE = '3'
    _TEST = {
        'url': 'http://www.xiami.com/collect/156527391?spm=a1z1s.2943601.6856193.12.4jpBnr',
        'info_dict': {
            'id': '156527391',
        },
        'playlist_mincount': 29,
        'skip': 'Georestricted',
    }
