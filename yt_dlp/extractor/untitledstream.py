import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
    traverse_obj,
    url_or_none,
)


class UntitledStreamIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?untitled\.stream/library/project/(?P<id>[A-Za-z0-9_-]+)'
    _TESTS = [{
        'url': 'https://untitled.stream/library/project/4uZWtNIwzqW1qGGMQ62Rv',
        'info_dict': {
            'id': '4uZWtNIwzqW1qGGMQ62Rv',
            'title': 'The Creamer Nation Tape, Vol. 2 (Test Pressing)',
            'uploader': 'Creamer Nation',
            'uploader_id': 'creamernation',
            'thumbnail': r're:https?://.*',
        },
        'playlist_mincount': 1,
        'playlist': [{
            'info_dict': {
                'id': 'trck_M2Nj_511a3608-028c-413a-bfba-85712dd7fd86',
                'ext': 'm4a',
                'title': 'Light Up The Night',
                'duration': 265.72,
                'filesize': 4301416,
                'track_number': 1,
                'artists': ['Creamer Nation'],
                'album': 'The Creamer Nation Tape, Vol. 2 (Test Pressing)',
                'timestamp': 1758859005,
                'upload_date': '20250926',
                'thumbnail': r're:https?://.*',
            },
        }],
    }, {
        'url': 'http://untitled.stream/library/project/4uZWtNIwzqW1qGGMQ62Rv',
        'only_matching': True,
    }, {
        'url': 'https://www.untitled.stream/library/project/4uZWtNIwzqW1qGGMQ62Rv',
        'only_matching': True,
    }]

    _API_HEADERS = {
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    }

    @staticmethod
    def _extract_audio_path(track):
        candidates = []
        for key in ('audio_url', 'audio_fallback_url', 'file_url'):
            audio_url = track.get(key)
            if not audio_url:
                continue
            m = re.search(r'/object/(.+?)(?:\?|$)', audio_url)
            if m:
                candidates.append(m.group(1))
        return next(
            (c for c in candidates if c.startswith('private-audio/')),
            candidates[0] if candidates else None)

    def _get_signed_url(self, object_path, video_id):
        slash_idx = object_path.find('/')
        if slash_idx == -1:
            return None
        bucket = object_path[:slash_idx]
        inner_path = object_path[slash_idx + 1:]
        data = self._download_json(
            f'https://untitled.stream/api/storage/buckets/{bucket}/objects/{urllib.parse.quote(inner_path, safe="")}/signedUrl?durationInSeconds=10800&cacheBufferInSeconds=600',
            video_id, headers=self._API_HEADERS,
            note='Downloading signed URL', errnote='Unable to download signed URL',
            fatal=False)
        return traverse_obj(data, 'signedURL', 'signedUrl', 'url', expected_type=url_or_none)

    def _real_extract(self, url):
        project_id = self._match_id(url)
        data = self._download_json(
            f'https://untitled.stream/library/project/{project_id}?_data',
            project_id, headers=self._API_HEADERS)

        project_data = data['project']
        project = project_data['project']
        raw_tracks = project_data.get('tracks') or project.get('tracks') or []

        title = traverse_obj(project, 'title', 'name')
        uploader = traverse_obj(project, 'artist_name', 'username', ('owner', 'username'), ('owner', 'name'))
        uploader_id = traverse_obj(project, 'username', ('owner', 'username'))
        thumbnail = traverse_obj(
            project, 'artwork_signed_url', 'artwork_url', 'cover_art_url', expected_type=url_or_none)

        entries = []
        for i, track in enumerate(raw_tracks):
            audio_path = self._extract_audio_path(track)
            if not audio_path:
                continue
            track_id = str(traverse_obj(track, 'id') or f'{project_id}-{i}')
            signed_url = self._get_signed_url(audio_path, track_id)
            if not signed_url:
                self.report_warning(f'Unable to get download URL for track {i + 1}')
                continue
            entries.append({
                'id': track_id,
                'title': traverse_obj(track, 'title', 'name') or f'Track {i + 1}',
                'url': signed_url,
                'ext': track.get('file_type') or 'mp3',
                'duration': float_or_none(track.get('duration')),
                'filesize': int_or_none(track.get('file_size_bytes')),
                'timestamp': int_or_none(track.get('time_created')),
                'track_number': i + 1,
                'artist': uploader,
                'album': title,
                'thumbnail': thumbnail,
            })

        return self.playlist_result(
            entries, project_id, title,
            uploader=uploader, uploader_id=uploader_id, thumbnail=thumbnail)
