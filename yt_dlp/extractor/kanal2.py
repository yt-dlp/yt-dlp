from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    join_nonempty,
    traverse_obj,
    unified_timestamp,
    url_or_none,
)


class Kanal2IE(InfoExtractor):
    _VALID_URL = r'https?://kanal2\.postimees\.ee/[^?#]+\?([^#]+&)?id=(?P<id>\d+)'
    _TESTS = [
        {
            'note': 'Test standard url (#5575)',
            'url': 'https://kanal2.postimees.ee/pluss/video/?id=40792',
            'md5': 'baf49cab468cf553bc1cf36909f1a0c7',
            'info_dict': {
                'id': '40792',
                'ext': 'mp4',
                'title': 'Aedniku aabits / Osa 53  (05.08.2016 20:00)',
                'thumbnail': r're:https?://.*\.jpg$',
                'description': 'md5:53cabf3c5d73150d594747f727431248',
                'upload_date': '20160805',
                'timestamp': 1470416400,
            }
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        playlist = self._download_json(
            f'https://kanal2.postimees.ee/player/playlist/{video_id}',
            video_id, query={'type': 'episodes'},
            headers={'X-Requested-With': 'XMLHttpRequest'})

        return {
            'id': video_id,
            'title': join_nonempty(*traverse_obj(playlist, ('info', ('title', 'subtitle'))), delim=' / '),
            'description': traverse_obj(playlist, ('info', 'description')),
            'thumbnail': traverse_obj(playlist, ('data', 'image')),
            'formats': self.get_formats(playlist, video_id),
            'timestamp': unified_timestamp(self._search_regex(
                r'\((\d{2}\.\d{2}\.\d{4}\s\d{2}:\d{2})\)$',
                traverse_obj(playlist, ('info', 'subtitle')), 'timestamp', default=None)),
        }

    def get_formats(self, playlist, video_id):
        session = self._download_json(
            'https://sts.postimees.ee/session/register',
            video_id, note='Creating session', errnote='Error creating session',
            headers={
                'X-Original-URI': traverse_obj(playlist, ('data', 'path')),
                'Accept': 'application/json',
            })
        if session['reason'] != 'OK':
            raise ExtractorError(f'Unable to obtain session - {session["reason"]}')

        formats = []
        for stream in traverse_obj(playlist, ('data', 'streams'), default=[]):
            if not stream.get('file'):
                continue
            formats.append({
                'protocol': 'm3u8',
                'ext': 'mp4',
                'url': url_or_none(stream.get('file') + '&s=' + session['session']),
            })

        return formats
