import functools
import uuid

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    InAdvancePagedList,
    UserNotLive,
    clean_html,
    int_or_none,
    join_nonempty,
    parse_iso8601,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class SoopGlobalBaseIE(InfoExtractor):
    def _call_api(self, item_id, path, fatal=False, **kwargs):
        info = self._download_json(
            f'https://api.sooplive.com/{path}/{item_id}', item_id,
            fatal=fatal, headers={'client-id': str(uuid.uuid4())}, expected_status=400, **kwargs)

        status = info.get('statusCode')
        if status and status != 200:
            code = traverse_obj(info, ('code', {clean_html}, filter))
            message = traverse_obj(info, ('message', {clean_html}, filter))
            raise ExtractorError(join_nonempty(code, message, delim=': '), expected=True)

        return info


class SoopGlobalIE(SoopGlobalBaseIE):
    IE_NAME = 'soop:global'

    _VALID_URL = r'https?://(?:www\.)?sooplive\.com/video/(?P<id>\d+)(?:[/?#]|$)'
    _TESTS = [{
        'url': 'https://www.sooplive.com/video/69365',
        'info_dict': {
            'id': '69365',
            'ext': 'mp4',
            'title': 'SEN vs. GEN — SVL 2024 — Group Stage— Day 3',
            'categories': ['VALORANT'],
            'channel': 'VALORANT_Esports_EN',
            'channel_id': 'valoranten',
            'comment_count': int,
            'duration': 33183,
            'like_count': int,
            'modified_date': '20241212',
            'modified_timestamp': 1734010413,
            'tags': 'count:3',
            'thumbnail': r're:https?://global-media-cdn\.sooplive\.com/.+',
            'timestamp': 1734010413,
            'upload_date': '20241212',
            'view_count': int,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # NFSW
        'url': 'https://www.sooplive.com/video/40771',
        'info_dict': {
            'id': '40771',
            'ext': 'mp4',
            'title': '✧ SOOP直播活動 ✧ 與哈娜 共度七夕 ♥ ✧ 08月29日 | 早安安! Thank u for coming♥ |',
            'age_limit': 19,
            'categories': ['Virtual Streaming'],
            'channel': '花猫ヒメ',
            'channel_id': 'hananekohime',
            'comment_count': int,
            'duration': 7346,
            'like_count': int,
            'modified_date': '20240829',
            'modified_timestamp': 1724930165,
            'tags': 'count:3',
            'thumbnail': r're:https?://global-media-cdn\.sooplive\.com/.+',
            'timestamp': 1724930165,
            'upload_date': '20240829',
            'view_count': int,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # Clip, NFSW
        'url': 'https://www.sooplive.com/video/163233',
        'info_dict': {
            'id': '163233',
            'ext': 'mp4',
            'title': 'Dance',
            'categories': ['Just Chatting'],
            'channel': '아리샤_ARISHA',
            'channel_id': 'arisha',
            'comment_count': int,
            'duration': 77,
            'like_count': int,
            'modified_date': '20250927',
            'modified_timestamp': 1758993491,
            'tags': 'count:2',
            'thumbnail': r're:https?://global-media-cdn\.sooplive\.com/.+',
            'timestamp': 1758993491,
            'upload_date': '20250927',
            'view_count': int,
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        file_info = traverse_obj(self._call_api(video_id, 'v2/vod/media/info'), (
            'data', 'fileList', lambda _, v: url_or_none(v['mediaPath']), any))

        m3u8_url = file_info['mediaPath']
        formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4')
        vod_info = self._call_api(video_id, 'vod/info')

        return {
            'id': video_id,
            'formats': formats,
            **traverse_obj(vod_info, {
                'title': ('titleName', {clean_html}),
                'age_limit': ('isAdult', {bool}, {lambda x: 19 if x else None}),
                'categories': ('categoryName', {str}, all, filter),
                'channel': ('nickName', {clean_html}),
                'channel_id': ('channelId', {str}),
                'comment_count': ('commentCnt', {int_or_none}),
                'duration': ('totalVideoDuration', {int_or_none(scale=1000)}),
                'like_count': ('likeCnt', {int_or_none}),
                'modified_timestamp': ('updateDate', {parse_iso8601}),
                'tags': ('tagList', ..., 'name', {str}, filter, all, filter),
                'thumbnail': ('thumb', {url_or_none}),
                'timestamp': ('createDate', {parse_iso8601}),
                'view_count': ('readCnt', {int_or_none}),
            }),
        }


class SoopGlobalLiveIE(SoopGlobalBaseIE):
    IE_NAME = 'soop:global:live'

    _VALID_URL = r'https?://(?:www\.)?sooplive\.com/(?P<id>\w+)/?(?=[?#]|$)'
    _TESTS = [{
        'url': 'https://www.sooplive.com/arisha',
        'info_dict': {
            'id': 'arisha',
            'ext': 'mp4',
            'title': str,
            'channel': '아리샤_ARISHA',
            'channel_follower_count': int,
            'channel_id': 'arisha',
            'concurrent_view_count': int,
            'like_count': int,
            'live_status': 'is_live',
            'thumbnail': r're:https?://global-media\.sooplive\.com/.+',
            'timestamp': int,
            'upload_date': str,
        },
        'skip': 'Livestream',
    }]

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        channel_info = self._call_api(channel_id, 'v2/channel/info')
        stream_info = self._call_api(channel_id, 'v2/stream/info')

        is_live = traverse_obj(stream_info, ('data', 'isStream', {bool}))
        if not is_live:
            raise UserNotLive(video_id=channel_id)

        formats = self._extract_m3u8_formats(
            f'https://global-media.sooplive.com/live/{channel_id}/master.m3u8', channel_id, 'mp4')

        return {
            'id': channel_id,
            **traverse_obj(channel_info, ('data', 'streamerChannelInfo', {
                'channel': ('nickname', {clean_html}),
                'channel_follower_count': ('totalFollowerCount', {int_or_none}),
            })),
            'channel_id': channel_id,
            'formats': formats,
            'is_live': is_live,
            **traverse_obj(stream_info, ('data', {
                'title': ('title', {clean_html}),
                'age_limit': ('isAdult', {bool}, {lambda x: 19 if x else None}),
                'concurrent_view_count': ('totalViewer', {int_or_none}),
                'like_count': ('likeCnt', {int_or_none}),
                'thumbnail': ('thumbnailUrl', {url_or_none}),
                'timestamp': ('streamStartDate', {parse_iso8601}),
            })),
        }


class SoopGlobalUserIE(SoopGlobalBaseIE):
    IE_NAME = 'soop:global:user'

    _PAGE_SIZE = 20
    _VALID_URL = r'https?://(?:www\.)?sooplive\.com/(?P<id>\w+)/(?P<type>clip|video)(?:[/?#]|$)'
    _TESTS = [{
        'url': 'https://www.sooplive.com/soopbilliards1/video',
        'info_dict': {
            'id': 'soopbilliards1',
        },
        'playlist_mincount': 140,
    }, {
        'url': 'https://www.sooplive.com/soopbaseball1/clip',
        'info_dict': {
            'id': 'soopbaseball1',
        },
        'playlist_mincount': 1020,
    }]

    def _entries(self, channel_id, page):
        vod_list = self._call_api(
            channel_id, 'v2/vod/channel/list',
            query={'limit': self._PAGE_SIZE, 'page': page})
        id_list = traverse_obj(vod_list, (
            'data', 'list', ..., 'vodNo', {str_or_none}))

        return self.playlist_from_matches(
            id_list, channel_id, ie=SoopGlobalIE,
            getter=lambda x: f'https://www.sooplive.com/video/{x}',
        )['entries']

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        total = traverse_obj(self._call_api(
            channel_id, 'v2/vod/channel/list'), ('data', 'total', {int_or_none}))
        total_pages = (total + self._PAGE_SIZE - 1) // self._PAGE_SIZE

        return self.playlist_result(InAdvancePagedList(
            functools.partial(self._entries, channel_id), total_pages, self._PAGE_SIZE), channel_id)
