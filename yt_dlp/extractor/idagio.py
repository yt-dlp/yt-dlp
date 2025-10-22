from .common import InfoExtractor
from ..utils import int_or_none, unified_timestamp, url_or_none
from ..utils.traversal import traverse_obj


class IdagioTrackIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?app\.idagio\.com(?:/[a-z]{2})?/recordings/\d+\?(?:[^#]+&)?trackId=(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://app.idagio.com/recordings/30576934?trackId=30576943',
        'md5': '15148bd71804b2450a2508931a116b56',
        'info_dict': {
            'id': '30576943',
            'ext': 'mp3',
            'title': 'Theme. Andante',
            'duration': 82,
            'composers': ['Edward Elgar'],
            'artists': ['Vasily Petrenko', 'Royal Liverpool Philharmonic Orchestra'],
            'genres': ['Orchestral', 'Other Orchestral Music'],
            'track': 'Theme. Andante',
            'timestamp': 1554474370,
            'upload_date': '20190405',
        },
    }, {
        'url': 'https://app.idagio.com/recordings/20514467?trackId=20514478&utm_source=pcl',
        'md5': '3acef2ea0feadf889123b70e5a1e7fa7',
        'info_dict': {
            'id': '20514478',
            'ext': 'mp3',
            'title': 'I. Adagio sostenuto',
            'duration': 316,
            'composers': ['Ludwig van Beethoven'],
            'genres': ['Keyboard', 'Sonata (Keyboard)'],
            'track': 'I. Adagio sostenuto',
            'timestamp': 1518076337,
            'upload_date': '20180208',
        },
    }, {
        'url': 'https://app.idagio.com/de/recordings/20514467?trackId=20514478&utm_source=pcl',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        track_id = self._match_id(url)
        track_info = self._download_json(
            f'https://api.idagio.com/v2.0/metadata/tracks/{track_id}',
            track_id, fatal=False, expected_status=406)
        if traverse_obj(track_info, 'error_code') == 'idagio.error.blocked.location':
            self.raise_geo_restricted()

        content_info = self._download_json(
            f'https://api.idagio.com/v1.8/content/track/{track_id}', track_id,
            query={
                'quality': '0',
                'format': '2',
                'client_type': 'web-4',
            })

        return {
            'ext': 'mp3',
            'vcodec': 'none',
            'id': track_id,
            'url': traverse_obj(content_info, ('url', {url_or_none})),
            **traverse_obj(track_info, ('result', {
                'title': ('piece', 'title', {str}),
                'timestamp': ('recording', 'created_at', {int_or_none(scale=1000)}),
                'location': ('recording', 'location', {str}),
                'duration': ('duration', {int_or_none}),
                'track': ('piece', 'title', {str}),
                'artists': ('recording', ('conductor', ('ensembles', ...), ('soloists', ...)), 'name', {str}, filter),
                'composers': ('piece', 'workpart', 'work', 'composer', 'name', {str}, filter, all, filter),
                'genres': ('piece', 'workpart', 'work', ('genre', 'subgenre'), 'title', {str}, filter),
            })),
        }


class IdagioPlaylistBaseIE(InfoExtractor):
    """Subclasses must set _API_URL_TMPL and define _parse_playlist_metadata"""
    _PLAYLIST_ID_KEY = 'id'  # vs. 'display_id'

    def _entries(self, playlist_info):
        for track_data in traverse_obj(playlist_info, ('tracks', lambda _, v: v['id'] and v['recording']['id'])):
            track_id = track_data['id']
            recording_id = track_data['recording']['id']
            yield self.url_result(
                f'https://app.idagio.com/recordings/{recording_id}?trackId={track_id}',
                ie=IdagioTrackIE, video_id=track_id)

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        playlist_info = self._download_json(
            self._API_URL_TMPL.format(playlist_id), playlist_id)['result']

        return {
            '_type': 'playlist',
            self._PLAYLIST_ID_KEY: playlist_id,
            'entries': self._entries(playlist_info),
            **self._parse_playlist_metadata(playlist_info),
        }


class IdagioRecordingIE(IdagioPlaylistBaseIE):
    _VALID_URL = r'https?://(?:www\.)?app\.idagio\.com(?:/[a-z]{2})?/recordings/(?P<id>\d+)(?![^#]*[&?]trackId=\d+)'
    _TESTS = [{
        'url': 'https://app.idagio.com/recordings/30576934',
        'info_dict': {
            'id': '30576934',
            'title': 'Variations on an Original Theme op. 36',
            'composers': ['Edward Elgar'],
            'artists': ['Vasily Petrenko', 'Royal Liverpool Philharmonic Orchestra'],
            'genres': ['Orchestral', 'Other Orchestral Music'],
            'timestamp': 1554474370,
            'modified_timestamp': 1554474370,
            'modified_date': '20190405',
            'upload_date': '20190405',
        },
        'playlist_count': 15,
    }, {
        'url': 'https://app.idagio.com/de/recordings/20514467',
        'info_dict': {
            'id': '20514467',
            'title': 'Sonata for Piano No. 14 in C sharp minor op. 27/2',
            'composers': ['Ludwig van Beethoven'],
            'genres': ['Keyboard', 'Sonata (Keyboard)'],
            'timestamp': 1518076337,
            'upload_date': '20180208',
            'modified_timestamp': 1518076337,
            'modified_date': '20180208',
        },
        'playlist_count': 3,
    }]
    _API_URL_TMPL = 'https://api.idagio.com/v2.0/metadata/recordings/{}'

    def _parse_playlist_metadata(self, playlist_info):
        return traverse_obj(playlist_info, {
            'title': ('work', 'title', {str}),
            'timestamp': ('created_at', {int_or_none(scale=1000)}),
            'modified_timestamp': ('created_at', {int_or_none(scale=1000)}),
            'location': ('location', {str}),
            'artists': (('conductor', ('ensembles', ...), ('soloists', ...)), 'name', {str}),
            'composers': ('work', 'composer', 'name', {str}, all),
            'genres': ('work', ('genre', 'subgenre'), 'title', {str}),
            'tags': ('tags', ..., {str}),
        })


class IdagioAlbumIE(IdagioPlaylistBaseIE):
    _VALID_URL = r'https?://(?:www\.)?app\.idagio\.com(?:/[a-z]{2})?/albums/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://app.idagio.com/albums/elgar-enigma-variations-in-the-south-serenade-for-strings',
        'info_dict': {
            'id': 'a9f139b8-f70d-4b8a-a9a4-5fe8d35eaf9c',
            'display_id': 'elgar-enigma-variations-in-the-south-serenade-for-strings',
            'title': 'Elgar: Enigma Variations, In the South, Serenade for Strings',
            'description': '',
            'thumbnail': r're:https://.+/albums/880040420521/main\.jpg',
            'artists': ['Vasily Petrenko', 'Royal Liverpool Philharmonic Orchestra', 'Edward Elgar'],
            'timestamp': 1553817600,
            'upload_date': '20190329',
            'modified_timestamp': 1562566559.0,
            'modified_date': '20190708',
        },
        'playlist_count': 19,
    }, {
        'url': 'https://app.idagio.com/de/albums/brahms-ein-deutsches-requiem-3B403DF6-62D7-4A42-807B-47173F3E0192',
        'info_dict': {
            'id': '2862ad4e-4a61-45ad-9ce4-7fcf0c2626fe',
            'display_id': 'brahms-ein-deutsches-requiem-3B403DF6-62D7-4A42-807B-47173F3E0192',
            'title': 'Brahms: Ein deutsches Requiem',
            'description': 'GRAMOPHONE CLASSICAL MUSIC AWARDS 2025 Recording of the Year & Choral',
            'thumbnail': r're:https://.+/albums/3149020954522/main\.jpg',
            'artists': ['Sabine Devieilhe', 'Stéphane Degout', 'Raphaël Pichon', 'Pygmalion', 'Johannes Brahms'],
            'timestamp': 1760054400,
            'upload_date': '20251010',
            'modified_timestamp': 1760624868,
            'modified_date': '20251016',
            'tags': ['recommended', 'recent-release'],
        },
        'playlist_count': 7,
    }]
    _API_URL_TMPL = 'https://api.idagio.com/v2.0/metadata/albums/{}'
    _PLAYLIST_ID_KEY = 'display_id'

    def _parse_playlist_metadata(self, playlist_info):
        return traverse_obj(playlist_info, {
            'id': ('id', {str}),
            'title': ('title', {str}),
            'timestamp': ('publishDate', {unified_timestamp}),
            'modified_timestamp': ('lastModified', {unified_timestamp}),
            'thumbnail': ('imageUrl', {url_or_none}),
            'description': ('description', {str}),
            'artists': ('participants', ..., 'name', {str}),
            'tags': ('tags', ..., {str}),
        })


