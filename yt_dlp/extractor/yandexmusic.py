import hashlib
import itertools

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    try_get,
)


class YandexMusicBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'https?://music\.yandex\.(?P<tld>ru|kz|ua|by|com)'

    @staticmethod
    def _handle_error(response):
        if isinstance(response, dict):
            error = response.get('error')
            if error:
                raise ExtractorError(error, expected=True)
            if response.get('type') == 'captcha' or 'captcha' in response:
                YandexMusicBaseIE._raise_captcha()

    @staticmethod
    def _raise_captcha():
        raise ExtractorError(
            'YandexMusic has considered yt-dlp requests automated and '
            'asks you to solve a CAPTCHA. You can either wait for some '
            'time until unblocked and optionally use --sleep-interval '
            'in future or alternatively you can go to https://music.yandex.ru/ '
            'solve CAPTCHA, then export cookies and pass cookie file to '
            'yt-dlp with --cookies',
            expected=True)

    def _download_webpage_handle(self, *args, **kwargs):
        webpage = super(YandexMusicBaseIE, self)._download_webpage_handle(*args, **kwargs)
        if 'Нам очень жаль, но&nbsp;запросы, поступившие с&nbsp;вашего IP-адреса, похожи на&nbsp;автоматические.' in webpage:
            self._raise_captcha()
        return webpage

    def _download_json(self, *args, **kwargs):
        response = super(YandexMusicBaseIE, self)._download_json(*args, **kwargs)
        self._handle_error(response)
        return response

    def _call_api(self, ep, tld, url, item_id, note, query):
        return self._download_json(
            'https://music.yandex.%s/handlers/%s.jsx' % (tld, ep),
            item_id, note,
            fatal=False,
            headers={
                'Referer': url,
                'X-Requested-With': 'XMLHttpRequest',
                'X-Retpath-Y': url,
            },
            query=query)


