# coding: utf-8
from __future__ import unicode_literals

import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    try_get,
)


class DroobleIE(InfoExtractor):
    _VALID_URL = r'https?://drooble\.com/(?:(?P<user>[^/]+)?/?(?P<kind>song|videos|music/albums)/(?P<id>\d+)|(?P<id_2>[^/]+)/(?P<kind_2>videos|music))'
    _TESTS = [{
        'url': 'https://drooble.com/song/2858030',
        'md5': 'TODO: md5 sum of the first 10241 bytes of the video file (use --test)',
        'info_dict': {
            'id': '2858030',
            'ext': 'unknown_video',
            'title': 'Skankocillin',
            'upload_date': '20200801',
            'timestamp': 1596241390,
            'uploader_id': '95894',
            'uploader': 'Bluebeat Shelter',
        }
    }, {
        'url': 'https://drooble.com/karl340758/videos/2859183',
        'info_dict': {
            'id': 'J6QCQY_I5Tk',
            'ext': 'mp4',
            'title': 'Skankocillin',
            'uploader_id': 'UCrSRoI5vVyeYihtWEYua7rg',
            'description': 'md5:ffc0bd8ba383db5341a86a6cd7d9bcca',
            'upload_date': '20200731',
            'uploader': 'Bluebeat Shelter',
        }
    }, {
        'url': 'https://drooble.com/karl340758/music/albums/2858031',
        'info_dict': {
            'id': '2858031',
        },
        'playlist_mincount': 8,
    }, {
        'url': 'https://drooble.com/karl340758/music',
        'info_dict': {
            'id': 'karl340758',
        },
        'playlist_mincount': 8,
    }]
    _API_BASE = 'https://drooble.com/api/dt/'

    def _call_api(self, method, video_id, data=None):
        data = {'children': 10, 'order': 'old2new', 'url_slug': video_id} if data is None else data
        response = self._download_json(self._API_BASE + method, video_id, data=json.dumps(data).encode())
        if not response[0]:
            raise ExtractorError('Unable to download JSON metadata')
        return response[1]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id') or mobj.group('id_2')
        user = mobj.group('user') or mobj.group('id_2')
        kind = mobj.group('kind') or mobj.group('kind_2')
        method = 'getMusicOverview' if kind in ('music/albums', 'music') else 'getElements'
        data = None
        if mobj.group('kind_2') == 'videos':
            data = {'album': -1, 'from_user': video_id, 'limit': 18, 'offset': 0, 'order': 'new2old',
                    'type': 'video'}
        elif kind in ('music/albums', 'music'):
            data = {'user': user, 'individual_limit': {'singles': 1, 'albums': 1, 'playlists': 1},
                    'public_only': True}
        json_data = self._call_api(method, video_id, data=data)

        if kind in ('music/albums', 'music'):
            json_data = json_data['singles']['list']

        entites = []
        for media in json_data:
            url = media.get('external_media_url') or media.get('link')
            if url.startswith('https://www.youtube.com'):
                entites.append({
                    '_type': 'url_transparent',
                    'url': url,
                    'ie_key': 'Youtube'
                })
                continue
            entites.append({
                'url': url,
                'id': media['id'],
                'title': media['title'],
                'duration': int_or_none(media.get('duration')),
                'timestamp': int_or_none(media.get('timestamp')),
                'album': try_get(media, lambda x: x['album']['title']),
                'uploader': try_get(media, lambda x: x['creator']['display_name']),
                'uploader_id': try_get(media, lambda x: x['creator']['id']),
                'thumbnail': media.get('image_comment'),
                'like_count': int_or_none(media.get('likes')),
                'vcodec': 'none' if (media.get('type') or '').lower() == 'audio' else None
            })

        if len(entites) > 1:
            return self.playlist_result(entites, video_id)

        return entites[0]
