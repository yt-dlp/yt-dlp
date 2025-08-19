from .common import InfoExtractor
from .. import traverse_obj

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
            'timestamp': 1554474370029
        }
    }]

    def _real_extract(self, url):
        track_id: str = self._match_id(url)
        track_info: dict = self._download_json(f'https://api.idagio.com/v2.0/metadata/tracks/{track_id}',
                                                track_id).get('result')

        content_info: dict = self._download_json(f'https://api.idagio.com/v1.8/content/track/{track_id}?quality=0&format=2&client_type=web-4', track_id)

        work_name = traverse_obj(track_info, ('piece', 'workpart', 'work', 'title'))

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
            'artists': ([traverse_obj(track_info, ('recording', 'conductor', 'name'))] or []) +
            (traverse_obj(track_info, ('recording', 'ensembles', ..., 'name')) or []) +
            (traverse_obj(track_info, ('recording', 'soloists', ..., 'name')) or []),
            'composers': [traverse_obj(track_info, ('piece', 'workpart', 'work', 'composer', 'name')),],
            'genres': [traverse_obj(track_info, ('piece', 'workpart', 'work', 'genre', 'title')),
                       traverse_obj(track_info, ('piece', 'workpart', 'work', 'subgenre', 'title')),],
        }


class IdagioRecordingIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?app\.idagio\.com/recordings/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://app.idagio.com/recordings/30576934',
        'md5': 'TODO: md5 sum of the first 10241 bytes of the video file (use --test)',
        'info_dict': {
            'id': '30576934',
            'ext': 'mp3',
            'title': 'Variations on an Original Theme op. 36',
            'composers': ['Edward Elgar'],
            'artists': ['Vasily Petrenko', 'Royal Liverpool Philharmonic Orchestra'],
            'genres': ['Orchestral', 'Other Orchestral Music'],
            'timestamp': 1554474370029,
            'entries': 'count:15'
        }
    }]

    def _real_extract(self, url):
        recording_id: str = self._match_id(url)
        recording_info: dict = self._download_json(f'https://api.idagio.com/v2.0/metadata/recordings/{recording_id}',
                                                   recording_id).get('result')

        track_ids: list[int] = traverse_obj(recording_info, ('tracks', ..., 'id'))

        return {
            '_type': 'playlist',
            'id': recording_id,
            'title': traverse_obj(recording_info, ('work', 'title')),
            'entries': [self.url_result(f'https://api.idagio.com/v2.0/metadata/tracks/{id}',
                                        ie='IdagioTrack', video_id=id, track_number=i)
                        for i, id in enumerate(track_ids, start=1)],
            'ext': 'mp3',
            'timestamp': traverse_obj(recording_info, ('created_at',)),
            'location': traverse_obj(recording_info, ('location',)),
            'artists': ([traverse_obj(recording_info, ('conductor', 'name'))] or []) +
            (traverse_obj(recording_info, ('ensembles', ..., 'name')) or []) +
            (traverse_obj(recording_info, ('soloists', ..., 'name')) or []),
            'composers': [traverse_obj(recording_info, ('work', 'composer', 'name')), ],
            'genres': [traverse_obj(recording_info, ('work', 'genre', 'title')),
                       traverse_obj(recording_info, ('work', 'subgenre', 'title')), ],
            }
