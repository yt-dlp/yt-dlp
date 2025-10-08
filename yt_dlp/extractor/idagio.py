from .common import InfoExtractor
from ..utils import traverse_obj, unified_timestamp


class IdagioTrackIE(InfoExtractor):
    """
    This extractor is only used internally to extract the info about tracks contained in every recording, album or
    playlist
    """
    _VALID_URL = r'https?://(?:www\.)?api\.idagio\.com/v2\.0/metadata/tracks/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://api.idagio.com/v2.0/metadata/tracks/30576943',
        'md5': '15148bd71804b2450a2508931a116b56',
        'info_dict': {
            'id': '30576943',
            'ext': 'mp3',
            'title': 'Variations on an Original Theme op. 36: Theme. Andante',
            'duration': 82,
            'composers': ['Edward Elgar'],
            'artists': ['Vasily Petrenko', 'Royal Liverpool Philharmonic Orchestra'],
            'genres': ['Orchestral', 'Other Orchestral Music'],
            'track': 'Variations on an Original Theme op. 36: Theme. Andante',
            'track_id': '30576943',
            'timestamp': 1554474370029,
        },
    }, {
        'url': 'https://api.idagio.com/v2.0/metadata/tracks/20514478',
        'md5': '3acef2ea0feadf889123b70e5a1e7fa7',
        'info_dict': {
            'id': '20514478',
            'ext': 'mp3',
            'title': 'Sonata for Piano No. 14 in C sharp minor op. 27/2: I. Adagio sostenuto',
            'duration': 316,
            'composers': ['Ludwig van Beethoven'],
            'artists': [],
            'genres': ['Keyboard', 'Sonata (Keyboard)'],
            'track': 'Sonata for Piano No. 14 in C sharp minor op. 27/2: I. Adagio sostenuto',
            'track_id': '20514478',
            'timestamp': 1518076337511,
        },
    }]

    def _real_extract(self, url):
        track_id: str = self._match_id(url)
        track_info: dict = self._download_json(f'https://api.idagio.com/v2.0/metadata/tracks/{track_id}',
                                               track_id).get('result')

        content_info: dict = self._download_json(f'https://api.idagio.com/v1.8/content/track/{track_id}?quality=0&format=2&client_type=web-4', track_id)

        work_name = traverse_obj(track_info, ('piece', 'workpart', 'work', 'title'))
        conductor = traverse_obj(track_info, ('recording', 'conductor', 'name'))
        artists = [] if conductor is None else [conductor]

        return {
            'id': str(traverse_obj(track_info, ('id',))),
            'title': work_name + ': ' + traverse_obj(track_info, ('piece', 'title')),
            'url': traverse_obj(content_info, ('url', )),
            'ext': 'mp3',
            'timestamp': traverse_obj(track_info, ('recording', 'created_at')),
            'location': traverse_obj(track_info, ('recording', 'location')),
            'duration': traverse_obj(track_info, ('duration',)),
            'track': work_name + ': ' + traverse_obj(track_info, ('piece', 'title')),
            'track_id': track_id,
            'artists': (artists + (traverse_obj(track_info, ('recording', 'ensembles', ..., 'name')) or [])
                        + (traverse_obj(track_info, ('recording', 'soloists', ..., 'name')) or [])),
            'composers': [traverse_obj(track_info, ('piece', 'workpart', 'work', 'composer', 'name'))],
            'genres': [traverse_obj(track_info, ('piece', 'workpart', 'work', 'genre', 'title')),
                       traverse_obj(track_info, ('piece', 'workpart', 'work', 'subgenre', 'title'))],
        }


class IdagioRecordingIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?app\.idagio\.com/recordings/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://app.idagio.com/recordings/30576934',
        'info_dict': {
            'id': '30576934',
            'title': 'Variations on an Original Theme op. 36',
            'composers': ['Edward Elgar'],
            'artists': ['Vasily Petrenko', 'Royal Liverpool Philharmonic Orchestra'],
            'genres': ['Orchestral', 'Other Orchestral Music'],
            'timestamp': 1554474370029,
            'modified_timestamp': 1554481570.0,
            'modified_date': '20190405',
        },
        'playlist_count': 15,
    }]

    def _real_extract(self, url):
        recording_id: str = self._match_id(url)
        recording_info: dict = self._download_json(f'https://api.idagio.com/v2.0/metadata/recordings/{recording_id}',
                                                   recording_id).get('result')

        track_ids: list[int] = traverse_obj(recording_info, ('tracks', ..., 'id'))

        return {
            '_type': 'multi_video',
            'id': recording_id,
            'title': traverse_obj(recording_info, ('work', 'title')),
            'entries': [self.url_result(f'https://api.idagio.com/v2.0/metadata/tracks/{track_id}',
                                        ie='IdagioTrack', video_id=track_id, track_number=i)
                        for i, track_id in enumerate(track_ids, start=1)],
            'ext': 'mp3',
            'timestamp': traverse_obj(recording_info, ('created_at',)),
            'modified_timestamp': unified_timestamp(recording_info.get('lastModified')),
            'location': traverse_obj(recording_info, ('location',)),
            'artists': ([traverse_obj(recording_info, ('conductor', 'name'))])
            + (traverse_obj(recording_info, ('ensembles', ..., 'name')) or [])
            + (traverse_obj(recording_info, ('soloists', ..., 'name')) or []),
            'composers': [traverse_obj(recording_info, ('work', 'composer', 'name'))],
            'genres': [traverse_obj(recording_info, ('work', 'genre', 'title')),
                       traverse_obj(recording_info, ('work', 'subgenre', 'title'))],
            'tags': traverse_obj(recording_info, ('tags',)) or None,
        }


class IdagioAlbumIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?app\.idagio\.com/albums/(?P<id>[a-z\-]+)'
    _TESTS = [{
        'url': 'https://app.idagio.com/albums/elgar-enigma-variations-in-the-south-serenade-for-strings',
        'info_dict': {
            'id': 'a9f139b8-f70d-4b8a-a9a4-5fe8d35eaf9c',
            'display_id': 'elgar-enigma-variations-in-the-south-serenade-for-strings',
            'title': 'Elgar: Enigma Variations, In the South, Serenade for Strings',
            'description': '',
            'thumbnail': 'https://idagio-images.global.ssl.fastly.net/albums/880040420521/main.jpg',
            'tags': [],
            'artists': ['Vasily Petrenko', 'Royal Liverpool Philharmonic Orchestra', 'Edward Elgar'],
            'timestamp': 1553817600,
            'upload_date': '20190329',
            'modified_timestamp': 1562566559.0,
            'modified_date': '20190708',
        },
        'playlist_count': 19,
    }]

    def _real_extract(self, url):
        album_display_id: str = self._match_id(url)
        album_info: dict = self._download_json(f'https://api.idagio.com/v2.0/metadata/albums/{album_display_id}',
                                               album_display_id).get('result')

        track_ids: list[int] = traverse_obj(album_info, ('tracks', ..., 'id'))

        return {
            '_type': 'playlist',
            'id': traverse_obj(album_info, ('id',)),
            'display_id': album_display_id,
            'title': traverse_obj(album_info, ('title',)),
            'entries': [self.url_result(f'https://api.idagio.com/v2.0/metadata/tracks/{track_id}',
                                        ie='IdagioTrack', video_id=track_id, track_number=i)
                        for i, track_id in enumerate(track_ids, start=1)],
            'timestamp': unified_timestamp(album_info.get('publishDate')),
            'modified_timestamp': unified_timestamp(album_info.get('lastModified')),
            'thumbnail': traverse_obj(album_info, ('imageUrl',)),
            'description': traverse_obj(album_info, ('description',)),
            'artists': traverse_obj(album_info, ('participants', ..., 'name')) or [],
            'tags': traverse_obj(album_info, ('tags',)) or [],
        }


class IdagioPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?app\.idagio\.com/playlists/(?!personal/)(?P<id>[a-z\-]+)\??.*'
    _TESTS = [{
        'url': 'https://app.idagio.com/playlists/beethoven-the-most-beautiful-piano-music',
        'info_dict': {
            'id': '31652bec-8c5b-460e-a3f0-cf1f69817f53',
            'display_id': 'beethoven-the-most-beautiful-piano-music',
            'title': 'Beethoven: the most beautiful piano music',
            'description': 'md5:d41bb04b8896bb69377f5c2cd9345ad1',
            'thumbnail': 'https://idagio-images.global.ssl.fastly.net/playlists/31652bec-8c5b-460e-a3f0-cf1f69817f53/main.jpg?_alt=sys/ph/artist-default.jpg',
            'creators': ['IDAGIO'],
        },
        'playlist_count': 17,
    }]

    def _real_extract(self, url):
        playlist_display_id: str = self._match_id(url)
        playlist_info: dict = self._download_json(f'https://api.idagio.com/v2.0/playlists/{playlist_display_id}',
                                                  playlist_display_id).get('result')

        track_ids: list[int] = traverse_obj(playlist_info, ('tracks', ..., 'id'))

        return {
            '_type': 'playlist',
            'id': traverse_obj(playlist_info, ('id',)),
            'display_id': playlist_display_id,
            'title': traverse_obj(playlist_info, ('title',)),
            'entries': [self.url_result(f'https://api.idagio.com/v2.0/metadata/tracks/{track_id}',
                                        ie='IdagioTrack', video_id=track_id, track_number=i)
                        for i, track_id in enumerate(track_ids, start=1)],
            'thumbnail': traverse_obj(playlist_info, ('imageUrl',)),
            'description': traverse_obj(playlist_info, ('description',)),
            'creators': [traverse_obj(playlist_info, ('curator', 'name'))],
        }


class IdagioPersonalPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?app\.idagio\.com/playlists/personal/(?P<id>[0-9a-f\-]+)'
    _TESTS = [{
        'url': 'https://app.idagio.com/playlists/personal/99dad72e-7b3a-45a4-b216-867c08046ed8',
        'info_dict': {
            'id': '99dad72e-7b3a-45a4-b216-867c08046ed8',
            'title': 'Test',
            'creators': ['1a6f16a6-4514-4d0c-b481-3a9877835626'],
            'thumbnail': 'https://idagio-images.global.ssl.fastly.net/artists/86371/main.jpg?_alt=sys/ph/artist-default.jpg',
            'timestamp': 1602859138286,
            'modified_timestamp': 1755616667629,
        },
        'playlist_count': 100,
    }]

    def _real_extract(self, url):
        playlist_id: str = self._match_id(url)
        playlist_info: dict = self._download_json(f'https://api.idagio.com/v1.0/personal-playlists/{playlist_id}',
                                                  playlist_id).get('result')

        track_ids: list[int] = traverse_obj(playlist_info, ('tracks', ..., 'id'))

        return {
            '_type': 'playlist',
            'id': playlist_id,
            'title': traverse_obj(playlist_info, ('title',)),
            'entries': [self.url_result(f'https://api.idagio.com/v2.0/metadata/tracks/{track_id}',
                                        ie='IdagioTrack', video_id=track_id, track_number=i)
                        for i, track_id in enumerate(track_ids, start=1)],
            'thumbnail': traverse_obj(playlist_info, ('image_url',)),
            'creators': [traverse_obj(playlist_info, ('user_id',))],
            'timestamp': traverse_obj(playlist_info, ('created_at',)),
            'modified_timestamp': traverse_obj(playlist_info, ('updated_at',)),
        }
