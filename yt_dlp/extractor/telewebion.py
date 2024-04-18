from __future__ import annotations
import functools
import json
import textwrap

from .common import InfoExtractor
from ..utils import ExtractorError, format_field, int_or_none, parse_iso8601
from ..utils.traversal import traverse_obj


def _fmt_url(url):
    return functools.partial(format_field, template=url, default=None)


class TelewebionIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?telewebion\.com/episode/(?P<id>(?:0x[a-fA-F\d]+|\d+))'
    _TESTS = [{
        'url': 'http://www.telewebion.com/episode/0x1b3139c/',
        'info_dict': {
            'id': '0x1b3139c',
            'ext': 'mp4',
            'title': 'قرعه‌کشی لیگ قهرمانان اروپا',
            'series': '+ فوتبال',
            'series_id': '0x1b2505c',
            'channel': 'شبکه 3',
            'channel_id': '0x1b1a761',
            'channel_url': 'https://telewebion.com/live/tv3',
            'timestamp': 1425522414,
            'upload_date': '20150305',
            'release_timestamp': 1425517020,
            'release_date': '20150305',
            'duration': 420,
            'view_count': int,
            'tags': ['ورزشی', 'لیگ اروپا', 'اروپا'],
            'thumbnail': 'https://static.telewebion.com/episodeImages/YjFhM2MxMDBkMDNiZTU0MjE5YjQ3ZDY0Mjk1ZDE0ZmUwZWU3OTE3OWRmMDAyODNhNzNkNjdmMWMzMWIyM2NmMA/default',
        },
        'skip_download': 'm3u8',
    }, {
        'url': 'https://telewebion.com/episode/162175536',
        'info_dict': {
            'id': '0x9aa9a30',
            'ext': 'mp4',
            'title': 'کارما یعنی این !',
            'series': 'پاورقی',
            'series_id': '0x29a7426',
            'channel': 'شبکه 2',
            'channel_id': '0x1b1a719',
            'channel_url': 'https://telewebion.com/live/tv2',
            'timestamp': 1699979968,
            'upload_date': '20231114',
            'release_timestamp': 1699991638,
            'release_date': '20231114',
            'duration': 78,
            'view_count': int,
            'tags': ['کلیپ های منتخب', ' کلیپ طنز ', ' کلیپ سیاست ', 'پاورقی', 'ویژه فلسطین'],
            'thumbnail': 'https://static.telewebion.com/episodeImages/871e9455-7567-49a5-9648-34c22c197f5f/default',
        },
        'skip_download': 'm3u8',
    }]

    def _call_graphql_api(
        self, operation, video_id, query,
        variables: dict[str, tuple[str, str]] | None = None,
        note='Downloading GraphQL JSON metadata',
    ):
        parameters = ''
        if variables:
            parameters = ', '.join(f'${name}: {type_}' for name, (type_, _) in variables.items())
            parameters = f'({parameters})'

        result = self._download_json('https://graph.telewebion.com/graphql', video_id, note, data=json.dumps({
            'operationName': operation,
            'query': f'query {operation}{parameters} @cacheControl(maxAge: 60) {{{query}\n}}\n',
            'variables': {name: value for name, (_, value) in (variables or {}).items()}
        }, separators=(',', ':')).encode(), headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        if not result or traverse_obj(result, 'errors'):
            message = ', '.join(traverse_obj(result, ('errors', ..., 'message', {str})))
            raise ExtractorError(message or 'Unknown GraphQL API error')

        return result['data']

    def _real_extract(self, url):
        video_id = self._match_id(url)
        if not video_id.startswith('0x'):
            video_id = hex(int(video_id))

        episode_data = self._call_graphql_api('getEpisodeDetail', video_id, textwrap.dedent('''
            queryEpisode(filter: {EpisodeID: $EpisodeId}, first: 1) {
              title
              program {
                ProgramID
                title
              }
              image
              view_count
              duration
              started_at
              created_at
              channel {
                ChannelID
                name
                descriptor
              }
              tags {
                name
              }
            }
        '''), {'EpisodeId': ('[ID!]', video_id)})

        info_dict = traverse_obj(episode_data, ('queryEpisode', 0, {
            'title': ('title', {str}),
            'view_count': ('view_count', {int_or_none}),
            'duration': ('duration', {int_or_none}),
            'tags': ('tags', ..., 'name', {str}),
            'release_timestamp': ('started_at', {parse_iso8601}),
            'timestamp': ('created_at', {parse_iso8601}),
            'series': ('program', 'title', {str}),
            'series_id': ('program', 'ProgramID', {str}),
            'channel': ('channel', 'name', {str}),
            'channel_id': ('channel', 'ChannelID', {str}),
            'channel_url': ('channel', 'descriptor', {_fmt_url('https://telewebion.com/live/%s')}),
            'thumbnail': ('image', {_fmt_url('https://static.telewebion.com/episodeImages/%s/default')}),
            'formats': (
                'channel', 'descriptor', {str},
                {_fmt_url(f'https://cdna.telewebion.com/%s/episode/{video_id}/playlist.m3u8')},
                {functools.partial(self._extract_m3u8_formats, video_id=video_id, ext='mp4', m3u8_id='hls')}),
        }))
        info_dict['id'] = video_id
        return info_dict
