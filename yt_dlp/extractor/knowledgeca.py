from .common import InfoExtractor
from ..utils import (
    clean_html,
    determine_ext,
    float_or_none,
    int_or_none,
    parse_age_limit,
    parse_iso8601,
    url_or_none,
)
from ..utils.traversal import require, subs_list_to_dict, traverse_obj


class KnowledgeCABaseIE(InfoExtractor):
    def _call_api(self, path, item_id):
        return self._download_json(
            f'https://api.knowledge.ca/api/v1/{path}/{item_id}', item_id, 'Downloading API JSON')

    @staticmethod
    def _parse_episode(episode):
        info = traverse_obj(episode, {
            'age_limit': ('rating', {parse_age_limit}),
            'description': ('description', {clean_html}, filter),
            'duration': ('duration', {int_or_none}),
            'media_type': ('type', {str}, filter),
            'release_timestamp': ('availability_ranges', 0, 'available_date', {parse_iso8601}),
            'season_id': ('season_id', {str}, filter),
            'season_number': ('season_number', {int_or_none}),
            'series': ('program_title', {clean_html}, filter),
            'series_id': ('program_id', {str}, filter),
            'thumbnail': ('image', 'url', {url_or_none}),
            'title': ('title', {clean_html}, filter),
        })
        if info.get('media_type') == 'episode':
            info.update(traverse_obj(episode, {
                'episode': ('title', {clean_html}, filter),
                'episode_number': ('episode_number', {int_or_none}),
            }))
        return info