class YandexMusicTrackIE(YandexMusicBaseIE):
    IE_NAME = 'yandexmusic:track'
    IE_DESC = 'Яндекс.Музыка - Трек'
    _VALID_URL = r'%s/album/(?P<album_id>\d+)/track/(?P<id>\d+)' % YandexMusicBaseIE._VALID_URL_BASE

    _TESTS = [{
        'url': 'http://music.yandex.ru/album/540508/track/4878838',
        'md5': 'dec8b661f12027ceaba33318787fff76',
        'info_dict': {
            'id': '4878838',
            'ext': 'mp3',
            'title': 'md5:c63e19341fdbe84e43425a30bc777856',
            'filesize': int,
            'duration': 193.04,
            'track': 'md5:210508c6ffdfd67a493a6c378f22c3ff',
            'album': 'md5:cd04fb13c4efeafdfa0a6a6aca36d01a',
            'album_artist': 'md5:5f54c35462c07952df33d97cfb5fc200',
            'artist': 'md5:e6fd86621825f14dc0b25db3acd68160',
            'release_year': 2009,
        },
        # 'skip': 'Travis CI servers blocked by YandexMusic',
    }, {
        # multiple disks
        'url': 'http://music.yandex.ru/album/3840501/track/705105',
        'md5': '82a54e9e787301dd45aba093cf6e58c0',
        'info_dict': {
            'id': '705105',
            'ext': 'mp3',
            'title': 'md5:f86d4a9188279860a83000277024c1a6',
            'filesize': int,
            'duration': 239.27,
            'track': 'md5:40f887f0666ba1aa10b835aca44807d1',
            'album': 'md5:624f5224b14f5c88a8e812fd7fbf1873',
            'album_artist': 'md5:dd35f2af4e8927100cbe6f5e62e1fb12',
            'artist': 'md5:dd35f2af4e8927100cbe6f5e62e1fb12',
            'release_year': 2016,
            'genre': 'pop',
            'disc_number': 2,
            'track_number': 9,
        },
        # 'skip': 'Travis CI servers blocked by YandexMusic',
    }, {
        'url': 'http://music.yandex.com/album/540508/track/4878838',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        tld, album_id, track_id = mobj.group('tld'), mobj.group('album_id'), mobj.group('id')

        track = self._call_api(
            'track', tld, url, track_id, 'Downloading track JSON',
            {'track': '%s:%s' % (track_id, album_id)})['track']
        track_title = track['title']

        download_data = self._download_json(
            'https://music.yandex.ru/api/v2.1/handlers/track/%s:%s/web-album_track-track-track-main/download/m' % (track_id, album_id),
            track_id, 'Downloading track location url JSON', query={'hq': 1}, headers={'X-Retpath-Y': url})

        fd_data = self._download_json(
            download_data['src'], track_id,
            'Downloading track location JSON',
            query={'format': 'json'})
        key = hashlib.md5(('XGRlBW9FXlekgbPrRHuSiA' + fd_data['path'][1:] + fd_data['s']).encode('utf-8')).hexdigest()
        f_url = 'http://%s/get-mp3/%s/%s?track-id=%s ' % (fd_data['host'], key, fd_data['ts'] + fd_data['path'], track['id'])

        thumbnail = None
        cover_uri = track.get('albums', [{}])[0].get('coverUri')
        if cover_uri:
            thumbnail = cover_uri.replace('%%', 'orig')
            if not thumbnail.startswith('http'):
                thumbnail = 'http://' + thumbnail

        track_info = {
            'id': track_id,
            'ext': 'mp3',
            'url': f_url,
            'filesize': int_or_none(track.get('fileSize')),
            'duration': float_or_none(track.get('durationMs'), 1000),
            'thumbnail': thumbnail,
            'track': track_title,
            'acodec': download_data.get('codec'),
            'abr': int_or_none(download_data.get('bitrate')),
        }

        def extract_artist_name(artist):
            decomposed = artist.get('decomposed')
            if not isinstance(decomposed, list):
                return artist['name']
            parts = [artist['name']]
            for element in decomposed:
                if isinstance(element, dict) and element.get('name'):
                    parts.append(element['name'])
                elif isinstance(element, compat_str):
                    parts.append(element)
            return ''.join(parts)

        def extract_artist(artist_list):
            if artist_list and isinstance(artist_list, list):
                artists_names = [extract_artist_name(a) for a in artist_list if a.get('name')]
                if artists_names:
                    return ', '.join(artists_names)

        albums = track.get('albums')
        if albums and isinstance(albums, list):
            album = albums[0]
            if isinstance(album, dict):
                year = album.get('year')
                disc_number = int_or_none(try_get(
                    album, lambda x: x['trackPosition']['volume']))
                track_number = int_or_none(try_get(
                    album, lambda x: x['trackPosition']['index']))
                track_info.update({
                    'album': album.get('title'),
                    'album_artist': extract_artist(album.get('artists')),
                    'release_year': int_or_none(year),
                    'genre': album.get('genre'),
                    'disc_number': disc_number,
                    'track_number': track_number,
                })

        track_artist = extract_artist(track.get('artists'))
        if track_artist:
            track_info.update({
                'artist': track_artist,
                'title': '%s - %s' % (track_artist, track_title),
            })
        else:
            track_info['title'] = track_title

        return track_info


class YandexMusicPlaylistBaseIE(YandexMusicBaseIE):
    def _extract_tracks(self, source, item_id, url, tld):
        tracks = source['tracks']
        track_ids = [compat_str(track_id) for track_id in source['trackIds']]

        # tracks dictionary shipped with playlist.jsx API is limited to 150 tracks,
        # missing tracks should be retrieved manually.
        if len(tracks) < len(track_ids):
            present_track_ids = set([
                compat_str(track['id'])
                for track in tracks if track.get('id')])
            missing_track_ids = [
                track_id for track_id in track_ids
                if track_id not in present_track_ids]
            # Request missing tracks in chunks to avoid exceeding max HTTP header size,
            # see https://github.com/ytdl-org/youtube-dl/issues/27355
            _TRACKS_PER_CHUNK = 250
            for chunk_num in itertools.count(0):
                start = chunk_num * _TRACKS_PER_CHUNK
                end = start + _TRACKS_PER_CHUNK
                missing_track_ids_req = missing_track_ids[start:end]
                assert missing_track_ids_req
                missing_tracks = self._call_api(
                    'track-entries', tld, url, item_id,
                    'Downloading missing tracks JSON chunk %d' % (chunk_num + 1), {
                        'entries': ','.join(missing_track_ids_req),
                        'lang': tld,
                        'external-domain': 'music.yandex.%s' % tld,
                        'overembed': 'false',
                        'strict': 'true',
                    })
                if missing_tracks:
                    tracks.extend(missing_tracks)
                if end >= len(missing_track_ids):
                    break

        return tracks

    def _build_playlist(self, tracks):
        entries = []
        for track in tracks:
            track_id = track.get('id') or track.get('realId')
            if not track_id:
                continue
            albums = track.get('albums')
            if not albums or not isinstance(albums, list):
                continue
            album = albums[0]
            if not isinstance(album, dict):
                continue
            album_id = album.get('id')
            if not album_id:
                continue
            entries.append(self.url_result(
                'http://music.yandex.ru/album/%s/track/%s' % (album_id, track_id),
                ie=YandexMusicTrackIE.ie_key(), video_id=track_id))
        return entries


class YandexMusicAlbumIE(YandexMusicPlaylistBaseIE):
    IE_NAME = 'yandexmusic:album'
    IE_DESC = 'Яндекс.Музыка - Альбом'
    _VALID_URL = r'%s/album/(?P<id>\d+)' % YandexMusicBaseIE._VALID_URL_BASE

    _TESTS = [{
        'url': 'http://music.yandex.ru/album/540508',
        'info_dict': {
            'id': '540508',
            'title': 'md5:7ed1c3567f28d14be9f61179116f5571',
        },
        'playlist_count': 50,
        # 'skip': 'Travis CI servers blocked by YandexMusic',
    }, {
        'url': 'https://music.yandex.ru/album/3840501',
        'info_dict': {
            'id': '3840501',
            'title': 'md5:36733472cdaa7dcb1fd9473f7da8e50f',
        },
        'playlist_count': 33,
        # 'skip': 'Travis CI servers blocked by YandexMusic',
    }, {
        # empty artists
        'url': 'https://music.yandex.ru/album/9091882',
        'info_dict': {
            'id': '9091882',
            'title': 'ТЕД на русском',
        },
        'playlist_count': 187,
    }]

    @classmethod
    def suitable(cls, url):
        return False if YandexMusicTrackIE.suitable(url) else super(YandexMusicAlbumIE, cls).suitable(url)

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        tld = mobj.group('tld')
        album_id = mobj.group('id')

        album = self._call_api(
            'album', tld, url, album_id, 'Downloading album JSON',
            {'album': album_id})

        entries = self._build_playlist([track for volume in album['volumes'] for track in volume])

        title = album['title']
        artist = try_get(album, lambda x: x['artists'][0]['name'], compat_str)
        if artist:
            title = '%s - %s' % (artist, title)
        year = album.get('year')
        if year:
            title += ' (%s)' % year

        return self.playlist_result(entries, compat_str(album['id']), title)


class YandexMusicPlaylistIE(YandexMusicPlaylistBaseIE):
    IE_NAME = 'yandexmusic:playlist'
    IE_DESC = 'Яндекс.Музыка - Плейлист'
    _VALID_URL = r'%s/users/(?P<user>[^/]+)/playlists/(?P<id>\d+)' % YandexMusicBaseIE._VALID_URL_BASE

    _TESTS = [{
        'url': 'http://music.yandex.ru/users/music.partners/playlists/1245',
        'info_dict': {
            'id': '1245',
            'title': 'md5:841559b3fe2b998eca88d0d2e22a3097',
            'description': 'md5:3b9f27b0efbe53f2ee1e844d07155cc9',
        },
        'playlist_count': 5,
        # 'skip': 'Travis CI servers blocked by YandexMusic',
    }, {
        'url': 'https://music.yandex.ru/users/ya.playlist/playlists/1036',
        'only_matching': True,
    }, {
        # playlist exceeding the limit of 150 tracks (see
        # https://github.com/ytdl-org/youtube-dl/issues/6666)
        'url': 'https://music.yandex.ru/users/mesiaz/playlists/1364',
        'info_dict': {
            'id': '1364',
            'title': 'md5:b3b400f997d3f878a13ae0699653f7db',
        },
        'playlist_mincount': 437,
        # 'skip': 'Travis CI servers blocked by YandexMusic',
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        tld = mobj.group('tld')
        user = mobj.group('user')
        playlist_id = mobj.group('id')

        playlist = self._call_api(
            'playlist', tld, url, playlist_id, 'Downloading playlist JSON', {
                'owner': user,
                'kinds': playlist_id,
                'light': 'true',
                'lang': tld,
                'external-domain': 'music.yandex.%s' % tld,
                'overembed': 'false',
            })['playlist']

        tracks = self._extract_tracks(playlist, playlist_id, url, tld)

        return self.playlist_result(
            self._build_playlist(tracks),
            compat_str(playlist_id),
            playlist.get('title'), playlist.get('description'))


class YandexMusicArtistBaseIE(YandexMusicPlaylistBaseIE):
    def _call_artist(self, tld, url, artist_id):
        return self._call_api(
            'artist', tld, url, artist_id,
            'Downloading artist %s JSON' % self._ARTIST_WHAT, {
                'artist': artist_id,
                'what': self._ARTIST_WHAT,
                'sort': self._ARTIST_SORT or '',
                'dir': '',
                'period': '',
                'lang': tld,
                'external-domain': 'music.yandex.%s' % tld,
                'overembed': 'false',
            })

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        tld = mobj.group('tld')
        artist_id = mobj.group('id')
        data = self._call_artist(tld, url, artist_id)
        tracks = self._extract_tracks(data, artist_id, url, tld)
        title = try_get(data, lambda x: x['artist']['name'], compat_str)
        return self.playlist_result(
            self._build_playlist(tracks), artist_id, title)


class YandexMusicArtistTracksIE(YandexMusicArtistBaseIE):
    IE_NAME = 'yandexmusic:artist:tracks'
    IE_DESC = 'Яндекс.Музыка - Артист - Треки'
    _VALID_URL = r'%s/artist/(?P<id>\d+)/tracks' % YandexMusicBaseIE._VALID_URL_BASE

    _TESTS = [{
        'url': 'https://music.yandex.ru/artist/617526/tracks',
        'info_dict': {
            'id': '617526',
            'title': 'md5:131aef29d45fd5a965ca613e708c040b',
        },
        'playlist_count': 507,
        # 'skip': 'Travis CI servers blocked by YandexMusic',
    }]

    _ARTIST_SORT = ''
    _ARTIST_WHAT = 'tracks'

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        tld = mobj.group('tld')
        artist_id = mobj.group('id')
        data = self._call_artist(tld, url, artist_id)
        tracks = self._extract_tracks(data, artist_id, url, tld)
        artist = try_get(data, lambda x: x['artist']['name'], compat_str)
        title = '%s - %s' % (artist or artist_id, 'Треки')
        return self.playlist_result(
            self._build_playlist(tracks), artist_id, title)


class YandexMusicArtistAlbumsIE(YandexMusicArtistBaseIE):
    IE_NAME = 'yandexmusic:artist:albums'
    IE_DESC = 'Яндекс.Музыка - Артист - Альбомы'
    _VALID_URL = r'%s/artist/(?P<id>\d+)/albums' % YandexMusicBaseIE._VALID_URL_BASE

    _TESTS = [{
        'url': 'https://music.yandex.ru/artist/617526/albums',
        'info_dict': {
            'id': '617526',
            'title': 'md5:55dc58d5c85699b7fb41ee926700236c',
        },
        'playlist_count': 8,
        # 'skip': 'Travis CI servers blocked by YandexMusic',
    }]

    _ARTIST_SORT = 'year'
    _ARTIST_WHAT = 'albums'

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        tld = mobj.group('tld')
        artist_id = mobj.group('id')
        data = self._call_artist(tld, url, artist_id)
        entries = []
        for album in data['albums']:
            if not isinstance(album, dict):
                continue
            album_id = album.get('id')
            if not album_id:
                continue
            entries.append(self.url_result(
                'http://music.yandex.ru/album/%s' % album_id,
                ie=YandexMusicAlbumIE.ie_key(), video_id=album_id))
        artist = try_get(data, lambda x: x['artist']['name'], compat_str)
        title = '%s - %s' % (artist or artist_id, 'Альбомы')
        return self.playlist_result(entries, artist_id, title)
