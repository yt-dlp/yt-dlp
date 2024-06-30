from .common import InfoExtractor
from ..utils import (
    clean_html,
    float_or_none,
    int_or_none,
    try_get,
)


class HitRecordIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?hitrecord\.org/records/(?P<id>\d+)'
    _TEST = {
        'url': 'https://hitrecord.org/records/2954362',
        'md5': 'fe1cdc2023bce0bbb95c39c57426aa71',
        'info_dict': {
            'id': '2954362',
            'ext': 'mp4',
            'title': 'A Very Different World (HITRECORD x ACLU)',
            'description': 'md5:e62defaffab5075a5277736bead95a3d',
            'duration': 139.327,
            'timestamp': 1471557582,
            'upload_date': '20160818',
            'uploader': 'Zuzi.C12',
            'uploader_id': '362811',
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'tags': list,
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video = self._download_json(
            f'https://hitrecord.org/api/web/records/{video_id}', video_id)

        title = video['title']
        video_url = video['source_url']['mp4_url']

        tags = None
        tags_list = try_get(video, lambda x: x['tags'], list)
        if tags_list:
            tags = [
                t['text']
                for t in tags_list
                if isinstance(t, dict) and t.get('text')
                and isinstance(t['text'], str)]

        return {
            'id': video_id,
            'url': video_url,
            'title': title,
            'description': clean_html(video.get('body')),
            'duration': float_or_none(video.get('duration'), 1000),
            'timestamp': int_or_none(video.get('created_at_i')),
            'uploader': try_get(
                video, lambda x: x['user']['username'], str),
            'uploader_id': try_get(
                video, lambda x: str(x['user']['id'])),
            'view_count': int_or_none(video.get('total_views_count')),
            'like_count': int_or_none(video.get('hearts_count')),
            'comment_count': int_or_none(video.get('comments_count')),
            'tags': tags,
        }
