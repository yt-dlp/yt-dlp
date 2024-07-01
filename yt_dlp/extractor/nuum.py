import functools

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    UserNotLive,
    filter_dict,
    int_or_none,
    parse_iso8601,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class NuumBaseIE(InfoExtractor):
    def _call_api(self, path, video_id, description, query={}):
        response = self._download_json(
            f'https://nuum.ru/api/v2/{path}', video_id, query=query,
            note=f'Downloading {description} metadata',
            errnote=f'Unable to download {description} metadata')
        if error := response.get('error'):
            raise ExtractorError(f'API returned error: {error!r}')
        return response['result']

    def _get_channel_info(self, channel_name):
        return self._call_api(
            'broadcasts/public', video_id=channel_name, description='channel',
            query={
                'with_extra': 'true',
                'channel_name': channel_name,
                'with_deleted': 'true',
            })

    def _parse_video_data(self, container, extract_formats=True):
        stream = traverse_obj(container, ('media_container_streams', 0, {dict})) or {}
        media = traverse_obj(stream, ('stream_media', 0, {dict})) or {}
        media_url = traverse_obj(media, (
            'media_meta', ('media_archive_url', 'media_url'), {url_or_none}), get_all=False)

        video_id = str(container['media_container_id'])
        is_live = media.get('media_status') == 'RUNNING'

        formats, subtitles = None, None
        headers = {'Referer': 'https://nuum.ru/'}
        if extract_formats:
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                media_url, video_id, 'mp4', live=is_live, headers=headers)

        return filter_dict({
            'id': video_id,
            'is_live': is_live,
            'formats': formats,
            'subtitles': subtitles,
            'http_headers': headers,
            **traverse_obj(container, {
                'title': ('media_container_name', {str}),
                'description': ('media_container_description', {str}),
                'timestamp': ('created_at', {parse_iso8601}),
                'channel': ('media_container_channel', 'channel_name', {str}),
                'channel_id': ('media_container_channel', 'channel_id', {str_or_none}),
            }),
            **traverse_obj(stream, {
                'view_count': ('stream_total_viewers', {int_or_none}),
                'concurrent_view_count': ('stream_current_viewers', {int_or_none}),
            }),
            **traverse_obj(media, {
                'duration': ('media_duration', {int_or_none}),
                'thumbnail': ('media_meta', ('media_preview_archive_url', 'media_preview_url'), {url_or_none}),
            }, get_all=False),
        })


class NuumMediaIE(NuumBaseIE):
    IE_NAME = 'nuum:media'
    _VALID_URL = r'https?://nuum\.ru/(?:streams|videos|clips)/(?P<id>[\d]+)'
    _TESTS = [{
        'url': 'https://nuum.ru/streams/1592713-7-days-to-die',
        'only_matching': True,
    }, {
        'url': 'https://nuum.ru/videos/1567547-toxi-hurtz',
        'md5': 'ce28837a5bbffe6952d7bfd3d39811b0',
        'info_dict': {
            'id': '1567547',
            'ext': 'mp4',
            'title': 'Toxi$ - Hurtz',
            'description': '',
            'timestamp': 1702631651,
            'upload_date': '20231215',
            'thumbnail': r're:^https?://.+\.jpg',
            'view_count': int,
            'concurrent_view_count': int,
            'channel_id': '6911',
            'channel': 'toxis',
            'duration': 116,
        },
    }, {
        'url': 'https://nuum.ru/clips/1552564-pro-misu',
        'md5': 'b248ae1565b1e55433188f11beeb0ca1',
        'info_dict': {
            'id': '1552564',
            'ext': 'mp4',
            'title': 'Про Мису 🙃',
            'timestamp': 1701971828,
            'upload_date': '20231207',
            'thumbnail': r're:^https?://.+\.jpg',
            'view_count': int,
            'concurrent_view_count': int,
            'channel_id': '3320',
            'channel': 'Misalelik',
            'duration': 41,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_data = self._call_api(f'media-containers/{video_id}', video_id, 'media')

        return self._parse_video_data(video_data)


class NuumLiveIE(NuumBaseIE):
    IE_NAME = 'nuum:live'
    _VALID_URL = r'https?://nuum\.ru/channel/(?P<id>[^/#?]+)/?(?:$|[#?])'
    _TESTS = [{
        'url': 'https://nuum.ru/channel/mts_live',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        channel = self._match_id(url)
        channel_info = self._get_channel_info(channel)
        if traverse_obj(channel_info, ('channel', 'channel_is_live')) is False:
            raise UserNotLive(video_id=channel)

        info = self._parse_video_data(channel_info['media_container'])
        return {
            'webpage_url': f'https://nuum.ru/streams/{info["id"]}',
            'extractor_key': NuumMediaIE.ie_key(),
            'extractor': NuumMediaIE.IE_NAME,
            **info,
        }


class NuumTabIE(NuumBaseIE):
    IE_NAME = 'nuum:tab'
    _VALID_URL = r'https?://nuum\.ru/channel/(?P<id>[^/#?]+)/(?P<type>streams|videos|clips)'
    _TESTS = [{
        'url': 'https://nuum.ru/channel/dankon_/clips',
        'info_dict': {
            'id': 'dankon__clips',
            'title': 'Dankon_',
        },
        'playlist_mincount': 29,
    }, {
        'url': 'https://nuum.ru/channel/dankon_/videos',
        'info_dict': {
            'id': 'dankon__videos',
            'title': 'Dankon_',
        },
        'playlist_mincount': 2,
    }, {
        'url': 'https://nuum.ru/channel/dankon_/streams',
        'info_dict': {
            'id': 'dankon__streams',
            'title': 'Dankon_',
        },
        'playlist_mincount': 1,
    }]

    _PAGE_SIZE = 50

    def _fetch_page(self, channel_id, tab_type, tab_id, page):
        CONTAINER_TYPES = {
            'clips': ['SHORT_VIDEO', 'REVIEW_VIDEO'],
            'videos': ['LONG_VIDEO'],
            'streams': ['SINGLE'],
        }

        media_containers = self._call_api(
            'media-containers', video_id=tab_id, description=f'{tab_type} tab page {page + 1}',
            query={
                'limit': self._PAGE_SIZE,
                'offset': page * self._PAGE_SIZE,
                'channel_id': channel_id,
                'media_container_status': 'STOPPED',
                'media_container_type': CONTAINER_TYPES[tab_type],
            })
        for container in traverse_obj(media_containers, (..., {dict})):
            metadata = self._parse_video_data(container, extract_formats=False)
            yield self.url_result(f'https://nuum.ru/videos/{metadata["id"]}', NuumMediaIE, **metadata)

    def _real_extract(self, url):
        channel_name, tab_type = self._match_valid_url(url).group('id', 'type')
        tab_id = f'{channel_name}_{tab_type}'
        channel_data = self._get_channel_info(channel_name)['channel']

        return self.playlist_result(OnDemandPagedList(functools.partial(
            self._fetch_page, channel_data['channel_id'], tab_type, tab_id), self._PAGE_SIZE),
            playlist_id=tab_id, playlist_title=channel_data.get('channel_name'))