class IdagioPlaylistIE(IdagioPlaylistBaseIE):
    _VALID_URL = r'https?://(?:www\.)?app\.idagio\.com(?:/[a-z]{2})?/playlists/(?!personal/)(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://app.idagio.com/playlists/beethoven-the-most-beautiful-piano-music',
        'info_dict': {
            'id': '31652bec-8c5b-460e-a3f0-cf1f69817f53',
            'display_id': 'beethoven-the-most-beautiful-piano-music',
            'title': 'Beethoven: the most beautiful piano music',
            'description': 'md5:d41bb04b8896bb69377f5c2cd9345ad1',
            'thumbnail': r're:https://.+/playlists/31652bec-8c5b-460e-a3f0-cf1f69817f53/main\.jpg',
            'creators': ['IDAGIO'],
        },
        'playlist_mincount': 16,  # one entry is geo-restricted
    }, {
        'url': 'https://app.idagio.com/de/playlists/piano-music-for-an-autumn-day',
        'info_dict': {
            'id': 'd70e9c7f-7080-4308-ae0f-f890dddeda82',
            'display_id': 'piano-music-for-an-autumn-day',
            'title': 'Piano Music for an Autumn Day',
            'description': 'Get ready to snuggle up and enjoy all the musical colours of this cosy, autumnal playlist.',
            'thumbnail': r're:https://.+/playlists/d70e9c7f-7080-4308-ae0f-f890dddeda82/main\.jpg',
            'creators': ['IDAGIO'],
        },
        'playlist_count': 35,
    }]
    _API_URL_TMPL = 'https://api.idagio.com/v2.0/playlists/{}'
    _PLAYLIST_ID_KEY = 'display_id'

    def _parse_playlist_metadata(self, playlist_info):
        return traverse_obj(playlist_info, {
            'id': ('id', {str}),
            'title': ('title', {str}),
            'thumbnail': ('imageUrl', {url_or_none}),
            'description': ('description', {str}),
            'creators': ('curator', 'name', {str}, all),
        })


