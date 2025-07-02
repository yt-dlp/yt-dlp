from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class SkebIE(InfoExtractor):
    _VALID_URL = r'https?://skeb\.jp/@(?P<uploader_id>[^/]+)/works/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://skeb.jp/@riiru_wm/works/10',
        'info_dict': {
            'id': '466853',
            'ext': 'mp4',
            'title': '10',
            'description': 'md5:1ec50901efc3437cfbfe3790468d532d',
            'display_id': '10',
            'duration': 313,
            'genres': ['video'],
            'thumbnail': r're:https?://.+',
            'uploader': '姫ノ森りぃる@ひとづま',
            'uploader_id': 'riiru_wm',
        },
    }, {
        'url': 'https://skeb.jp/@furukawa_nob/works/3',
        'info_dict': {
            'id': '489408',
            'ext': 'mp3',
            'title': '3',
            'description': 'md5:6de1f8f876426a6ac321c123848176a8',
            'display_id': '3',
            'duration': 98,
            'genres': ['voice'],
            'tags': 'count:11',
            'thumbnail': r're:https?://.+',
            'uploader': '古川ノブ@宮城の動画勢Vtuber',
            'uploader_id': 'furukawa_nob',
        },
    }, {
        'url': 'https://skeb.jp/@Rizu_panda_cube/works/626',
        'info_dict': {
            'id': '626',
        },
        'playlist_count': 2,
    }]

    def _real_extract(self, url):
        uploader_id, work_id = self._match_valid_url(url).group('uploader_id', 'id')
        works = self._download_json(
            f'https://skeb.jp/api/users/{uploader_id}/works/{work_id}', work_id, headers={
                'Accept': 'application/json, text/plain, */*',
                'Authorization': 'Bearer null',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            })

        info = {
            'title': work_id,
            'display_id': work_id,
            'uploader_id': uploader_id,
            **traverse_obj(works, {
                'age_limit': ('nsfw', {bool}, {lambda x: 18 if x else None}),
                'description': (('source_body', 'body'), {clean_html}, any),
                'genres': ('genre', {str}, filter, all, filter),
                'tags': ('tag_list', ..., {str}, filter, all, filter),
                'uploader': ('creator', 'name', {str}),
            }),
        }

        entries = []
        for preview in works['previews']:
            ext = traverse_obj(preview, ('information', 'extension', {str}))
            if ext not in ('mp3', 'mp4'):
                continue
            mp3_info = {'abr': 128, 'vcodec': 'none'} if ext == 'mp3' else {}

            subtitles = {}
            subtitles.setdefault('ja', []).append({
                'ext': 'vtt',
                'url': preview['vtt_url'],
            })

            entries.append({
                'ext': ext,
                'subtitles': subtitles,
                **info,
                **mp3_info,
                **traverse_obj(preview, {
                    'id': ('id', {str_or_none}),
                    'thumbnail': ('poster_url', {url_or_none}),
                    'url': ('url', {url_or_none}),
                }),
                **traverse_obj(preview, ('information', {
                    'duration': ('duration', {int_or_none}),
                    'fps': ('frame_rate', {int_or_none}),
                    'height': ('height', {int_or_none}),
                    'width': ('width', {int_or_none}),
                })),
            })

        return self.playlist_result(entries, work_id)