class KnowledgeCAIE(KnowledgeCABaseIE):
    IE_NAME = 'knowledge.ca'
    _VALID_URL = r'https?://(?:www\.)?knowledge\.ca/watch/(?P<id>[\da-f]{8}(?:-[\da-f]{4}){3}-[\da-f]{12})'
    _TESTS = [{
        'url': 'https://www.knowledge.ca/watch/86bb900b-667c-400f-9b0e-3cbb4a07fb19',
        'info_dict': {
            'id': '86bb900b-667c-400f-9b0e-3cbb4a07fb19',
            'ext': 'mp4',
            'title': 'Silvicola',
            'age_limit': 10,
            'description': 'md5:02e8b3e0fe874e48f7d288d2ac8423ec',
            'duration': 4749,
            'episode': 'Silvicola',
            'media_type': 'episode',
            'release_date': '20260908',
            'release_timestamp': 1788850800,
            'season_id': 'acd9e54a-6300-44f6-8d8e-05e141434fb9',
            'series': 'Silvicola',
            'series_id': '27459d3d-ade2-4c21-8179-d392a670a8bc',
            'subtitles': {'eng': 'mincount:1'},
            'thumbnail': r're:https?://api\.knowledge\.ca/api/v1/media/[\da-f-]+',
            'timestamp': 1771976307,
            'upload_date': '20260224',
        },
    }, {
        'url': 'https://www.knowledge.ca/watch/d61b3183-e6c0-4537-ab53-a615199a9ca6',
        'info_dict': {
            'id': 'd61b3183-e6c0-4537-ab53-a615199a9ca6',
            'ext': 'mp4',
            'title': 'Silvicola',
            'age_limit': 10,
            'duration': 60,
            'media_type': 'preview',
            'release_date': '20260813',
            'release_timestamp': 1786604400,
            'season_id': 'acd9e54a-6300-44f6-8d8e-05e141434fb9',
            'series': 'Silvicola',
            'series_id': '27459d3d-ade2-4c21-8179-d392a670a8bc',
            'subtitles': {'eng': 'mincount:1'},
            'thumbnail': r're:https?://api\.knowledge\.ca/api/v1/media/[\da-f-]+',
            'timestamp': 1784955301,
            'upload_date': '20260725',
        },
    }, {
        'url': 'https://www.knowledge.ca/watch/023c76f9-2253-4073-b5be-3a4a3db5d387',
        'info_dict': {
            'id': '023c76f9-2253-4073-b5be-3a4a3db5d387',
            'ext': 'mp4',
            'title': 'The Falls',
            'age_limit': 14,
            'description': 'md5:91cd889401774f74d94f1ee9c4ba9995',
            'duration': 4174,
            'episode': 'The Falls',
            'episode_number': 1,
            'media_type': 'episode',
            'release_date': '20240901',
            'release_timestamp': 1725174000,
            'season_id': '283d38f7-cf5e-43ca-b5b0-e2b457dbc39a',
            'series': 'Rebus',
            'series_id': '7643980d-4523-49b0-929a-7ce43ff3dd20',
            'subtitles': {'eng': 'mincount:1'},
            'thumbnail': r're:https?://api\.knowledge\.ca/api/v1/media/[\da-f-]+',
            'timestamp': 1602025680,
            'upload_date': '20201006',
        },
    }]

    def _extract_jwplayer_media(self, jwplayer_id, video_id):
        media = traverse_obj(self._download_json(
            f'https://cdn.jwplayer.com/v2/media/{jwplayer_id}', video_id,
            'Downloading JW Player media JSON'), ('playlist', 0, {dict}, {require('media item')}))

        # Don't use `parse_jwplayer_data`, as it keys subtitles on `label` rather than `language`
        # `language` is often absent and `label` can be an asset ID, but this network is English-only
        subtitles = traverse_obj(media, ('tracks', lambda _, v: v['kind'] == 'captions', {
            'url': ('file', {url_or_none}),
            'id': ('language', {str}),
        }, all, {subs_list_to_dict(lang='eng')}))

        formats, manifest_subs = [], {}
        for source in traverse_obj(media, ('sources', lambda _, v: url_or_none(v['file']))):
            if determine_ext(source['file']) == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    source['file'], video_id, 'mp4', m3u8_id='hls', fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=manifest_subs)
                continue
            fmt = {
                'url': source['file'],
                **traverse_obj(source, {
                    'filesize': ('filesize', {int_or_none}),
                    'format_id': ('label', {str}),
                    'fps': ('framerate', {float_or_none}),
                    'height': ('height', {int_or_none}),
                    'tbr': ('bitrate', {int_or_none(scale=1000)}),
                    'width': ('width', {int_or_none}),
                }),
            }
            if (traverse_obj(source, ('type', {str})) or '').startswith('audio/'):
                fmt['vcodec'] = 'none'
            formats.append(fmt)

        return {
            'formats': formats,
            # The HLS segments have broken frame timestamps, so prefer the progressive MP4s
            '_format_sort_fields': ('res', 'proto'),
            # The manifest carries the same captions, but chunked and inconsistently tagged
            'subtitles': subtitles or manifest_subs,
            'timestamp': traverse_obj(media, ('pubdate', {int_or_none})),
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        episode = self._call_api('episodes', video_id)

        return {
            'id': video_id,
            **self._extract_jwplayer_media(
                traverse_obj(episode, ('jwplayer_id', {str}, {require('JW Player ID')})), video_id),
            **self._parse_episode(episode),
        }


class KnowledgeCAProgramIE(KnowledgeCABaseIE):
    IE_NAME = 'knowledge.ca:program'
    _VALID_URL = r'https?://(?:www\.)?knowledge\.ca/program/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.knowledge.ca/program/27459d3d-ade2-4c21-8179-d392a670a8bc',
        'info_dict': {
            'id': '27459d3d-ade2-4c21-8179-d392a670a8bc',
            'title': 'Silvicola',
            'creators': ['Jean-Philippe Marquis'],
            'description': 'md5:02e8b3e0fe874e48f7d288d2ac8423ec',
            'display_id': '27459d3d-ade2-4c21-8179-d392a670a8bc',
            'release_year': 2023,
            'tags': 'count:5',
            'thumbnail': r're:https?://api\.knowledge\.ca/api/v1/media/[\da-f-]+',
        },
        'playlist_count': 1,
    }, {
        # series, addressed by its alias
        'url': 'https://www.knowledge.ca/program/rebus',
        'info_dict': {
            'id': '7643980d-4523-49b0-929a-7ce43ff3dd20',
            'title': 'Rebus',
            'cast': 'count:3',
            'description': 'md5:236ee8e7529e6868d8fddfa4fca99a85',
            'display_id': 'rebus',
            'release_year': 2006,
            'tags': ['Detective Series'],
            'thumbnail': r're:https?://api\.knowledge\.ca/api/v1/media/[\da-f-]+',
        },
        'playlist_count': 10,
    }, {
        # multiple seasons, with bonus content
        'url': 'https://www.knowledge.ca/program/emergency-room-life-and-death-at-vgh',
        'info_dict': {
            'id': '2e1e1a1e-19a3-4a28-9410-d8c0e6276cbc',
            'title': 'Emergency Room: Life and Death at VGH',
            'creators': 'count:2',
            'description': 'md5:543fba6ef8a008a494da8313045e3dbb',
            'display_id': 'emergency-room-life-and-death-at-vgh',
            'release_year': 2013,
            'tags': 'count:7',
            'thumbnail': r're:https?://api\.knowledge\.ca/api/v1/media/[\da-f-]+',
        },
        'playlist_mincount': 45,
    }]

    def _entries(self, program):
        # `previews` are trailers for the program itself, so they're skipped
        for episode in traverse_obj(program, (
                'seasons', ..., ('episodes', 'extras'), lambda _, v: v['id'] and v['jwplayer_id'])):
            yield self.url_result(
                f'https://www.knowledge.ca/watch/{episode["id"]}', KnowledgeCAIE,
                episode['id'], **self._parse_episode(episode))

    def _real_extract(self, url):
        display_id = self._match_id(url)
        program = self._call_api('programs', display_id)

        return self.playlist_result(
            self._entries(program), program['id'], display_id=display_id, **traverse_obj(program, {
                'title': ('title', {clean_html}, filter),
                'description': ('description', {clean_html}, filter),
                'release_year': ('year', {int_or_none}),
                'thumbnail': (('header_landscape_image', 'card_landscape_image'), 'url', {url_or_none}, any),
                'tags': ('attributes', lambda _, v: v['type'] == 'tags', 'values', ..., {str}),
                'cast': ('attributes', lambda _, v: v['category'] == 'Cast', 'values', ..., {str}),
                'creators': ('attributes', lambda _, v: v['category'] in (
                    'Creator', 'Creators', 'Director', 'Directors'), 'values', ..., {str}),
            }))


class KnowledgeCACollectionIE(KnowledgeCABaseIE):
    IE_NAME = 'knowledge.ca:collection'
    _VALID_URL = r'https?://(?:www\.)?knowledge\.ca/collection/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.knowledge.ca/collection/curated-knowledge-originals',
        'info_dict': {
            'id': '539f22d2-0e45-48c7-9a67-6ff55aab1195',
            'title': 'Knowledge Originals',
            'display_id': 'curated-knowledge-originals',
        },
        'playlist_mincount': 10,
    }]

    def _entries(self, collection):
        for program in traverse_obj(collection, ('items', lambda _, v: v['id'])):
            yield self.url_result(
                f'https://www.knowledge.ca/program/{program["id"]}', KnowledgeCAProgramIE,
                program['id'], traverse_obj(program, ('title', {clean_html}, filter)))

    def _real_extract(self, url):
        display_id = self._match_id(url)
        collection = self._call_api('collections', display_id)

        return self.playlist_result(
            self._entries(collection), collection['id'],
            traverse_obj(collection, ('title', {clean_html}, filter)), display_id=display_id)
