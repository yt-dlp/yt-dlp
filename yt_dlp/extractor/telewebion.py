from __future__ import annotations

import json
import textwrap
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    format_field,
    int_or_none,
    merge_dicts,
    parse_iso8601,
    url_or_none,
)
from ..utils.traversal import traverse_obj


def _fmt_url(url):
    return format_field(template=url, default=None)


def _append_query_params(url, query):
    return url if not query else f'{url}?{urllib.parse.urlencode(query)}'


class TelewebionIE(InfoExtractor):
    _WORKING = True
    _VALID_URL = r'https?://(?:www\.)?telewebion\.ir/(?:embed/)?episode/(?P<id>(?:0x[a-fA-F\d]+|\d+))/?(?:[#?].*)?'
    _TESTS = [{
        'url': 'http://www.telewebion.ir/episode/0x1b3139c/',
        'info_dict': {
            'id': '0x1b3139c',
            'ext': 'mp4',
            'title': 'قرعه‌کشی لیگ قهرمانان اروپا',
            'series': '+ فوتبال',
            'series_id': '0x1b2505c',
            'channel': 'شبکه 3',
            'channel_id': '0x1b1a761',
            'channel_url': 'https://telewebion.ir/live/tv3',
            'timestamp': 1425522414,
            'upload_date': '20150305',
            'release_timestamp': 1425517020,
            'release_date': '20150305',
            'duration': 420,
            'view_count': int,
            'tags': ['ورزشی', 'لیگ اروپا', 'اروپا'],
            'thumbnail': 'https://static.telewebion.ir/episodeImages/YjFhM2MxMDBkMDNiZTU0MjE5YjQ3ZDY0Mjk1ZDE0ZmUwZWU3OTE3OWRmMDAyODNhNzNkNjdmMWMzMWIyM2NmMA/default',
        },
        'skip_download': 'm3u8',
    }, {
        'url': 'https://telewebion.ir/episode/162175536',
        'info_dict': {
            'id': '0x9aa9a30',
            'ext': 'mp4',
            'title': 'کارما یعنی این !',
            'series': 'پاورقی',
            'series_id': '0x29a7426',
            'channel': 'شبکه 2',
            'channel_id': '0x1b1a719',
            'channel_url': 'https://telewebion.ir/live/tv2',
            'timestamp': 1699979968,
            'upload_date': '20231114',
            'release_timestamp': 1699991638,
            'release_date': '20231114',
            'duration': 78,
            'view_count': int,
            'tags': ['کلیپ های منتخب', ' کلیپ طنز ', ' کلیپ سیاست ', 'پاورقی', 'ویژه فلسطین'],
            'thumbnail': 'https://static.telewebion.ir/episodeImages/871e9455-7567-49a5-9648-34c22c197f5f/default',
        },
        'skip_download': 'm3u8',
    }, {
        'url': 'https://telewebion.ir/episode/0x16b8e258',
        'info_dict': {
            'id': '0x16b8e258',
            'ext': 'mp4',
            'title': '۲۱ بهمن ۱۴۰۴ - دعای 19 صحیفه سجادیه (دعای باران) | پخش زنده شبکه آموزش - ۲۱ بهمن ماه ۱۴۰۴',
            'thumbnail': 'https://static.telewebion.ir/episodeImages/d591669c-f8a4-4fc9-b6a7-0c01a481cd34/default',
            'duration': 310,
            'timestamp': 1770733607,
            'view_count': int,
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

        result = self._download_json('https://graph.telewebion.ir/graphql', video_id, note, data=json.dumps({
            'operationName': operation,
            'query': f'query {operation}{parameters} @cacheControl(maxAge: 60) {{{query}\n}}\n',
            'variables': {name: value for name, (_, value) in (variables or {}).items()},
        }, separators=(',', ':')).encode(), headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        if not result or traverse_obj(result, 'errors'):
            message = ', '.join(traverse_obj(result, ('errors', ..., 'message', {str})))
            raise ExtractorError(message or 'Unknown GraphQL API error')

        return result['data']

    def _extract_webpage_info(self, url, video_id):
        webpage = self._download_webpage(url, video_id, fatal=False)
        if not webpage:
            return {}

        json_ld = self._search_json_ld(webpage, video_id, expected_type='VideoObject', default={})
        info = traverse_obj(json_ld, {
            'title': ('title', {str}),
            'description': ('description', {str}),
            'thumbnail': ('thumbnails', 0, 'url', {url_or_none}),
            'duration': ('duration', {int_or_none}),
            'timestamp': ('timestamp', {int_or_none}),
            'view_count': ('view_count', {int_or_none}),
        })

        media_url = url_or_none(json_ld.get('url'))
        if media_url:
            info['formats'] = self._extract_m3u8_formats(
                media_url, video_id, 'mp4', m3u8_id='hls', fatal=False)
        return info

    def _extract_candidate_formats(self, video_id, *urls):
        formats = []
        for m3u8_url in urls:
            if not m3u8_url:
                continue
            extracted = self._extract_m3u8_formats(
                m3u8_url, video_id, 'mp4', m3u8_id='hls', fatal=False)
            if extracted:
                return extracted
            formats.extend(extracted)
        return formats

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage_info = self._extract_webpage_info(url, video_id)

        if not video_id.startswith('0x'):
            video_id = hex(int(video_id))

        api_info = {}
        if not webpage_info.get('formats'):
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

            api_info = traverse_obj(episode_data, ('queryEpisode', 0, {
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
                'channel_url': ('channel', 'descriptor', {_fmt_url('https://telewebion.ir/live/%s')}),
                'thumbnail': ('image', {_fmt_url('https://static.telewebion.ir/episodeImages/%s/default')}),
            }))
            descriptor = traverse_obj(episode_data, ('queryEpisode', 0, 'channel', 'descriptor', {str}))
            api_info['formats'] = self._extract_candidate_formats(
                video_id,
                descriptor and _append_query_params(
                    f'https://archive-azd1105.telewebion.ir/{descriptor}/episode/{video_id}/playlist.m3u8',
                    {'isp': 'NA', 'city': 'NA'}),
                descriptor and f'https://cdna.telewebion.ir/{descriptor}/episode/{video_id}/playlist.m3u8',
                descriptor and f'https://cdna.telewebion.ir/{descriptor}/episode/{video_id}/playlist.m3u8?isp=NA&city=NA',
            )

        return merge_dicts(api_info, webpage_info, {'id': video_id})
