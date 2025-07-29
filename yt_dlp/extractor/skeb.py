from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    clean_html,
    int_or_none,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class SkebIE(InfoExtractor):
    _VALID_URL = r'https?://skeb\.jp/@(?P<uploader_id>[^/?#]+)/works/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://skeb.jp/@riiru_wm/works/10',
        'info_dict': {
            'id': '466853',
            'ext': 'mp4',
            'title': '10-1',
            'description': 'md5:1ec50901efc3437cfbfe3790468d532d',
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
            'title': '3-1',
            'description': 'md5:6de1f8f876426a6ac321c123848176a8',
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
            'description': 'md5:834557b39ca56960c5f77dd6ddabe775',
            'uploader': 'りづ100億%',
            'uploader_id': 'Rizu_panda_cube',
            'tags': 'count:57',
            'genres': ['video'],
        },
        'playlist_count': 2,
        'expected_warnings': ['Skipping unsupported extension'],
    }]

    def _call_api(self, uploader_id, work_id):
        return self._download_json(
            f'https://skeb.jp/api/users/{uploader_id}/works/{work_id}', work_id, headers={
                'Accept': 'application/json',
                'Authorization': 'Bearer null',
            })

    def _real_extract(self, url):
        uploader_id, work_id = self._match_valid_url(url).group('uploader_id', 'id')
        try:
            works = self._call_api(uploader_id, work_id)
        except ExtractorError as e:
            if not isinstance(e.cause, HTTPError) or e.cause.status != 429:
                raise
            webpage = e.cause.response.read().decode()
            value = self._search_regex(
                r'document\.cookie\s*=\s*["\']request_key=([^;"\']+)', webpage, 'request key')
            self._set_cookie('skeb.jp', 'request_key', value)
            works = self._call_api(uploader_id, work_id)

        info = {
            'uploader_id': uploader_id,
            **traverse_obj(works, {
                'age_limit': ('nsfw', {bool}, {lambda x: 18 if x else None}),
                'description': (('source_body', 'body'), {clean_html}, filter, any),
                'genres': ('genre', {str}, filter, all, filter),
                'tags': ('tag_list', ..., {str}, filter, all, filter),
                'uploader': ('creator', 'name', {str}),
            }),
        }

        entries = []
        for idx, preview in enumerate(traverse_obj(works, ('previews', lambda _, v: url_or_none(v['url']))), 1):
            ext = traverse_obj(preview, ('information', 'extension', {str}))
            if ext not in ('mp3', 'mp4'):
                self.report_warning(f'Skipping unsupported extension "{ext}"')
                continue

            entries.append({
                'ext': ext,
                'title': f'{work_id}-{idx}',
                'subtitles': {
                    'ja': [{
                        'ext': 'vtt',
                        'url': preview['vtt_url'],
                    }],
                } if url_or_none(preview.get('vtt_url')) else None,
                'vcodec': 'none' if ext == 'mp3' else None,
                **info,
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

        return self.playlist_result(entries, work_id, **info)