class IdagioPersonalPlaylistIE(IdagioPlaylistBaseIE):
    _VALID_URL = r'https?://(?:www\.)?app\.idagio\.com(?:/[a-z]{2})?/playlists/personal/(?P<id>[\da-f-]+)'
    _TESTS = [{
        'url': 'https://app.idagio.com/playlists/personal/99dad72e-7b3a-45a4-b216-867c08046ed8',
        'info_dict': {
            'id': '99dad72e-7b3a-45a4-b216-867c08046ed8',
            'title': 'Test',
            'creators': ['1a6f16a6-4514-4d0c-b481-3a9877835626'],
            'thumbnail': r're:https://.+/artists/86371/main\.jpg',
            'timestamp': 1602859138,
            'modified_timestamp': 1755616667,
            'upload_date': '20201016',
            'modified_date': '20250819',
        },
        'playlist_count': 100,
    }, {
        'url': 'https://app.idagio.com/de/playlists/personal/99dad72e-7b3a-45a4-b216-867c08046ed8',
        'only_matching': True,
    }]
    _API_URL_TMPL = 'https://api.idagio.com/v1.0/personal-playlists/{}'

    def _parse_playlist_metadata(self, playlist_info):
        return traverse_obj(playlist_info, {
            'title': ('title', {str}),
            'thumbnail': ('image_url', {url_or_none}),
            'creators': ('user_id', {str}, all),
            'timestamp': ('created_at', {int_or_none(scale=1000)}),
            'modified_timestamp': ('updated_at', {int_or_none(scale=1000)}),
        })
