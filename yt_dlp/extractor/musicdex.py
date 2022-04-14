from .common import InfoExtractor
from ..utils import (
    date_from_str,
    format_field,
    try_get,
    unified_strdate,
)


class MusicdexBaseIE(InfoExtractor):
    def _return_info(self, track_json, album_json, id):
        return {
            'id': str(id),
            'title': track_json.get('name'),
            'track': track_json.get('name'),
            'description': track_json.get('description'),
            'track_number': track_json.get('number'),
            'url': format_field(track_json, 'url', 'https://www.musicdex.org/%s'),
            'duration': track_json.get('duration'),
            'genre': [genre.get('name') for genre in track_json.get('genres') or []],
            'like_count': track_json.get('likes_count'),
            'view_count': track_json.get('plays'),
            'artist': [artist.get('name') for artist in track_json.get('artists') or []],
            'album_artist': [artist.get('name') for artist in album_json.get('artists') or []],
            'thumbnail': format_field(album_json, 'image', 'https://www.musicdex.org/%s'),
            'album': album_json.get('name'),
            'release_year': try_get(album_json, lambda x: date_from_str(unified_strdate(x['release_date'])).year),
            'extractor_key': MusicdexSongIE.ie_key(),
            'extractor': 'MusicdexSong',
        }


class MusicdexSongIE(MusicdexBaseIE):
    _VALID_URL = r'https?://(?:www\.)?musicdex\.org/track/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://www.musicdex.org/track/306/dual-existence',
        'info_dict': {
            'id': '306',
            'ext': 'mp3',
            'title': 'dual existence',
            'description': '#NIPPONSEI @ IRC.RIZON.NET',
            'track': 'dual existence',
            'track_number': 1,
            'duration': 266000,
            'genre': ['Anime'],
            'like_count': int,
            'view_count': int,
            'artist': ['fripSide'],
            'album_artist': ['fripSide'],
            'thumbnail': 'https://www.musicdex.org/storage/album/9iDIam1DHTVqUG4UclFIEq1WAFGXfPW4y0TtZa91.png',
            'album': 'To Aru Kagaku no Railgun T OP2 Single - dual existence',
            'release_year': 2020
        },
        'params': {'skip_download': True}
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        data_json = self._download_json(f'https://www.musicdex.org/secure/tracks/{id}?defaultRelations=true', id)['track']
        return self._return_info(data_json, data_json.get('album') or {}, id)


class MusicdexAlbumIE(MusicdexBaseIE):
    _VALID_URL = r'https?://(?:www\.)?musicdex\.org/album/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://www.musicdex.org/album/56/tenmon-and-eiichiro-yanagi-minori/ef-a-tale-of-memories-original-soundtrack-2-fortissimo',
        'playlist_mincount': 28,
        'info_dict': {
            'id': '56',
            'genre': ['OST'],
            'view_count': int,
            'artist': ['TENMON & Eiichiro Yanagi / minori'],
            'title': 'ef - a tale of memories Original Soundtrack 2 ~fortissimo~',
            'release_year': 2008,
            'thumbnail': 'https://www.musicdex.org/storage/album/2rSHkyYBYfB7sbvElpEyTMcUn6toY7AohOgJuDlE.jpg',
        },
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        data_json = self._download_json(f'https://www.musicdex.org/secure/albums/{id}?defaultRelations=true', id)['album']
        entries = [self._return_info(track, data_json, track['id']) for track in data_json.get('tracks') or [] if track.get('id')]

        return {
            '_type': 'playlist',
            'id': id,
            'title': data_json.get('name'),
            'description': data_json.get('description'),
            'genre': [genre.get('name') for genre in data_json.get('genres') or []],
            'view_count': data_json.get('plays'),
            'artist': [artist.get('name') for artist in data_json.get('artists') or []],
            'thumbnail': format_field(data_json, 'image', 'https://www.musicdex.org/%s'),
            'release_year': try_get(data_json, lambda x: date_from_str(unified_strdate(x['release_date'])).year),
            'entries': entries,
        }


class MusicdexPageIE(MusicdexBaseIE):
    def _entries(self, id):
        next_page_url = self._API_URL % id
        while next_page_url:
            data_json = self._download_json(next_page_url, id)['pagination']
            for data in data_json.get('data') or []:
                yield data
            next_page_url = data_json.get('next_page_url')


class MusicdexArtistIE(MusicdexPageIE):
    _VALID_URL = r'https?://(?:www\.)?musicdex\.org/artist/(?P<id>\d+)'
    _API_URL = 'https://www.musicdex.org/secure/artists/%s/albums?page=1'

    _TESTS = [{
        'url': 'https://www.musicdex.org/artist/11/fripside',
        'playlist_mincount': 28,
        'info_dict': {
            'id': '11',
            'view_count': int,
            'title': 'fripSide',
            'thumbnail': 'https://www.musicdex.org/storage/artist/ZmOz0lN2vsweegB660em3xWffCjLPmTQHqJls5Xx.jpg',
        },
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        data_json = self._download_json(f'https://www.musicdex.org/secure/artists/{id}', id)['artist']
        entries = []
        for album in self._entries(id):
            entries.extend(self._return_info(track, album, track['id']) for track in album.get('tracks') or [] if track.get('id'))

        return {
            '_type': 'playlist',
            'id': id,
            'title': data_json.get('name'),
            'view_count': data_json.get('plays'),
            'thumbnail': format_field(data_json, 'image_small', 'https://www.musicdex.org/%s'),
            'entries': entries,
        }


class MusicdexPlaylistIE(MusicdexPageIE):
    _VALID_URL = r'https?://(?:www\.)?musicdex\.org/playlist/(?P<id>\d+)'
    _API_URL = 'https://www.musicdex.org/secure/playlists/%s/tracks?perPage=10000&page=1'

    _TESTS = [{
        'url': 'https://www.musicdex.org/playlist/9/test',
        'playlist_mincount': 73,
        'info_dict': {
            'id': '9',
            'view_count': int,
            'title': 'Test',
            'thumbnail': 'https://www.musicdex.org/storage/album/jXATI79f0IbQ2sgsKYOYRCW3zRwF3XsfHhzITCuJ.jpg',
            'description': 'Test 123 123 21312 32121321321321312',
        },
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        data_json = self._download_json(f'https://www.musicdex.org/secure/playlists/{id}', id)['playlist']
        entries = [self._return_info(track, track.get('album') or {}, track['id'])
                   for track in self._entries(id) or [] if track.get('id')]

        return {
            '_type': 'playlist',
            'id': id,
            'title': data_json.get('name'),
            'description': data_json.get('description'),
            'view_count': data_json.get('plays'),
            'thumbnail': format_field(data_json, 'image', 'https://www.musicdex.org/%s'),
            'entries': entries,
        }
